import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import deque


@dataclass
class FlightDetails:
    date: str = ""
    origin: str = ""
    destination: str = ""
    flight_number: str = ""


@dataclass
class FlightStatus:
    flight_number: str = ""
    origin: str = ""
    destination: str = ""
    date: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    status: str = "Unknown"
    gate: Optional[str] = None
    delay_minutes: Optional[int] = None
    passengers: List[str] = field(default_factory=list)
    confirmed: bool = False


@dataclass
class ChatState:
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history: List[Dict[str, str]] = field(default_factory=list)
    pnr: Optional[str] = None
    flight_details: Optional[FlightDetails] = None
    flight_status: Optional[FlightStatus] = None
    dependency_queue: deque = field(default_factory=deque)
    awaiting_confirmation: bool = False

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def add_dependency(self, dependency: str):
        if dependency not in self.dependency_queue:
            self.dependency_queue.append(dependency)
