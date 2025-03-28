from typing import Tuple
from flight_booking.models import BookingState
from flight_booking.services import parse_user_intent, generate_response, update_booking_state
from flight_booking.date_utils import format_date_for_system, get_current_date

def process_message(state: BookingState, user_input: str) -> Tuple[BookingState, str]:
    state.add_user_message(user_input)
    intent_data = parse_user_intent(state, user_input)
    state = update_booking_state(state, intent_data)
    response = generate_response(state, intent_data, user_input)
    state.add_assistant_message(response)
    return state, response

def main():
    print("Flight Booking Assistant")
    print(f"Today's date: {format_date_for_system(get_current_date())}")
    print("Type 'exit' to end.")
    print()

    state = BookingState()
    greeting = "Hello! I'm your flight booking assistant. How can I assist you today?"
    print(f"Assistant: {greeting}")
    state.add_assistant_message(greeting)

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Assistant: Thank you for using our service. Have a great day!")
            break
        state, response = process_message(state, user_input)
        print(f"Assistant: {response}")

if __name__ == "__main__":
    main()