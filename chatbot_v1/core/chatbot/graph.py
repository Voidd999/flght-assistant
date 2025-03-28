"""Define a simple graph with structured tools.

This module implements a simple graph with two structured tools using LangGraph.
"""

import os
import json
import logging

from langgraph.graph import START, END,  StateGraph
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent, InjectedState
from langchain_core.messages.modifier import RemoveMessage # use to remove message from state
from langgraph.pregel.retry import RetryPolicy
from langchain_core.tools import Tool, tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.checkpoint.redis import RedisSaver
from app.core.chatbot.utils.redis_client import get_redis_client
from langgraph.types import Command, Interrupt
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools.base import InjectedToolCallId
from langsmith import traceable

from app.core.chatbot.prompts import FAQ_PROMPT, \
    CONFIRMATION_CLASSIFICATION_PROMPT, \
    INTENT_CLASSIFICATION_PROMPT, \
    WELCOME_PROMPT, \
    LANGUAGE_RULES, \
    SYSTEM_PROMPT, \
    TRANSLATION_PROMPT
from app.core.chatbot.state import State
from app.core.chatbot.tools import search_docs
from app.core.chatbot.utils.prompt import get_formatted_prompt
from app.core.chatbot.workflow_manager import workflow_manager, WorkflowStep
from app.core.chatbot.tools.flight_booking.tools import *
from app.core.chatbot.llm_manager import LLMManager
from app.core.chatbot.utils.messages import clean_messages, remove_thinking_tags
from app.core.chatbot.tools.baggage_tracking.tools import register_tools as baggage_tracking_tools
from app.core.chatbot.tools.flight_booking.tools import register_tools as flight_booking_tools
from app.core.chatbot.tools.sample_wf.tools import register_tools as sample_wf_tools
from app.core.chatbot.tools.flight_status.tools import register_tools as flight_status_tools
from langgraph.checkpoint.base import BaseCheckpointSaver
from app.core.chatbot.tools.base import BASE_TOOLS
from app.core.chatbot.kbs.faq_graph import faq_graph as  build_faq_graph

# Set up logger
logger = logging.getLogger(__name__)

async def graph(saver: BaseCheckpointSaver):
    # Replace the old settings.get("llm") with direct access to settings
    llm = LLMManager.from_settings({
        "provider": os.environ["LLM_PROVIDER"],
        "model": os.environ["LLM_MODEL"],
        "config": {
            "temperature": os.environ["LLM_TEMPERATURE"]
        }
    })
    
    TOOL_MAPPING = {
        **flight_booking_tools(),
        **baggage_tracking_tools(),
        **sample_wf_tools(),
        **flight_status_tools(),
    }

    
    async def classify_intention_condition(state: State):
        """Classify user intention with workflow detection"""
        
        logger.info("condition: classify_intention_condition")
        
        # Get last user message with proper type checking
        last_msg = next(
            (msg for msg in reversed(state.get("messages", [])) 
             if isinstance(msg, HumanMessage)),
            None
        )
        
        # Handle empty conversation state
        if not state.get("messages"):
            return "welcome"  

        # Safely extract content with fallback
        last_msg_content = getattr(last_msg, "content", str(last_msg))
        
        # Translate the message for classification purposes
        translation_prompt = TRANSLATION_PROMPT.format(message=last_msg_content)
        
        translation_response = await llm.ainvoke([SystemMessage(content=translation_prompt)])
        translated_content = translation_response.content.strip()
        
        workflow_name = state.get("current_workflow")
        workflow_state = state.get("workflow_data", {}).get(workflow_name, {})
        current_step = workflow_state.get("current_step")
        collected_data = workflow_state.get("collected_data", {}).copy()  
        
        # Build context-aware prompt using translated content for classification
        workflow_context = (
            f"Current Workflow: {workflow_name}\n"
            f"Current Step: {current_step}\n"
            f"Collected Data: {json.dumps(collected_data, indent=2)}"
        ) if current_step else "No active workflow"
        
        workflow_descriptions = workflow_manager.workflow_descriptions
        prompt = get_formatted_prompt(
            state,
            INTENT_CLASSIFICATION_PROMPT,
            [],
            {
                "workflows": workflow_descriptions,
                "last_msg": translated_content.replace("{", "{{").replace("}", "}}"),
                "workflow_context": workflow_context,
                "recent_messages": "\n".join([
                    getattr(m, "content", str(m)) 
                    for m in state.get("messages", [])[-3:]
                ])
            }
        )

        response = await llm.ainvoke([SystemMessage(content=prompt)])
        intention = response.content.strip().lower()
        logger.info(f"Classified intention: {intention}")
        logger.debug(f"Original message: {last_msg_content}")
        logger.debug(f"Translated message (for classification): {translated_content}")
        
        # Return routing decision without modifying state
        if "start_workflow" in intention.lower():
            workflow_name = intention.split("/")[-1]
            if workflow_name in workflow_manager.workflows:
                return workflow_name
        # elif intention == "human":
        #     return "human_help"
        elif intention == "faq":
            return "faq"
        else:
            return "agent"
        
    async def welcome_node(state: State):
        """Handle initial welcome interaction"""
        
        logger.info("node: welcome_node")
        
        llm = LLMManager.from_settings({
            "provider": os.environ["LLM_PROVIDER"],
            "model": os.environ["LLM_MODEL"],
            "config": {
                "temperature": os.environ["LLM_TEMPERATURE"]
            }
        })

        
        if not state.get("messages"):
            response = await llm.ainvoke([
                SystemMessage(content=get_formatted_prompt(state, WELCOME_PROMPT)),
            ])
            cleaned_content = remove_thinking_tags(response.content)
            return {"messages": [AIMessage(content=cleaned_content)]}
        return state

    
    async def check_step_node(state: State):
        """Determine next step using workflow config from state"""
        
        logger.info("node: check_step_node")
        
        workflow_name = state.get("current_workflow")
        workflow_state = state.get("workflow_data", {}).get(workflow_name, {})
        current_step = workflow_state.get("current_step")
        
        next_step = workflow_manager.get_next_step(
            state,
            current_step, 
            workflow_name
        ) if workflow_name else None
            
        # Update the state with the new current step
        if next_step:
            state["workflow_data"][workflow_name]["current_step"] = next_step            
                
        return state

    # Add human help node handler BEFORE init_main_graph
    # async def human_help_node(state: State):
    #     """Handle transfer to human support"""
        
    #     logger.info("node: human_help_node")
        
    #     return {
    #         "messages": [
    #             AIMessage(content="Let me connect you to a human specialist. Please wait...")
    #         ]
    #     }


    async def agent_node(state: State):                
        """
        Process user input using the appropriate agent based on workflow context.
        
        Args:
            state: The current state
            
        Returns:
            Updated state with agent response
        """
        logger.info("node: agent_node")

        # Get workflow name
        workflow_name = state.get("current_workflow")
        
        # Handle user talking about anything else not related to a workflow
        if not workflow_name:
            agent = create_react_agent(
                llm,
                [],
                prompt=get_formatted_prompt(state, SYSTEM_PROMPT),
                state_schema=State
            )
            response = await agent.ainvoke(state)
            cleaned_messages = clean_messages(response["messages"])
            response["messages"] = cleaned_messages
            return response

        workflow_state = state.get("workflow_data", {}).get(workflow_name, {})
        current_step = workflow_state.get("current_step")
        collected_data = workflow_state.get("collected_data", {}).copy()  
        workflow = workflow_manager.get_workflow(workflow_name)
        
        if current_step not in workflow.steps:
            logger.warning(f"Step {current_step} not found in workflow {workflow_name}")
            return state
        else:
            step = workflow.steps[current_step]

        # Enforce step-specific tool restrictions
        allowed_tools = step.tools
        
        # Build the list of tools based on allowed_tools
        agent_tools = []
        tool_registry = workflow_manager.tool_registry
        
        for tool_name in allowed_tools:
            # First try the tool name as is (should already be scoped)
            if tool_name in tool_registry:
                agent_tools.append(tool_registry[tool_name])
                continue
                
            # If not found and not already prefixed, try with workflow prefix
            if not tool_name.startswith(f"{workflow_name}."):
                scoped_tool_name = f"{workflow_name}.{tool_name}"
                if scoped_tool_name in tool_registry:
                    agent_tools.append(tool_registry[scoped_tool_name])
                    continue
            
            # If we get here, the tool wasn't found
            logger.warning(f"Tool '{tool_name}' not found in tool registry")
            error_message = ToolMessage(
                content="An error occurred while processing your request. Please try again later.",
                tool_call_id=None,
                name="error"
            )
            state["messages"].append(error_message)
            return state
            
        # Create and execute agent with restricted tools
        prompt = workflow.build_workflow_prompt(state, current_step, workflow_name)
        
        has_tools = len(agent_tools) > 0
        llm_with_tools = llm.bind_tools(agent_tools) if has_tools else llm
        agent = create_react_agent(
            llm_with_tools,
            agent_tools if has_tools else [],
            prompt=prompt,
            state_schema=State
        )
        
        response = await agent.ainvoke(state)

        # Add thinking tag cleanup
        cleaned_messages = clean_messages(response["messages"])
        response["messages"] = cleaned_messages
        
        logger.info(f"node: agent node - current step: {current_step}")
        
        return response
        
                
    # ==========================================
    
    # Build the graph
    builder = StateGraph(State)

    # Add FAQ graph
    faq_graph = await build_faq_graph(llm, saver)
    builder.add_node("faq", faq_graph)
    
    # Add nodes
    builder.add_node("agent", agent_node, retry=RetryPolicy(max_attempts=3))
    builder.add_node("check_step", check_step_node)
    builder.add_node("welcome", welcome_node)
    for wf in workflow_manager.workflows.values():
        builder.add_node(wf.name, wf.init_workflow_node)
    

    workflows_keys = workflow_manager.workflow_names
    # Update initial edges
    builder.add_conditional_edges(
        START,
        classify_intention_condition,
        {
            **{wf: wf for wf in workflows_keys},
            # "human_help": "human_help",
            "faq": "faq", 
            "welcome": "welcome",
            "agent": "agent"
        }
    )
    
    # Connect workflow initialization
    for wf in workflows_keys:
        builder.add_edge(wf, "agent")

    # # Add edge for human help node
    # builder.add_edge("human_help", END)

    # Connect welcome node
    builder.add_edge("welcome", END)

    # Connect agent node
    builder.add_edge("agent", "check_step")
    builder.add_edge("check_step", END)

    logger.info(f"Graph built with {len(workflows_keys)} workflows")
    
    # redis saver
    graph = builder.compile(checkpointer=saver)    
    return graph
    
    # memory saver
    # checkpointer = MemorySaver()            
    # graph = builder.compile(checkpointer=checkpointer)    
    # return graph