import json
from datetime import datetime
from typing import Dict, Any, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.callbacks import get_openai_callback

from chatbot_v2.models import ChatState  
from flight_status.services.dependency_manager import check_dependencies
from flight_status.services.flight_lookup import lookup_flight_status
from flight_status.config.settings import llm
from flight_status.utils.logger import logger
from flight_status.data.mock_data import FLIGHT_STATUS_DB

async def process_message(state: ChatState, user_input: str) -> Tuple[ChatState, str]:
    """Process user input for flight status and update the centralized ChatState."""
    ws = state.workflow_state.get("flight_status", {
        "pnr": None,
        "flight_status": None,
        "flight_details": {},  
        "awaiting_confirmation": False
    })
    state.workflow_state["flight_status"] = ws 
    state.add_message("user", user_input)

    system_prompt = """
    You are a friendly flight status assistant by Flynas. Respond naturally and conversationally to the user's input, leveraging the full context of the conversation.

    Current date: {current_date}
    Conversation history: {history}
    Current flight status: {flight_status}
    Flight database preview: {db_preview}
    Dependency queue: {dependency_queue}
    Awaiting confirmation: {awaiting_confirmation}
    User input: "{user_input}"

    Guidelines:
    1. Identify the intent:
       - "check_status_pnr": User provides a PNR (e.g., "BA789012")
       - "check_status_details": User provides flight details (date, origin, destination)
       - "get_more_info": User asks for additional details about a confirmed flight
       - "ask_delay_reason": User asks why a flight is delayed
       - "confirm_flight": User confirms or rejects a flight (e.g., "yes", "no")
       - "general_query": Anything else or unclear intent
    2. Extract data if present (pnr, date, origin, destination, flight_number)
    3. Respond naturally based on intent, history, and context:
       - Be tolerant of typos (e.g., "staus" means "status", "thinl" means "think").
       - Use the conversation history to stay context-aware and avoid repetition.
       - Keep responses friendly, concise, and emoji-rich.

    Specific cases:
    - For "check_status_pnr":
      - If pnr is missing, ask naturally: "I'd love to check that for you! Could you share your PNR (like BA789012)? 😊✈️"
      - If no flight found, say: "I couldn't find that flight—did you mean a PNR like BA789012 or a flight number like BA107?"
      - If found (and not confirmed), format as: "I found flight {flight_number} with PNR {pnr}\nOrigin: {origin}\nDestination: {destination}\nDate: {date}\nIs this your flight? 😊✈️"
    - For "check_status_details":
      - If details are incomplete, ask for what's missing: "I need a bit more info—could you share the date, origin, or destination? 😊✈️"
      - If no flight found, say: "I couldn't find that flight—can you check the details?"
      - If found (and not confirmed), say: "I found flight {flight_number} from {origin} to {destination} on {date}. Is this your flight? 😊✈️"
    - For "confirm_flight":
      - If input contains "yes" (or similar like "yep", "sure", "correct") and flight_status exists, confirm and show:
        "✈️ Flight {flight_number}\n📅 Date: {date}\n🏃 Origin: {origin}\n🛬 Destination: {destination}\n🕒 Departure: {departure_time}\n🕒 Arrival: {arrival_time}\n📊 Status: {status}{delay_info}\n🚪 Gate: {gate}\nAnything else you'd like to know?"
        (delay_info: " - Delayed by {delay_minutes} min" if applicable)
      - If input contains "no" (or similar), clear flight_status and ask: "No worries! Could you share another PNR or flight details? 😊✈️"
    - For "get_more_info", share details (e.g., passengers, gate) if confirmed, else say: "I need to confirm your flight first—what's your PNR or details? 😊✈️"
    - For "ask_delay_reason", say: "I don't have exact delay reasons—could be weather, technical issues, or ATC. Anything else?"
    - For "general_query":
      - Respond conversationally based on input and history.
      - If user mentions "flight" or "status", nudge gently: "I can help with that! Do you have a PNR or flight details handy?"
      - If user delays (e.g., "wait"), say something like: "Take your time! Let me know when you've got it! 😊✈️"
      - Otherwise, keep it open: "How can I assist you today? 😊✈️"

    Return a JSON object with:
    - intent: string
    - extracted_data: object (pnr, date, origin, destination, flight_number)
    - response: string
    """

    history_str = json.dumps(state.history[-5:])
    flight_status_dict = ws.get("flight_status", {}) 
    flight_status_str = json.dumps(flight_status_dict)
    db_preview = json.dumps({"PNR": list(FLIGHT_STATUS_DB["PNR"].keys()), "FLIGHT": list(FLIGHT_STATUS_DB["FLIGHT"].keys())})
    dependency_queue_str = json.dumps(list(state.dependency_queue))

    flight_number = flight_status_dict.get("flight_number", "")
    date = flight_status_dict.get("date", "")
    origin = flight_status_dict.get("origin", "")
    destination = flight_status_dict.get("destination", "")
    departure_time = flight_status_dict.get("departure_time", "")
    arrival_time = flight_status_dict.get("arrival_time", "")
    status = flight_status_dict.get("status", "Unknown")
    gate = flight_status_dict.get("gate", "N/A")
    delay_minutes = flight_status_dict.get("delay_minutes")
    delay_info = f" - Delayed by {delay_minutes} min" if delay_minutes else ""

    prompt = system_prompt.format(
        current_date=datetime.now().strftime("%m/%d/%Y"),
        history=history_str,
        flight_status=flight_status_str,
        db_preview=db_preview,
        dependency_queue=dependency_queue_str,
        awaiting_confirmation=str(ws.get("awaiting_confirmation", False)),
        user_input=user_input,
        flight_number=flight_number,
        date=date,
        origin=origin,
        destination=destination,
        departure_time=departure_time,
        arrival_time=arrival_time,
        status=status,
        gate=gate,
        delay_info=delay_info,
        delay_minutes=delay_minutes if delay_minutes is not None else "",
        pnr=ws.get("pnr", "") if ws.get("pnr") else ""
    )

    messages = [SystemMessage(content=prompt)]
    with get_openai_callback() as cb:
        response = await llm.ainvoke(messages)

    try:
        result = json.loads(response.content.strip("```json\n```"))
        intent, extracted_data, response_text = result["intent"], result["extracted_data"], result["response"]

        # Check dependencies before proceeding
        missing_deps = check_dependencies(state, intent)
        if missing_deps and intent != "confirm_flight":
            for dep in missing_deps:
                state.add_dependency(dep)
            logger.info(f"Missing dependencies added to queue: {missing_deps}")

        # Handle flight lookup and reconfirmation
        if intent in ["check_status_pnr", "check_status_details"]:
            flight_status = lookup_flight_status(
                pnr=extracted_data.get("pnr"),
                details={
                    "date": extracted_data.get("date"),
                    "origin": extracted_data.get("origin"),
                    "destination": extracted_data.get("destination"),
                    "flight_number": extracted_data.get("flight_number")
                }
            )
            if flight_status:
                # Store flight status
                ws["flight_status"] = {
                    "flight_number": flight_status.flight_number,
                    "date": flight_status.date,
                    "origin": flight_status.origin,
                    "destination": flight_status.destination,
                    "departure_time": flight_status.departure_time,
                    "arrival_time": flight_status.arrival_time,
                    "status": flight_status.status,
                    "gate": flight_status.gate,
                    "delay_minutes": flight_status.delay_minutes,
                    "confirmed": flight_status.confirmed
                }
                ws["pnr"] = extracted_data.get("pnr")
                ws["flight_details"] = {
                    "date": extracted_data.get("date"),
                    "origin": extracted_data.get("origin"),
                    "destination": extracted_data.get("destination"),
                    "flight_number": extracted_data.get("flight_number")
                }
                ws["awaiting_confirmation"] = True
                if intent == "check_status_pnr" and not ws["flight_status"]["confirmed"]:
                    response_text = (
                        f"I found flight {flight_status.flight_number} with PNR {ws['pnr']}\n"
                        f"Origin: {flight_status.origin}\n"
                        f"Destination: {flight_status.destination}\n"
                        f"Date: {flight_status.date}\n"
                        "Is this your flight? 😊✈️"
                    )
            else:
                ws["flight_status"] = None
                ws["awaiting_confirmation"] = False
                logger.warning("Flight status not found for extracted data")
                if intent == "check_status_pnr" and extracted_data.get("pnr"):
                    response_text = f"I couldn't find a flight with PNR {extracted_data['pnr']}—did you mean a PNR like BA789012 or a flight number like BA107? 😊✈️"

        elif intent == "confirm_flight":
            user_input_lower = user_input.lower()
            if any(word in user_input_lower for word in ["yes", "yep", "sure", "correct"]):
                if ws.get("flight_status"):
                    ws["flight_status"]["confirmed"] = True
                    ws["awaiting_confirmation"] = False
                    state.dependency_queue.clear()
                    logger.info("Flight confirmed and queue cleared")
                    response_text = (
                        f"✈️ Flight {ws['flight_status']['flight_number']}\n"
                        f"📅 Date: {ws['flight_status']['date']}\n"
                        f"🏃 Origin: {ws['flight_status']['origin']}\n"
                        f"🛬 Destination: {ws['flight_status']['destination']}\n"
                        f"🕒 Departure: {ws['flight_status']['departure_time']}\n"
                        f"🕒 Arrival: {ws['flight_status']['arrival_time']}\n"
                        f"📊 Status: {ws['flight_status']['status']}{delay_info}\n"
                        f"🚪 Gate: {ws['flight_status']['gate']}\n"
                        "Anything else you'd like to know?"
                    )
            elif any(word in user_input_lower for word in ["no", "nope", "not"]):
                ws["flight_status"] = None
                ws["awaiting_confirmation"] = False
                state.dependency_queue.clear()
                logger.info("Flight status cleared due to non-confirmation")
                response_text = "No worries! Could you share another PNR or flight details? 😊✈️"

        state.add_message("assistant", response_text)
        return state, response_text
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
        response_text = f"Oops, something went wrong: {str(e)}. How can I assist you now?"
        state.add_message("assistant", response_text)
        return state, response_text