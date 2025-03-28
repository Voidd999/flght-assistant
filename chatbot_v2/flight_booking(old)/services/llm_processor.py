import json
from typing import Dict, Any, Tuple
from flight_booking.config.settings import llm
from flight_booking.data.mock_data import FLIGHT_AVAILABILITY
from flight_booking.services.date_utils import (
    get_current_date,
    format_date_for_system,
    is_valid_booking_date,
)
from flight_booking.utils.logger import logger
from langchain_core.messages import SystemMessage, HumanMessage
from chatbot_v2.models import ChatState
import random
import string


async def parse_user_intent(state: ChatState, user_input: str) -> Dict[str, Any]:
    ws = state.workflow_state.get("flight_booking", {})
    context = get_conversation_context(state)
    today_date = format_date_for_system(get_current_date())

    available_origins = set()
    available_destinations = set()
    for route in FLIGHT_AVAILABILITY.keys():
        origin, destination = route.split("-")
        available_origins.add(origin)
        available_destinations.add(destination)

    available_routes_info = ""
    for route, date_flights in FLIGHT_AVAILABILITY.items():
        origin, destination = route.split("-")
        dates = list(date_flights.keys())
        available_routes_info += (
            f"- {origin} to {destination}: Available on {', '.join(dates)}\n"
        )
        for date, flights in date_flights.items():
            available_routes_info += f"  Flights on {date}:\n"
            for flight in flights:
                available_routes_info += (
                    f"    - ID: {flight['id']}, Airline: {flight['airline']}, "
                )
                available_routes_info += f"Flight#: {flight['flight_number']}, "
                available_routes_info += (
                    f"Time: {flight['departure_time']} to {flight['arrival_time']}, "
                )
                available_routes_info += f"Price: ${flight['price']}\n"

    system_prompt = f"""You are an AI flight booking assistant analyzing user inputs to extract relevant information and determine the conversation flow. 

CURRENT BOOKING STATE:
{context}

TODAY'S DATE:
Today is {today_date}. The user might refer to dates relatively like "tomorrow", "next week", etc.

AVAILABLE ORIGINS AND DESTINATIONS:
We ONLY have the following routes and dates available in our system:
{available_routes_info}

CRITICAL INSTRUCTIONS:
1. You MUST extract the selected_flight_id if the user selects a specific flight
2. If the user mentions a flight, check if it matches an actual flight ID from our database
3. If the user mentions a flight but doesn't specify an ID, set the next_step to "show_flights"
4. If the user asks about flight details, set the next_step to "show_flights"
5. NEVER extract destinations we don't serve
6. The only valid origins are: {', '.join(available_origins)}
7. The only valid destinations are: {', '.join(available_destinations)}

YOUR TASK:
Analyze the user's message and extract all relevant booking information. Based on what information we already have and what the user has just provided, determine what we should do next.

When the user mentions dates:
1. If they use relative terms like "tomorrow", "next Friday", etc., convert them to MM/DD/YYYY format relative to today's date ({today_date}).
2. Reject any dates that are in the past.

Return a JSON object with these fields:
1. "extracted_info": Dictionary of information extracted from the user's message
   - "origin": City of departure, if mentioned
   - "destination": City of arrival, if mentioned
   - "departure_date": Departure date in MM/DD/YYYY format, if mentioned
   - "return_date": Return date in MM/DD/YYYY format, if mentioned
   - "is_one_way": Boolean, true if user explicitly asks for one-way, false if round trip
   - "passenger_count": Number of passengers, if mentioned
   - "selected_flight_id": Flight ID if user selects a specific flight
   - For each passenger mentioned:
     - "passenger_N_name": Full name for the Nth passenger
     - "passenger_N_dob": Date of birth in MM/DD/YYYY format
     - "passenger_N_passport": Passport number

"intent": The primary user intent (one of these values):
"provide_info": User is giving requested information
"change_info": User wants to change previously provided information
"ask_question": User is asking a question
"confirm": User is confirming something
"start_over": User wants to start over
"complete_booking": User wants to complete the booking

"next_step": What we should do next (one of these values):
"ask_origin": We need to ask for origin
"ask_destination": We need to ask for destination
"ask_dates": We need to ask for travel dates
"show_flights": We should show available flights
"ask_flight_selection": We need to ask which flight they want
"ask_passenger_count": We need to ask how many passengers
"ask_passenger_details": We need to ask for passenger details
"confirm_booking": We should confirm all details before completing
"complete_booking": We should complete the booking
"answer_question": We should answer their question

"missing_info": List of fields still needed to complete the booking

"needs_clarification": Boolean, true if the user's message is unclear and we need to ask for clarification
"clarification_message": Message explaining what we need clarified, if needs_clarification is true

"date_validation": {{
  "valid_departure_date": Boolean indicating if departure date is valid,
  "valid_return_date": Boolean indicating if return date is valid,
  "date_error_message": String with error message if dates are invalid
}}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f'User message: "{user_input}"'),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()

        intent_data = json.loads(content)
        logger.debug(f"Parsed intent: {json.dumps(intent_data, indent=2)}")
        return intent_data
    except Exception as e:
        logger.error(f"Error parsing user intent: {str(e)}")
        return {
            "extracted_info": {},
            "intent": "provide_info",
            "next_step": "ask_origin" if not ws.get("origin") else "ask_destination",
            "missing_info": ["origin", "destination", "dates"],
            "needs_clarification": True,
            "clarification_message": "I'm having trouble understanding. Could you please rephrase that?",
            "date_validation": {
                "valid_departure_date": True,
                "valid_return_date": True,
                "date_error_message": None,
            },
        }


def get_conversation_context(state: ChatState) -> str:
    """Get the conversation context for the LLM"""
    from flight_booking.services.date_utils import (
        format_date_for_system,
        get_current_date,
    )

    ws = state.workflow_state.get("flight_booking", {})

    context = []
    current_date = format_date_for_system(get_current_date())
    context.append(f"Current date: {current_date}")

    if ws.get("origin"):
        context.append(f"Origin: {ws['origin']}")

    if ws.get("destination"):
        context.append(f"Destination: {ws['destination']}")

    if ws.get("departure_date"):
        context.append(f"Departure date: {ws['departure_date']}")
        if ws.get("is_one_way"):
            context.append("This is a one-way trip")
        elif ws.get("return_date"):
            context.append(f"Return date: {ws['return_date']}")

    if ws.get("selected_flight_id"):
        selected_flight = get_selected_flight(state)
        if selected_flight:
            context.append(
                f"Selected flight: {selected_flight['airline']} {selected_flight['flight_number']}"
            )
            context.append(f"Departure time: {selected_flight['departure_time']}")
            context.append(f"Arrival time: {selected_flight['arrival_time']}")
            context.append(f"Price: ${selected_flight['price']} per passenger")

    if ws.get("passenger_count"):
        context.append(f"Number of passengers: {ws['passenger_count']}")
        if ws.get("passenger_details"):
            context.append("Passenger details:")
            for i, passenger in enumerate(ws["passenger_details"], 1):
                completed_fields = []
                if passenger.get("name"):
                    completed_fields.append(f"name: {passenger['name']}")
                if passenger.get("dob"):
                    completed_fields.append(f"DOB: {passenger['dob']}")
                if passenger.get("passport"):
                    completed_fields.append(f"passport: {passenger['passport']}")
                if completed_fields:
                    context.append(f"  Passenger {i}: {', '.join(completed_fields)}")

    if ws.get("booking_reference"):
        context.append(f"Booking reference: {ws['booking_reference']}")
        context.append(
            f"Booking status: {'Complete' if ws.get('is_complete') else 'In progress'}"
        )

    context.append(f"Current step: {ws.get('current_step', 'ask_origin')}")

    return "\n".join(context)


def get_selected_flight(state: ChatState) -> Dict[str, Any]:
    """Get the selected flight details"""
    ws = state.workflow_state.get("flight_booking", {})
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


async def generate_response(
    state: ChatState, intent_data: Dict[str, Any], user_input: str
) -> str:
    ws = state.workflow_state.get("flight_booking", {})
    messages_context = []
    for message in state.history[-10:]:
        if message["role"] == "user":
            messages_context.append(f"User: {message['content']}")
        else:
            messages_context.append(f"Assistant: {message['content']}")

    context = get_conversation_context(state)
    today_date = format_date_for_system(get_current_date())

    available_routes_info = ""
    for route, date_flights in FLIGHT_AVAILABILITY.items():
        origin, destination = route.split("-")
        dates = list(date_flights.keys())
        available_routes_info += (
            f"- {origin} to {destination}: Available on {', '.join(dates)}\n"
        )

    flights_to_show = ""
    if ws.get("origin") and ws.get("destination") and ws.get("departure_date"):
        route = f"{ws['origin']}-{ws['destination']}"
        if (
            route in FLIGHT_AVAILABILITY
            and ws["departure_date"] in FLIGHT_AVAILABILITY[route]
        ):
            flights = FLIGHT_AVAILABILITY[route][ws["departure_date"]]
            for i, flight in enumerate(flights, 1):
                flights_to_show += f"{i}. **Flight ID: {flight['id']}**\n"
                flights_to_show += f"   Airline: {flight['airline']}\n"
                flights_to_show += f"   Flight Number: {flight['flight_number']}\n"
                flights_to_show += f"   Departure: {flight['departure_time']}\n"
                flights_to_show += f"   Arrival: {flight['arrival_time']}\n"
                flights_to_show += f"   Price: ${flight['price']}\n\n"

    date_validation = intent_data.get("date_validation", {})
    date_error_message = ""
    if not date_validation.get("valid_departure_date", True):
        date_error_message = "I notice you've selected a departure date that's in the past. Please choose a date from today onwards."
    elif not date_validation.get("valid_return_date", True):
        date_error_message = "The return date you've selected appears to be invalid. Please ensure it's after your departure date and not in the past."
    elif date_validation.get("date_error_message"):
        date_error_message = date_validation.get("date_error_message")

    system_prompt = f"""You are a friendly and helpful airline booking assistant. Your job is to have a natural, helpful conversation with the customer to help them book a flight.

CURRENT BOOKING STATE:
{context}

TODAY'S DATE:
Today is {today_date}. When discussing dates, refer to them in a natural way while making clear what actual date you're referring to.

USER INTENT:
{json.dumps(intent_data, indent=2)}

RECENT CONVERSATION:
{chr(10).join(messages_context)}

CURRENT USER INPUT:
"{user_input}"

{date_error_message}

AVAILABLE ROUTES IN OUR SYSTEM:
{available_routes_info}

CONVERSATION FLOW REQUIREMENTS:
1. If next_step is "ask_origin", ask "Where would you like to fly from?"
2. If next_step is "ask_destination", ask "Where are you flying to?"
3. If next_step is "ask_dates", ask "When would you like to travel?"
4. If next_step is "ask_flight_selection" or "show_flights", we’ll handle flight display outside this prompt
5. If next_step is "ask_passenger_count", ask "How many passengers will be traveling?"
6. If next_step is "ask_passenger_details", ask "Please provide your full name, date of birth (MM/DD/YYYY), and passport number."
7. If next_step is "confirm_booking" or "complete_booking", we’ll handle it outside this prompt
8. If next_step is "answer_question", respond to the user’s question naturally

YOUR TASK:
Respond naturally as a helpful booking assistant. Be conversational, friendly, and patient. Acknowledge what the user has said and what information they've provided. Ask for the next piece of information needed in a natural way based on the next_step.

- Do NOT invent flight details or show flights here; flight display is handled programmatically.
- If there’s a date validation error, politely explain it and ask for a valid date.
- Keep responses concise, warm, and professional with a human-like tone.
- If the user wants to change something, acknowledge it positively and adjust accordingly.
- If the intent is unclear, ask for clarification politely.

IMPORTANT CONSTRAINTS:
1. NEVER make up flights, routes, or dates. Flight details are provided programmatically.
2. Only use the routes and dates listed in AVAILABLE ROUTES IN OUR SYSTEM.
3. Do not provide specific airport names (like Heathrow or DXB) as these aren’t in our database.
"""

    messages = [SystemMessage(content=system_prompt)]

    try:
        response = await llm.ainvoke(messages)
        logger.debug(f"Generated response: {response.content}")
        return response.content
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I apologize, but I'm having trouble processing your request right now. Could you please try again or rephrase your question?"


def update_booking_state(state: ChatState, intent_data: Dict[str, Any]) -> ChatState:
    ws = state.workflow_state.get("flight_booking", {})
    state.workflow_state["flight_booking"] = ws  # Ensure workflow_state is set
    extracted_info = intent_data.get("extracted_info", {})
    date_validation = intent_data.get("date_validation", {})
    valid_departure_date = date_validation.get("valid_departure_date", True)
    valid_return_date = date_validation.get("valid_return_date", True)

    if "origin" in extracted_info and extracted_info["origin"]:
        ws["origin"] = extracted_info["origin"].strip().title()

    if "destination" in extracted_info and extracted_info["destination"]:
        ws["destination"] = extracted_info["destination"].strip().title()

    if (
        "departure_date" in extracted_info
        and extracted_info["departure_date"]
        and valid_departure_date
    ):
        date_text = extracted_info["departure_date"]
        is_valid, formatted_date = is_valid_booking_date(date_text)
        if is_valid:
            ws["departure_date"] = formatted_date

    if (
        "return_date" in extracted_info
        and extracted_info["return_date"]
        and valid_return_date
    ):
        date_text = extracted_info["return_date"]
        is_valid, formatted_date = is_valid_booking_date(date_text)
        if is_valid:
            ws["return_date"] = formatted_date
            ws["is_one_way"] = False

    if "is_one_way" in extracted_info:
        ws["is_one_way"] = extracted_info["is_one_way"]
        if ws["is_one_way"]:
            ws["return_date"] = None

    if "passenger_count" in extracted_info and extracted_info["passenger_count"]:
        try:
            count = int(extracted_info["passenger_count"])
            if 1 <= count <= 9:
                ws["passenger_count"] = count
                if "passenger_details" not in ws:
                    ws["passenger_details"] = []
                while len(ws["passenger_details"]) < count:
                    ws["passenger_details"].append(
                        {"name": "", "dob": "", "passport": "", "is_complete": False}
                    )
        except (ValueError, TypeError):
            pass

    if "selected_flight_id" in extracted_info and extracted_info["selected_flight_id"]:
        ws["selected_flight_id"] = extracted_info["selected_flight_id"]

    passenger_updates = {}
    for key, value in extracted_info.items():
        if key.startswith("passenger_") and "_" in key[10:]:
            try:
                parts = key.split("_")
                if len(parts) >= 3:
                    idx = int(parts[1]) - 1
                    field = parts[2]
                    if idx not in passenger_updates:
                        passenger_updates[idx] = {}
                    passenger_updates[idx][field] = value
            except (ValueError, IndexError):
                pass

    for idx, updates in passenger_updates.items():
        if "passenger_details" not in ws:
            ws["passenger_details"] = []
        while len(ws["passenger_details"]) <= idx:
            ws["passenger_details"].append(
                {"name": "", "dob": "", "passport": "", "is_complete": False}
            )
        passenger = ws["passenger_details"][idx]
        if "name" in updates:
            passenger["name"] = updates["name"]
        if "dob" in updates:
            passenger["dob"] = updates["dob"]
        if "passport" in updates:
            passenger["passport"] = updates["passport"]
        passenger["is_complete"] = bool(
            passenger["name"] and passenger["dob"] and passenger["passport"]
        )

    next_step = intent_data.get("next_step")
    if next_step:
        ws["current_step"] = next_step

    # Check if all required data is present to move to confirm_booking
    if (
        ws.get("selected_flight_id")
        and ws.get("passenger_details")
        and all(p["is_complete"] for p in ws["passenger_details"])
        and ws.get("current_step") not in ["confirm_booking", "complete_booking"]
    ):
        ws["current_step"] = "confirm_booking"

    # Move to complete_booking only after explicit confirmation
    if (
        intent_data.get("intent") == "confirm"
        and ws.get("current_step") == "confirm_booking"
    ):
        ws["current_step"] = "complete_booking"

    if ws.get("current_step") == "complete_booking" and not ws.get("booking_reference"):
        selected_flight = get_selected_flight(state)
        if selected_flight:
            airline_code = selected_flight["flight_number"][:2]
            random_part = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=6)
            )
            ws["booking_reference"] = f"{airline_code}{random_part}"
            ws["is_complete"] = True

    return state


async def process_message(state: ChatState, user_input: str) -> Tuple[ChatState, str]:
    ws = state.workflow_state.get("flight_booking", {})
    if not ws:  # Initialize workflow state if empty
        ws = {"current_step": "ask_origin"}
    state.workflow_state["flight_booking"] = ws  # Ensure workflow_state is set
    state.add_message("user", user_input)

    available_cities = set()
    for route in FLIGHT_AVAILABILITY.keys():
        origin, destination = route.split("-")
        available_cities.add(origin.lower())
        available_cities.add(destination.lower())

    changed_destination = False
    prev_destination = ws.get("destination")

    if ("change" in user_input.lower() and "destination" in user_input.lower()) or (
        ws.get("destination")
        and any(
            city.lower() in user_input.lower()
            for city in available_cities
            if city.lower() != ws["destination"].lower()
        )
    ):
        ws["selected_flight_id"] = None
        ws["current_step"] = "show_flights"
        changed_destination = True

    if (
        ws.get("origin")
        and ws.get("destination")
        and ws.get("departure_date")
        and (
            "flight" in user_input.lower()
            or "show" in user_input.lower()
            or "available" in user_input.lower()
            or "option" in user_input.lower()
            or ws.get("current_step") == "show_flights"
        )
    ):
        ws["current_step"] = "show_flights"

    intent_data = await parse_user_intent(state, user_input)

    extracted_flight_id = None
    if (
        "extracted_info" in intent_data
        and "selected_flight_id" in intent_data["extracted_info"]
    ):
        extracted_flight_id = intent_data["extracted_info"]["selected_flight_id"]

    if (
        not extracted_flight_id
        and ws.get("origin")
        and ws.get("destination")
        and ws.get("departure_date")
    ):
        route = f"{ws['origin']}-{ws['destination']}"
        if (
            route in FLIGHT_AVAILABILITY
            and ws["departure_date"] in FLIGHT_AVAILABILITY[route]
        ):
            flights = FLIGHT_AVAILABILITY[route][ws["departure_date"]]
            for flight in flights:
                if flight["id"].lower() in user_input.lower():
                    intent_data["extracted_info"]["selected_flight_id"] = flight["id"]
                    intent_data["next_step"] = "ask_passenger_details"
                    break
            if not extracted_flight_id:
                for index_word in [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "one",
                    "two",
                    "three",
                    "four",
                    "five",
                    "first",
                    "second",
                    "third",
                    "fourth",
                    "fifth",
                ]:
                    if index_word in user_input.lower():
                        try:
                            if index_word == "one" or index_word == "first":
                                index = 0
                            elif index_word == "two" or index_word == "second":
                                index = 1
                            elif index_word == "three" or index_word == "third":
                                index = 2
                            elif index_word == "four" or index_word == "fourth":
                                index = 3
                            elif index_word == "five" or index_word == "fifth":
                                index = 4
                            else:
                                index = int(index_word) - 1
                            if 0 <= index < len(flights):
                                intent_data["extracted_info"]["selected_flight_id"] = (
                                    flights[index]["id"]
                                )
                                intent_data["next_step"] = "ask_passenger_details"
                                break
                        except ValueError:
                            pass

    state = update_booking_state(state, intent_data)

    if changed_destination or (
        prev_destination and prev_destination != ws.get("destination")
    ):
        ws["selected_flight_id"] = None
        ws["current_step"] = "show_flights"

    # Handle show_flights step with exact mock data
    if ws.get("current_step") == "show_flights":
        origin = ws.get("origin")
        destination = ws.get("destination")
        departure_date = ws.get("departure_date")
        if origin and destination and departure_date:
            route = f"{origin}-{destination}"
            if (
                route in FLIGHT_AVAILABILITY
                and departure_date in FLIGHT_AVAILABILITY[route]
            ):
                flights = FLIGHT_AVAILABILITY[route][departure_date]
                response = f"Here are the available flights from {origin} to {destination} on {departure_date}:\n\n"
                for i, flight in enumerate(flights, 1):
                    response += f"{i}. **Flight ID: {flight['id']}**\n"
                    response += f"   Airline: {flight['airline']}\n"
                    response += f"   Flight Number: {flight['flight_number']}\n"
                    response += f"   Departure: {flight['departure_time']}\n"
                    response += f"   Arrival: {flight['arrival_time']}\n"
                    response += f"   Price: ${flight['price']}\n\n"
                response += (
                    "Please select a flight by its Flight ID (e.g., LD1001). 😊✈️"
                )
                state.add_message("assistant", response)
                return state, response
            else:
                available_dates = list(FLIGHT_AVAILABILITY.get(route, {}).keys())
                response = f"Sorry, no flights are available from {origin} to {destination} on {departure_date}. "
                if available_dates:
                    response += f"We have flights on these dates: {', '.join(available_dates)}. Would you like to choose a different date?"
                else:
                    response += "We don’t have any scheduled flights for this route. Try a different route or date!"
                state.add_message("assistant", response)
                return state, response

    # Handle confirm_booking step with exact mock data
    if (
        ws.get("current_step") == "confirm_booking"
        and not intent_data.get("intent") == "confirm"
    ):
        selected_flight = get_selected_flight(state)
        if selected_flight and ws.get("passenger_details"):
            summary = (
                f"Let’s review your booking details:\n\n"
                f"Flight Details:\n"
                f"- Flight ID: {selected_flight['id']}\n"
                f"- Airline: {selected_flight['airline']}\n"
                f"- Flight Number: {selected_flight['flight_number']}\n"
                f"- Departure: {selected_flight['departure_time']} on {ws['departure_date']} from {ws['origin']}\n"
                f"- Arrival: {selected_flight['arrival_time']} on {ws['departure_date']} at {ws['destination']}\n"
                f"- Price: ${selected_flight['price']}\n\n"
                f"Passenger Details:\n"
            )
            for i, passenger in enumerate(ws["passenger_details"], 1):
                summary += (
                    f"Passenger {i}:\n"
                    f"- Name: {passenger['name']}\n"
                    f"- Date of Birth: {passenger['dob']}\n"
                    f"- Passport: {passenger['passport']}\n"
                )
            summary += "\nPlease review and confirm if everything looks correct! 😊✈️"
            state.add_message("assistant", summary)
            return state, summary

    # Handle completion with exact mock data
    if ws.get("current_step") == "complete_booking" and ws.get("booking_reference"):
        selected_flight = get_selected_flight(state)
        if selected_flight and ws.get("passenger_details"):
            first_name = (
                ws["passenger_details"][0]["name"].split()[0]
                if ws["passenger_details"][0]["name"]
                else "traveler"
            )
            response = (
                f"Booking confirmed, {first_name}! Your reference is {ws['booking_reference']}. "
                f"You’re all set for your trip from {ws['origin']} to {ws['destination']} "
                f"on {selected_flight['airline']} flight {selected_flight['flight_number']} "
                f"departing at {selected_flight['departure_time']} on {ws['departure_date']}. "
                f"Safe travels! 😊✈️ Anything else I can help you with?"
            )
            # Reset state for new booking
            state.workflow_state["flight_booking"] = {"current_step": "ask_origin"}
            state.add_message("assistant", response)
            return state, response

    response = await generate_response(state, intent_data, user_input)
    state.add_message("assistant", response)

    return state, response
