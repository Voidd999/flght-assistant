from chatbot_v2.agent import ChatState  # Use centralized ChatState
from flight_status.utils.logger import logger


def check_dependencies(state: ChatState, intent: str) -> list:
    """Check if required data is present based on intent."""
    ws = state.workflow_state.get("flight_status", {})
    missing = []
    if intent == "check_status_pnr" and not ws.get("pnr"):
        missing.append("pnr")
    elif intent == "check_status_details":
        flight_details = ws.get("flight_details", {})
        if not flight_details.get("date"):
            missing.append("date")
        if not flight_details.get("origin"):
            missing.append("origin")
        if not flight_details.get("destination"):
            missing.append("destination")
    if missing:
        logger.info(f"Dependencies missing for intent {intent}: {missing}")
    return missing
