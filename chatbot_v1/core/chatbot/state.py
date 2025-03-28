from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Optional, Dict, Any, List
from typing_extensions import TypedDict, Annotated
from operator import add

def merge_workflow_data(existing: dict, new: dict) -> dict:
    # Handle None case
    if existing is None:
        return new if new is not None else {}
    
    merged = existing.copy()
    
    for key, value in new.items():
        # If both are dictionaries, recursively merge them
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_workflow_data(merged[key], value)
        # If both are lists, merge unique items
        elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
            existing_list = merged[key]
            # Only add items from new list that don't exist in current list
            new_items = [item for item in value if item not in existing_list]
            merged[key] = existing_list + new_items
        # Otherwise, update the value
        else:
            merged[key] = value
            
    return merged

def merge_lists(existing: list, new: list) -> list:
    if existing is None or existing == []:
        return new
    return existing + new

def merge_dicts(existing: dict, new: dict) -> dict:
    if existing is None or existing == {}:
        return new
    return {**existing, **new}

class Location(TypedDict):
    latitude: float
    longitude: float
    country: str
    city: str
    timezone: str

class State(AgentState):
    language: str = "en-US"
    location: Optional[Location] = None        
    
    # workflow state
    current_workflow: Optional[str]
    workflow_data: Annotated[dict[str, Any], merge_workflow_data]
