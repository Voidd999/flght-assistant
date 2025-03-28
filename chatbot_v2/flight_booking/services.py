import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from flight_booking.models import BookingState, PassengerInfo
from flight_booking.data import FLIGHT_AVAILABILITY
from flight_booking.settings import llm, intent_llm
from flight_booking.date_utils import format_date_for_system, get_current_date, is_valid_booking_date


def parse_user_intent(state: BookingState, user_input: str) -> Dict[str, Any]:
    context = state.get_conversation_context()
    today_date = format_date_for_system(get_current_date())
    
    available_routes_info = ""
    for route, dates in FLIGHT_AVAILABILITY.items():
        origin, destination = route.split('-')
        available_routes_info += f"- {route}: {', '.join(dates.keys())}\n"
        for date, flights in dates.items():
            for f in flights:
                available_routes_info += f"  {date}: {f['id']}, {f['airline']} {f['flight_number']}, "
                available_routes_info += f"{f['departure_time']}-{f['arrival_time']}, ${f['price']}\n"

    system_prompt = f"""You are a flight booking assistant.

CURRENT STATE:
{context}

TODAY: {today_date}

AVAILABLE FLIGHTS:
{available_routes_info}

INSTRUCTIONS:
1. Extract info only from user input, not past state unless updating.
2. Match flight IDs exactly from database.
3. If flight mentioned without ID, set next_step to "show_flights".
4. Convert relative dates (e.g., "tomorrow") to MM/DD/YYYY based on {today_date}.
5. Reject past dates.
6. If user says "book another flight" or similar, intent is "start_over".

Return JSON:
- "extracted_info": {{origin, destination, departure_date, return_date, is_one_way, passenger_count, selected_flight_id, passenger_N_name, passenger_N_dob, passenger_N_passport}}
- "intent": "provide_info", "change_info", "ask_question", "confirm", "start_over", "complete_booking"
- "next_step": "ask_origin", "ask_destination", "ask_dates", "show_flights", "ask_flight_selection", "ask_passenger_count", "ask_passenger_details", "confirm_booking", "complete_booking", "answer_question"
- "missing_info": List of missing fields
- "needs_clarification": Boolean
- "clarification_message": String if needed
- "date_validation": {{"valid_departure_date": boolean, "valid_return_date": boolean, "date_error_message": string}}
"""

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_input)]
    try:
        response = intent_llm.invoke(messages).content
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        return json.loads(response)
    except Exception as e:
        print(f"Error parsing intent: {e}")
        return {
            "extracted_info": {},
            "intent": "provide_info",
            "next_step": "ask_origin" if not state.origin else "ask_destination",
            "missing_info": ["origin", "destination", "departure_date"],
            "needs_clarification": True,
            "clarification_message": "Could you please clarify?",
            "date_validation": {"valid_departure_date": True, "valid_return_date": True, "date_error_message": None}
        }

def generate_response(state: BookingState, intent_data: Dict[str, Any], user_input: str) -> str:
    context = state.get_conversation_context()
    today_date = format_date_for_system(get_current_date())
    messages_context = [f"{m['role'].capitalize()}: {m['content']}" for m in state.conversation_history[-10:]]

    available_routes_info = ""
    for route, dates in FLIGHT_AVAILABILITY.items():
        available_routes_info += f"\nRoute: {route}\n"
        for date, flights in dates.items():
            for f in flights:
                available_routes_info += f"  {date}: {f['id']}, {f['airline']} {f['flight_number']}, "
                available_routes_info += f"{f['departure_time']}-{f['arrival_time']}, ${f['price']}\n"

    flights_to_show = ""
    if state.origin and state.destination and state.departure_date:
        route = f"{state.origin}-{state.destination}"
        if route in FLIGHT_AVAILABILITY and state.departure_date in FLIGHT_AVAILABILITY[route]:
            flights = FLIGHT_AVAILABILITY[route][state.departure_date]
            flights_to_show = f"Flights from {state.origin} to {state.destination} on {state.departure_date}:\n"
            for i, f in enumerate(flights, 1):
                flights_to_show += f"{i}. {f['id']}: {f['airline']} {f['flight_number']}, "
                flights_to_show += f"{f['departure_time']}-{f['arrival_time']}, ${f['price']}\n"
        else:
            flights_to_show = f"No flights from {state.origin} to {state.destination} on {state.departure_date}.\n"
            if route in FLIGHT_AVAILABILITY:
                flights_to_show += f"Available dates: {', '.join(FLIGHT_AVAILABILITY[route].keys())}"

    date_error = ""
    dv = intent_data.get("date_validation", {})
    if not dv.get("valid_departure_date", True):
        date_error = "Departure date is invalid or in the past. Please provide a date from today onwards."
    elif not dv.get("valid_return_date", True) and state.return_date:
        date_error = "Return date must be after departure date and not in the past."

    missing_passenger_info = ""
    if state.passenger_count and state.current_step in ["ask_passenger_details", "confirm_booking"]:
        incomplete = [i for i, p in enumerate(state.passenger_details) if not (p.name and p.dob and p.passport)]
        if incomplete:
            missing_passenger_info = "We need full details (name, DOB as MM/DD/YYYY, passport) for passengers: " + ", ".join([str(i+1) for i in incomplete])

    system_prompt = f"""You are a friendly flight booking assistant.

STATE:
{context}

TODAY: {today_date}

INTENT:
{json.dumps(intent_data, indent=2)}

HISTORY:
{chr(10).join(messages_context)}

INPUT: "{user_input}"

FLIGHTS:
{available_routes_info}

TO SHOW:
{flights_to_show}

DATE ERROR:
{date_error}

MISSING PASSENGER INFO:
{missing_passenger_info}

INSTRUCTIONS:
1. NEVER invent flights or dates. Use only FLIGHTS data.
2. If showing flights, use TO SHOW exactly and ask for flight ID.
3. Follow steps: origin → destination → date → flights → passenger count → details → confirm → complete.
4. If passenger details incomplete, ask for them before confirming.
5. Reset for new booking on "start_over" intent.
6. Be warm, concise, and professional.

TASK:
Respond naturally, advancing the booking process deterministically.
"""

    messages = [SystemMessage(content=system_prompt)]
    try:
        return llm.invoke(messages).content
    except Exception as e:
        print(f"Error generating response: {e}")
        return "Sorry, I’m having trouble. Please try again!"

def update_booking_state(state: BookingState, intent_data: Dict[str, Any]) -> BookingState:
    extracted = intent_data.get("extracted_info", {})
    dv = intent_data.get("date_validation", {})

    if intent_data["intent"] == "start_over":
        state.reset_for_new_booking()

    if "origin" in extracted and extracted["origin"]:
        state.origin = extracted["origin"].strip().title()
    if "destination" in extracted and extracted["destination"]:
        state.destination = extracted["destination"].strip().title()
    if "departure_date" in extracted and extracted["departure_date"] is not None and dv.get("valid_departure_date", True):
        is_valid, date = is_valid_booking_date(extracted["departure_date"])
        if is_valid:
            state.departure_date = date
    if "return_date" in extracted and extracted["return_date"] is not None and dv.get("valid_return_date", True):
        is_valid, date = is_valid_booking_date(extracted["return_date"])
        if is_valid:
            state.return_date = date
            state.is_one_way = False
    if "is_one_way" in extracted:
        state.is_one_way = extracted["is_one_way"]
        if state.is_one_way:
            state.return_date = None
    if "selected_flight_id" in extracted and extracted["selected_flight_id"]:
        state.selected_flight_id = extracted["selected_flight_id"]
    if "passenger_count" in extracted and extracted["passenger_count"] is not None:
        try:
            count = int(extracted["passenger_count"])
            if 1 <= count <= 9:
                state.passenger_count = count
                while len(state.passenger_details) < count:
                    state.passenger_details.append(PassengerInfo())
                state.passenger_details = state.passenger_details[:count]
        except (ValueError, TypeError):
            pass

    passenger_updates = {}
    for key, value in extracted.items():
        if key.startswith("passenger_"):
            try:
                parts = key.split("_")
                idx = int(parts[1]) - 1
                field = parts[2]
                if idx not in passenger_updates:
                    passenger_updates[idx] = {}
                passenger_updates[idx][field] = value
            except (ValueError, IndexError):
                pass

    for idx, updates in passenger_updates.items():
        while len(state.passenger_details) <= idx:
            state.passenger_details.append(PassengerInfo())
        p = state.passenger_details[idx]
        if "name" in updates:
            p.name = updates["name"]
        if "dob" in updates:
            p.dob = updates["dob"]
        if "passport" in updates:
            p.passport = updates["passport"]
        if "email" in updates:
            p.email = updates["email"]
        p.is_complete = bool(p.name and p.dob and p.passport)

    if intent_data.get("next_step"):
        state.current_step = intent_data["next_step"]

    if state.current_step == "complete_booking" and not state.booking_reference:
        flight = state.get_selected_flight()
        if flight and all(p.is_complete for p in state.passenger_details):
            airline_code = flight["flight_number"][:2]
            import random
            import string
            state.booking_reference = f"{airline_code}{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            state.is_complete = True

    return state