from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
from langchain_core.tools import Tool
from app.core.chatbot.utils import normalize_language_code
from app.core.chatbot.state import State
from app.core.chatbot.workflow_manager import WorkflowStep, workflow_manager


def generate_tool_descriptions(tools: list[Tool]) -> list[str]:
    return [f"{tool.name}: {tool.description}" for tool in tools] if tools else []

def get_formatted_prompt(state: State, base_prompt: str, tools: list = None, extra_context: dict = None) -> str:
    """
    Formats a prompt string with context information from the state.

    Args:
        state: The current conversation state.
        base_prompt: The prompt string to format.
        tools: A list of available tools.

    Returns:
        The formatted prompt string.
    """

    # Get current time in user's timezone, defaulting to UTC if not available
    current_time = datetime.now(ZoneInfo(state.get("timezone", "UTC")))

    # Handle location data safely - ensure it's always a dict
    location = state.get("location") or {}
    location_str = "Unknown location"
    try:
        if location:
            location_str = (
                f"{location.get('city', 'Unknown city')}, "
                f"{location.get('country', 'Unknown country')} "
                f"({location.get('latitude', '?')}, {location.get('longitude', '?')})"
            )
    except AttributeError:
        location_str = "Invalid location format"

    # Normalize language code, defaulting to 'en' if not available
    language = normalize_language_code(state.get("language", "en"))

    # Handle None case for extra_context
    extra_context = extra_context or {}
    
    # Create a dictionary of context variables to pass to the prompt
    vars = {**extra_context, **{
        "system_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
        "language": language,
        "location": location_str,
        "city": location.get('city', 'Not provided'),
        "country": location.get('country', 'Not provided'),
        "timezone": state.get("timezone", "UTC"),        
    }}
    
    tools = tools or []
    vars = {**vars, "tools": generate_tool_descriptions(tools)}

    # Add safe workflow data formatting with descriptive defaults
    workflow_data = extra_context.get("workflow_data", {})
    
    vars = {
        **vars,
        "workflow_data": workflow_data
    }
    
    return base_prompt.format(**vars)

    
    
    
    