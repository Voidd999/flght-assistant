
from app.core.chatbot.tools import search_docs
from app.core.chatbot.state import State
from app.core.chatbot.utils.prompt import get_formatted_prompt
from app.core.chatbot.llm_manager import LLMManager
from app.core.chatbot.utils.messages import clean_messages
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition
from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from app.core.chatbot.prompts import FAQ_PROMPT


async def faq_graph(llm: LLMManager, checkpointer: BaseCheckpointSaver):
  
  faq_tools = [search_docs]
  faq_llm = llm.bind_tools(faq_tools)

  async def faq_node(state: State):
      """
      Process FAQ queries using document search tools.
      
      Args:
          state: The current state
          
      Returns:
          Updated state with FAQ response
      """
      print("node: faq_node")
      
      formatted_system_prompt = get_formatted_prompt(state, FAQ_PROMPT, faq_tools)        
      faq_agent = create_react_agent(
          faq_llm,
          faq_tools,
          prompt=formatted_system_prompt
      )
      
      response = await faq_agent.ainvoke(state)
      
      # Clean FAQ response
      cleaned_messages = clean_messages(response["messages"])
      response["messages"] = cleaned_messages
      
      return response


  builder = StateGraph(State)
  builder.add_node("faq", faq_node)
  builder.add_node("tools", ToolNode(faq_tools))
  
  builder.add_conditional_edges("faq", tools_condition, {"tools", END})  
  builder.add_edge("tools", "faq")
  builder.add_edge("faq", END)
  
  builder.set_entry_point("faq")
  
  
  return builder.compile(checkpointer=checkpointer)