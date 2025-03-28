import os

from typing import Annotated, List, Dict, Optional
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from .workflow import name as workflow_name
import logging

logger = logging.getLogger(__name__)

@tool
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str],
    passengers: int,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Search for available flights between cities on a specific date.

    Args:
        origin (str): The city of origin for the flight.
        destination (str): The destination city for the flight.
        departure_date (str): The date of departure in YYYY-MM-DD format.
        return_date (Optional[str]): The date of return in YYYY-MM-DD format (if applicable).
        passengers (int): The number of passengers traveling.

    Returns:
        List of available flights that match the search parameters.
    """
    logger.info(f"TOOL: search_flights")
    # PHYSICAL INPUT VALIDATION
    if not all([origin, destination, departure_date, passengers]):
        raise ValueError("Missing required search parameters")
    
    # Implement simplified flight search logic here
    flights = [
        {"flight_number": "XY123", "departure": "08:00", "arrival": "10:00", "price": 300},
        {"flight_number": "XY456", "departure": "12:00", "arrival": "14:00", "price": 450},
        {"flight_number": "XY789", "departure": "16:00", "arrival": "18:00", "price": 600}
    ]
    
    command = Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "available_options": flights,
                        "search_params": f"{origin}-{destination}-{departure_date}",
                        "origin": origin,
                        "destination": destination,
                        "departure_date": departure_date,
                        "return_date": return_date,
                        "passengers_count": passengers,
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Found {len(flights)} flights: {flights}",
                    tool_call_id=tool_call_id,
                    name="search_flights"
                )
            ]
        }
    )
    
    return command

@tool
async def select_flight(
    flight_number: str,
    available_options: list,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Select a specific flight by flight number.

    Args:
        flight_number (str): The flight number to select.
        available_options (list): A list of available flight options.

    Returns:
        The selected flight information.
    """
    logger.info(f"TOOL: select_flight")
    # PHYSICAL SELECTION VALIDATION
    
    selected = next((f for f in available_options if f["flight_number"] == flight_number), None)
    if not selected:
        raise ValueError("Invalid flight selection")
    
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "selected_flight": selected,
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Selected flight {selected}",
                    tool_call_id=tool_call_id,
                    name="select_flight"
                )
            ]
        }
    )

@tool
async def collect_passenger_info(
    first_name: Annotated[str, "Passenger's first name"],
    last_name: Annotated[str, "Passenger's last name"],
    dob: Annotated[str, "Date of birth in YYYY-MM-DD format"],
    passport_number: Annotated[str, "Passport number"],
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState]
) -> Command:
    """
    Collect a passenger information and store it in state.

    Args:
        first_name (str): Passenger's first name.
        last_name (str): Passenger's last name.
        dob (str): Passenger's date of birth in YYYY-MM-DD format.
        passport_number (str): Passenger's passport number.

    Returns:
        The collected passenger information.
    """
    logger.info(f"TOOL: collect_passenger_info")
    passenger_info = {
            "first_name": first_name,
            "last_name": last_name,
            "dob": dob,
            "passport_number": passport_number
        }

    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "passengers": [passenger_info]
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Passenger info collected: {passenger_info}", 
                    tool_call_id=tool_call_id, 
                    name="collect_passenger_info"
                )
            ]
        }
    )

@tool
async def collect_contact_info(
    email: str,
    phone: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Collect contact information from the user.

    Args:
        email (str): The user's email address.
        phone (str): The user's phone number.

    Returns:
        The collected contact information.
    """
    logger.info(f"TOOL: collect_contact_info")
    contact_info = {
        "email": email,
        "phone": phone
    }
    
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": { 
                        "contact_info": contact_info
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Contact info collected: {contact_info}",
                    tool_call_id=tool_call_id,
                    name="collect_contact_info"
                )
            ]   
        }
    )

@tool
async def collect_payment_info(
    card_number: str,
    expiration: str,
    cvv: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Collect payment information and store it in state.

    Args:
        card_number (str): The credit card number.
        expiration (str): The expiration date of the card.
        cvv (str): The CVV of the card.

    Returns:
        The collected payment information.
    """
    logger.info(f"TOOL: collect_payment_info")
    total_amount = state.get("workflow_data", {}).get(
        workflow_name, {}).get("collected_data", {}).get("total_amount", 0)
    
    payment_info = {
        "card_number": card_number,
        "expiration": expiration,
        "cvv": cvv,
        "amount": total_amount
    }
    
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "payment": payment_info
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=f"Payment of ${total_amount} processed successfully", 
                    tool_call_id=tool_call_id, 
                    name="collect_payment_info"
                )
            ]
        }
    )

@tool
async def booking_summary(
    state: Annotated[dict, InjectedState], 
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Generate booking summary based on the collected data from user for user confirmation.

    Returns:
        The booking summary details.
    """
    logger.info(f"TOOL: booking_summary")
    
    collected_data = state.get("workflow_data", {}) \
                .get(workflow_name, {}) \
                .get("collected_data", {})
                
    booking_details = {
        "flight": collected_data.get("selected_flight", ""),
        "passengers": collected_data.get("passengers", []),
        "payment": collected_data.get("payment", {}),
    }

    # Format human-readable message
    details_message = f"""
    Booking Summary
    ==========================
    ✈️ Flight: {booking_details['flight'].get('flight_number')}
    📅 Date: {collected_data.get('date')}
    👥 Passengers: {len(booking_details['passengers'])} travelers
    💳 Payment: ****-****-****-{booking_details['payment'].get('card_number', '')[-4:]}
    
    ==========================
    Please confirm the booking details above to proceed with the booking.
    """

    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "booking_details": booking_details
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content=details_message.strip(), 
                    tool_call_id=tool_call_id, 
                    name="booking_summary"
                )
            ]
        }
    )

@tool
async def book_flight(
    state: Annotated[dict, InjectedState], 
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Book the flight based on the collected data and confirmationfrom user.
    
    Returns:
        The final booking confirmation details.
    """
    logger.info(f"TOOL: book_flight")
    
    collected_data = state.get("workflow_data", {}) \
                .get(workflow_name, {}) \
                .get("collected_data", {})
    
    # check if we are waiting for user confirmation
    # pending_user_confirmation = collected_data.get("pending_user_confirmation", False)
    # if pending_user_confirmation:
    #     return Command(update={
    #         "messages": [
    #             ToolMessage(
    #                 content=f"Confirm the booking details above to proceed with the booking.",
    #                 tool_call_id=tool_call_id,
    #                 name="book_flight"
    #             )
    #         ]
    #     })
    
    booking = collected_data.get("booking_details", {})

    pnr = os.urandom(3).hex().upper() 
    summary = f"""
    Booking Confirmation
    ==========================
    🔖 Reference (PNR): {pnr}
    ✈️ Flight: {booking.get('flight', {}).get('flight_number', 'N/A')}
    📅 Date: {booking.get('flight', {}).get('date', 'N/A')}
    👥 Passengers: {len(booking.get('passengers', []))} travelers
    💳 Payment: ****-****-****-{booking.get('payment', {}).get('card_number', '')[-4:]}
    """
    
    return Command(
        update={
            "current_workflow": None,
            "workflow_data": {workflow_name: None},
            "messages": [
                ToolMessage(
                    content=summary.strip(),
                    tool_call_id=tool_call_id,
                    name="book_flight"
                )
            ]
        }
    )
    
    
def register_tools() -> Dict[str, callable]:
    """
    Register all flight booking tools.

    Returns:
        Dict[str, callable]: A dictionary mapping tool names to their respective functions.
    """
    return {
        "search_flights": search_flights,
        "select_flight": select_flight,
        "collect_passenger_info": collect_passenger_info,
        "collect_contact_info": collect_contact_info,
        "collect_payment_info": collect_payment_info,
        "booking_summary": booking_summary,
        "book_flight": book_flight,
    }