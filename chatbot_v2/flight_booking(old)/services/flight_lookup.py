from typing import Optional, Dict, Any
from flight_booking.data.mock_data import FLIGHT_AVAILABILITY
from chatbot_v2.agent import ChatState


def get_selected_flight(state: ChatState) -> Optional[Dict[str, Any]]:
    """Get the selected flight details"""
    ws = state.workflow_state
    if (
        not ws.get("selected_flight_id")
        or not ws.get("origin")
        or not ws.get("destination")
        or not ws.get("departure_date")
    ):
        return None

    route = f"{ws['origin']}-{ws['destination']}"
    if (
        route not in FLIGHT_AVAILABILITY
        or ws["departure_date"] not in FLIGHT_AVAILABILITY[route]
    ):
        return None

    flights = FLIGHT_AVAILABILITY[route][ws["departure_date"]]
    for flight in flights:
        if flight["id"] == ws["selected_flight_id"]:
            return flight

    return None
