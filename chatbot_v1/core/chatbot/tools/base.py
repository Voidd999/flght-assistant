from typing import Dict, List, Optional, Type, Literal, Annotated
from pydantic import BaseModel
from langchain_core.tools import BaseTool, tool
from typing import Any
from langgraph.types import Command, interrupt
from langgraph.prebuilt import InjectedState
from langchain_core.messages import ToolMessage
@tool
def ask_for_confirmation(state: Annotated[dict, InjectedState]) -> Command:
    """
    Ask the user for confirmation of the current action.
    """
    print("TOOL: ask_for_confirmation")
    
    last_message = state["messages"][-1]
    message_content = last_message.content
    workflow_name = state.get("current_workflow", None)
    if workflow_name is None:
        raise ValueError("Workflow name is not set")
    
    return Command(
        update={
             "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "pending_user_confirmation": True
                    }
                }
            },       
            "messages": [
                ToolMessage(
                    content=f"Confirm the action for {workflow_name}",
                    tool_call_id=last_message.tool_call_id,
                    name="ask_for_confirmation"
                )
            ]
        }
    )


BASE_TOOLS = {
    "ask_for_confirmation": ask_for_confirmation,
}
