from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command
from .workflow import name as workflow_name
import logging

# Set up logger
logger = logging.getLogger(__name__)

@tool
async def collect_claim_number(
    claim_number: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
):
    """
    Collect the baggage claim number from the user and store it in the state.

    Args:
        claim_number (str): The baggage claim number provided by the user.

    Returns:
        Claim number recorded in the state.
    """
    logger.info("TOOL: collect_claim_number")
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "claim_number": claim_number
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Claim number {claim_number}  collected, I will now check the status of the baggage claim",
                    tool_call_id=tool_call_id,
                    name="collect_claim_number"
                )
            ]
        }
    )

@tool
async def check_baggage_status(
    claim_number: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState]
):
    """
    Check the baggage claim status from the backend system.

    Args:
        claim_number (str): The baggage claim number to check status for.

    Returns:
        Baggage status, compensation amount, and last update information.
    """
    logger.info("TOOL: check_baggage_status")
    # Mock response - replace with actual API call
    mock_responses = {
        "ABC123456": {
            "status": "COMPENSATION_APPROVED",
            "last_update": "2024-02-15",
            "compensation": 1500.00
        },
        "DEF654321": {
            "status": "IN_REVIEW",
            "last_update": "2024-02-14",
            "compensation": 0.00
        }
    }
    
    result = mock_responses.get(claim_number, {
        "status": "NOT_FOUND",
        "last_update": "N/A",
        "compensation": 0.00
    })
    
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "status": result["status"],
                        "compensation_amount": result["compensation"],
                        "last_update": result["last_update"]
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Status check complete for {claim_number} - status: {result['status']}, compensation: {result['compensation']}, last update: {result['last_update']}",
                    tool_call_id=tool_call_id,
                    name="check_baggage_status"
                )
            ]
        }
    )

def register_tools():
    """Register tools for the baggage tracking workflow"""
    logger.info("TOOL: Registering baggage tracking tools")
    return {
        "collect_claim_number": collect_claim_number,
        "check_baggage_status": check_baggage_status
    }