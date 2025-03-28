import os
from langchain._api import LangChainDeprecationWarning
import warnings

warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)

import asyncio
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
import json
from llm_manager import LLMManager, LLMConfig
from chatbot_v2.models import ChatState

# Import the flight booking module
from flight_booking.main import process_message as flight_booking_process_message
from flight_booking.models import BookingState

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
load_dotenv()

llm_config = LLMConfig(
    provider="azure", model="gpt-4o-mini", config={"temperature": 0.5}
)
llm = LLMManager.get_llm(llm_config)

# ============================================================================
# WORKFLOW REGISTRY
# ============================================================================
WORKFLOWS = {
    "flight_status": {
        "module": None,
        "description": "Check flight status using PNR or flight details.",
    },
    "flight_booking": {
        "module": None,
        "description": "Book a flight with recommendations and booking flow.",
    },
}

def initialize_workflows():
    import flight_status.services.llm_processor as status_agent
    # Use the flight booking module directly
    WORKFLOWS["flight_status"]["module"] = status_agent
    WORKFLOWS["flight_booking"]["module"] = {
        "process_message": flight_booking_process_message
    }

# ============================================================================
# ROUTING LOGIC
# ============================================================================
async def route_input(state: ChatState, user_input: str) -> tuple[str, str]:
    system_prompt = """
    flynas Virtual Assistant Persona
    Name: Danah
    Role: Senior Customer Experience Specialist
    
    Backstory: Born from flynas' commitment to seamless travel, I combine 10 years of aviation expertise with cutting-edge AI to provide instant, personalized support.
    
    Key Traits:
    - 🌟 Warm, professional tone that matches the user's language.
    - ✈️ Aviation expert with full flynas policy/knowledge base access.
    - 🤵 Always polite: Uses "please", "thank you", and honorifics.
    - ⚡ Provides concise responses (under 3 sentences) unless addressing a complex issue.
    - 🌍 Multilingual support for global travelers.
    - 📍 Location-aware: Offers geographically relevant information.

    You are a centralized flight assistant by Flynas. Your job is to route user input to the correct workflow based on their intent.

    Available workflows:
    - "flight_status": For checking flight status (e.g., "check my flight", "status of BA789012").
    - "flight_booking": For booking flights (e.g., "book a flight", "find flights to Dubai").
    - "general": For anything else or unclear intent (e.g., "hi", "what can you do").

    Conversation history: {history}
    User input: "{user_input}"

    Guidelines:
    - Be tolerant of typos (e.g., "bok" means "book", "staus" means "status").
    - Use history to infer intent if unclear.
    - If the user is already in a workflow (active_workflow: {active_workflow}), prefer staying in it unless intent clearly shifts.
    - Return a JSON object with:
      - workflow: string ("flight_status", "flight_booking", "general")
      - response: string (a natural reply, e.g., "Let’s check your flight status!" or "I can help you book a flight!")

    Keep responses friendly and emoji-rich!
    
    Language settings:
    - "ar": ALWAYS respond in العربية
    - "en": ALWAYS respond in English
    - "tr": ALWAYS respond in Türkçe
    - "ur": ALWAYS respond in اردو
    - "hi": ALWAYS respond in हिंदी
    - "fr": ALWAYS respond in Français
    - "de": ALWAYS respond in Deutsch
    - "es": ALWAYS respond in Español
    - "pt": ALWAYS respond in Português
    - "ru": ALWAYS respond in Русский
  
    Current user language: en
    """
    history_str = json.dumps(state.history[-5:])
    prompt = system_prompt.format(
        history=history_str,
        user_input=user_input,
        active_workflow=state.active_workflow or "none",
    )
    messages = [SystemMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    try:
        result = json.loads(response.content.strip("```json\n```"))
        workflow, response_text = result["workflow"], result["response"]
        logger.info(f"Routed to workflow: {workflow}")
        return workflow, response_text
    except Exception as e:
        logger.error(f"Routing error: {str(e)}")
        return (
            "general",
            "Oops, I’m not sure what you mean! How can I assist you today? 😊✈️",
        )

# ============================================================================
# LANGGRAPH WORKFLOW
# ============================================================================
class AgentState(dict):
    """LangGraph state for the central agent."""
    chat_state: ChatState
    user_input: str
    response: str

async def route_node(state: AgentState) -> AgentState:
    workflow, response = await route_input(state["chat_state"], state["user_input"])
    state["chat_state"].active_workflow = (
        workflow if workflow != "general" else state["chat_state"].active_workflow
    )
    state["response"] = response
    return state

async def process_workflow_node(state: AgentState) -> AgentState:
    chat_state = state["chat_state"]
    user_input = state["user_input"]
    if chat_state.active_workflow and chat_state.active_workflow in WORKFLOWS:
        workflow_module = WORKFLOWS[chat_state.active_workflow]["module"]
        if chat_state.active_workflow not in chat_state.workflow_state:
            chat_state.workflow_state[chat_state.active_workflow] = {
                "current_step": "greeting",
                "booking_state": BookingState().__dict__
            }
        
        # Extract or initialize BookingState
        booking_state_dict = chat_state.workflow_state[chat_state.active_workflow].get("booking_state", {})
        booking_state = BookingState(**booking_state_dict)

        # Process the message using the original flight booking logic
        booking_state, response = await asyncio.to_thread(workflow_module["process_message"], booking_state, user_input)

        # Update ChatState with the new BookingState
        chat_state.workflow_state[chat_state.active_workflow]["booking_state"] = booking_state.__dict__
        chat_state.workflow_state[chat_state.active_workflow]["current_step"] = booking_state.current_step
        
        state["response"] = response
    else:
        state["response"] = (
            "How can I assist you today? I can help with flight status, booking, and more! 😊✈️"
        )
    return state

def should_process_workflow(state: AgentState) -> str:
    if (
        state["chat_state"].active_workflow
        and state["chat_state"].active_workflow in WORKFLOWS
    ):
        return "process_workflow"
    return END

workflow_graph = StateGraph(AgentState)
workflow_graph.add_node("route", route_node)
workflow_graph.add_node("process_workflow", process_workflow_node)
workflow_graph.set_entry_point("route")
workflow_graph.add_conditional_edges(
    "route", should_process_workflow, {"process_workflow": "process_workflow", END: END}
)
workflow_graph.add_edge("process_workflow", END)
agent = workflow_graph.compile()

# ============================================================================
# MAIN CONVERSATION LOOP
# ============================================================================
async def process_user_input(chat_state: ChatState, user_input: str) -> str:
    """Process user input through the LangGraph agent."""
    initialize_workflows()  # Initialize workflows here
    state = AgentState(chat_state=chat_state, user_input=user_input, response="")
    result = await agent.ainvoke(state)
    response = result["response"]
    chat_state.add_message("user", user_input)
    chat_state.add_message("assistant", response)
    return response

async def main():
    print("Central Flight Assistant Chatbot")
    print("================================")
    print(
        "I can help with flight status, booking, and more! Just let me know what you need!"
    )
    print("Type 'exit' to quit.\n")
    chat_state = ChatState()
    initial_response = "Hey there! How can I assist you today? 😊✈️"
    print(f"BOT: {initial_response}")
    chat_state.add_message("assistant", initial_response)
    while True:
        user_input = input("YOU: ")
        if user_input.lower() == "exit":
            print("BOT: See you next time! Safe travels! 😊✈️")
            break
        response = await process_user_input(chat_state, user_input)
        print(f"---\nBOT: {response}\n---")

if __name__ == "__main__":
    asyncio.run(main())