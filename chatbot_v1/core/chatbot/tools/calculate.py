"""Calculate tool for arithmetic operations."""

from typing import Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

@tool
def calculate(expression: str, state: Annotated[dict, InjectedState]) -> float:
    """Calculate the result of an arithmetic expression."""
    result = eval(expression)
    return result 