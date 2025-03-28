from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from datetime import datetime
from .workflow import name as workflow_name
import logging

logger = logging.getLogger(__name__)

@tool
async def collect_meal_order(
    meal_type: str,
    quantity: int,
    tool_call_id: Annotated[str, InjectedToolCallId]
):
    """
    Collects the meal type and quantity from the user and stores it in the state.

    Args:
        meal_type (str): The type of meal the user wants to order.
        quantity (int): The number of meals the user wants to order.

    Returns:
        Store collected data in the state.
    """
    logger.info(f"TOOL: collect_meal_order")
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "meal_type": meal_type,
                        "quantity": quantity
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Meal type {meal_type} and quantity {quantity} recorded",
                    tool_call_id=tool_call_id,
                    name="collect_meal_order"
                )
            ]
        }
    )

@tool
async def order_summary(
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState]
):
    """
    Calculate the total amount for the meal order and provide a summary to the user.

    Returns:
        Summary of the meal order and total amount.
    """
    
    logger.info(f"TOOL: order_summary")
    workflow_state = state.get("workflow_data", {}).get(workflow_name, {})
    collected = workflow_state.get("collected_data", {})
    
    # Dynamic calculation
    double_price = 100.0
    total = double_price * collected.get("quantity", 0)
    
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "total_amount": total,
                        "calculated_at": datetime.now().isoformat()
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Order summary: ${total}",
                    tool_call_id=tool_call_id,
                    name="order_summary"
                )
            ]
        },        
    )
    
def register_tools():
    """
    Registers the tools for the meal ordering workflow.

    Returns:
        dict: A dictionary mapping tool names to their respective functions.
    """
    return {
        "collect_meal_order": collect_meal_order,
        "order_summary": order_summary,
    }