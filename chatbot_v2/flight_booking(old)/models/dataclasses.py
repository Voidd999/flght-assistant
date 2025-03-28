from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime


@dataclass
class PassengerInfo:
    """Information about a passenger"""

    name: str = ""
    dob: str = ""  
    passport: str = ""
    is_complete: bool = False


@dataclass
class BookingState:
    """Main state object for the booking conversation"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Core booking data
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None 
    return_date: Optional[str] = None 
    is_one_way: bool = False

    selected_flight_id: Optional[str] = None
    passenger_count: Optional[int] = None
    passenger_details: List[PassengerInfo] = field(default_factory=list)

    # Conversation state
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_step: str = "greeting"
    booking_reference: Optional[str] = None
    is_complete: bool = False

    def add_user_message(self, content: str) -> None:
        """Add a user message to conversation history"""
        self.conversation_history.append(
            {
                "role": "user",
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to conversation history"""
        self.conversation_history.append(
            {
                "role": "assistant",
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert booking state to dictionary"""
        return {
            "id": self.id,
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date,
            "return_date": self.return_date,
            "is_one_way": self.is_one_way,
            "selected_flight_id": self.selected_flight_id,
            "passenger_count": self.passenger_count,
            "passenger_details": [asdict(p) for p in self.passenger_details],
            "current_step": self.current_step,
            "booking_reference": self.booking_reference,
            "is_complete": self.is_complete,
        }

    def get_selected_flight(self) -> Optional[Dict[str, Any]]:
        """Get the selected flight details"""
        from flight_booking.services.flight_lookup import (
            get_selected_flight,
        )  # Moved inside method

        return get_selected_flight(self)

    def get_conversation_context(self) -> str:
        """Get the conversation context for the LLM"""
        from flight_booking.services.date_utils import (
            format_date_for_system,
            get_current_date,
        )

        # Build a summary of the booking state for the LLM
        context = []

        # Add current date context
        current_date = format_date_for_system(get_current_date())
        context.append(f"Current date: {current_date}")

        if self.origin:
            context.append(f"Origin: {self.origin}")

        if self.destination:
            context.append(f"Destination: {self.destination}")

        if self.departure_date:
            context.append(f"Departure date: {self.departure_date}")

            if self.is_one_way:
                context.append("This is a one-way trip")
            elif self.return_date:
                context.append(f"Return date: {self.return_date}")

        if self.selected_flight_id:
            selected_flight = self.get_selected_flight()
            if selected_flight:
                context.append(
                    f"Selected flight: {selected_flight['airline']} {selected_flight['flight_number']}"
                )
                context.append(f"Departure time: {selected_flight['departure_time']}")
                context.append(f"Arrival time: {selected_flight['arrival_time']}")
                context.append(f"Price: ${selected_flight['price']} per passenger")

        if self.passenger_count:
            context.append(f"Number of passengers: {self.passenger_count}")

            if self.passenger_details:
                context.append("Passenger details:")
                for i, passenger in enumerate(self.passenger_details, 1):
                    completed_fields = []
                    if passenger.name:
                        completed_fields.append(f"name: {passenger.name}")
                    if passenger.dob:
                        completed_fields.append(f"DOB: {passenger.dob}")
                    if passenger.passport:
                        completed_fields.append(f"passport: {passenger.passport}")

                    if completed_fields:
                        context.append(
                            f"  Passenger {i}: {', '.join(completed_fields)}"
                        )

        if self.booking_reference:
            context.append(f"Booking reference: {self.booking_reference}")
            context.append(
                f"Booking status: {'Complete' if self.is_complete else 'In progress'}"
            )

        context.append(f"Current step: {self.current_step}")

        return "\n".join(context)
