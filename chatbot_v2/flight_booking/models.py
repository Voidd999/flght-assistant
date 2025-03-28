from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta


@dataclass
class PassengerInfo:
    name: str = ""
    dob: str = ""
    passport: str = ""
    is_complete: bool = False

@dataclass
class BookingState:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    is_one_way: bool = False
    selected_flight_id: Optional[str] = None
    passenger_count: Optional[int] = None
    passenger_details: List[PassengerInfo] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_step: str = "greeting"
    booking_reference: Optional[str] = None
    is_complete: bool = False

    def add_user_message(self, content: str) -> None:
        self.conversation_history.append({"role": "user", "content": content, "timestamp": datetime.now().isoformat()})

    def add_assistant_message(self, content: str) -> None:
        self.conversation_history.append({"role": "assistant", "content": content, "timestamp": datetime.now().isoformat()})

    def get_selected_flight(self) -> Optional[Dict[str, Any]]:
        from flight_booking.data import FLIGHT_AVAILABILITY
        if not all([self.selected_flight_id, self.origin, self.destination, self.departure_date]):
            return None
        route = f"{self.origin}-{self.destination}"
        if route not in FLIGHT_AVAILABILITY or self.departure_date not in FLIGHT_AVAILABILITY[route]:
            return None
        return next((f for f in FLIGHT_AVAILABILITY[route][self.departure_date] if f["id"] == self.selected_flight_id), None)

    def get_conversation_context(self) -> str:
        from flight_booking.date_utils import format_date_for_system, get_current_date
        context = [f"Current date: {format_date_for_system(get_current_date())}"]
        if self.origin:
            context.append(f"Origin: {self.origin}")
        if self.destination:
            context.append(f"Destination: {self.destination}")
        if self.departure_date:
            context.append(f"Departure date: {self.departure_date}")
            context.append("One-way trip" if self.is_one_way else f"Return date: {self.return_date or 'Not set'}")
        if self.selected_flight_id:
            flight = self.get_selected_flight()
            if flight:
                context.append(f"Selected flight: {flight['airline']} {flight['flight_number']}, "
                              f"Dep: {flight['departure_time']}, Arr: {flight['arrival_time']}, Price: ${flight['price']}")
        if self.passenger_count:
            context.append(f"Passengers: {self.passenger_count}")
            if self.passenger_details:
                context.append("Passenger details:")
                for i, p in enumerate(self.passenger_details, 1):
                    details = []
                    if p.name: details.append(f"Name: {p.name}")
                    if p.dob: details.append(f"DOB: {p.dob}")
                    if p.passport: details.append(f"Passport: {p.passport}")
                    if details: context.append(f"  {i}. {', '.join(details)}")
        if self.booking_reference:
            context.append(f"Booking reference: {self.booking_reference}")
            context.append(f"Status: {'Complete' if self.is_complete else 'In progress'}")
        context.append(f"Current step: {self.current_step}")
        return "\n".join(context)

    def reset_for_new_booking(self):
        self.origin = None
        self.destination = None
        self.departure_date = None
        self.return_date = None
        self.is_one_way = False
        self.selected_flight_id = None
        self.passenger_count = None
        self.passenger_details = []
        self.current_step = "ask_origin"
        self.booking_reference = None
        self.is_complete = False