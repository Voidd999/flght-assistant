from app.core.chatbot.base_workflow import Workflow, WorkflowStep
from pydantic import BaseModel, Field
from typing import ClassVar, Type, List
from app.core.chatbot.state import State

# Data models for each step
class SearchStepData(BaseModel):
    origin: str = Field(..., required=True)
    destination: str = Field(..., required=True)
    departure_date: str = Field(..., required=True)
    return_date: str = Field(..., required=False)
    passengers_count: int = Field(..., required=True)

class SelectFlightData(BaseModel):
    selected_flight: str = Field(..., required=True)
    
class Passenger(BaseModel):
    first_name: str = Field(..., required=True)
    last_name: str = Field(..., required=True)
    passport_number: str = Field(..., required=True)
    dob: str = Field(..., required=True)

class PassengerInfoData(BaseModel):
    passengers: List[Passenger] = Field(..., required=True)

class ContactInfo(BaseModel):
    email: str = Field(..., required=True)
    phone: str = Field(..., required=True)

class ContactInfoData(BaseModel):
    contact_info: ContactInfo = Field(..., required=True)

class PaymentInfo(BaseModel):
    card_number: str = Field(..., required=True)
    expiration: str = Field(..., required=True)
    cvv: str = Field(..., required=True)
    amount: float = Field(..., required=True)

class PaymentData(BaseModel):
    payment: PaymentInfo = Field(..., required=True)

class CompleteBookingData(BaseModel):
    confirmation: bool = Field(..., description="User confirmation", required=True)

class FlightBookingWorkflow(Workflow):
    def __init__(self):
        super().__init__(
            name="flight_booking",
            description="Use this workflow if the user wants to book a flight",
            prompt_template=""""""
        )
        
        # Set initial state
        self.initial_state = {
            "origin": "",
            "destination": "",
            "departure_date": "",
            "return_date": "",
            "passengers_count": 0,
            "passengers": []
        }
        
        # Define workflow steps
        self.add_step(WorkflowStep(
            name="search",
            description="Search for flights based on the user's input",
            prompt_template="Try to extract the required information for the tool call from the user's prompt",
            next_steps=["select"],
            data_schema=SearchStepData,
            tools=["search_flights"],
        ))
        
        self.add_step(WorkflowStep(
            name="select",
            description="Select a flight from the available options based on the user's input",
            prompt_template="",
            next_steps=["passenger_info"],
            data_schema=SelectFlightData,
            tools=["select_flight"],
            value_calculations={
                "flight_number": "next(opt for opt in available_options if opt['flight_number'] == flight_number)"
            }
        ))
        
        self.add_step(WorkflowStep(
            name="passenger_info",
            description="Collect the passenger information from the user",
            prompt_template="",
            next_steps=["contact_info"],
            data_schema=PassengerInfoData,
            tools=["collect_passenger_info"],
            value_calculations={
                "total_amount": "flight_number['price'] * len(passengers)"
            }
        ))
        
        self.add_step(WorkflowStep(
            name="contact_info",
            description="Collect the contact information from the user",
            prompt_template="",
            next_steps=["payment"],
            data_schema=ContactInfoData,
            tools=["collect_contact_info"],
        ))
        
        self.add_step(WorkflowStep(
            name="payment",
            description="Collect the payment information from the user and prepare the booking summary",
            prompt_template="",
            next_steps=["book_flight"],
            data_schema=PaymentData,
            tools=["collect_payment_info", "booking_summary"],
            requires_confirmation=True,
        ))
        
        self.add_step(WorkflowStep(
            name="book_flight",
            description="Book the flight and show the final booking details to the user",
            prompt_template="",
            next_steps=[],
            data_schema=None,
            tools=["book_flight"],
            is_terminal=True
        ))

# Create workflow instance
workflow = FlightBookingWorkflow()
name = workflow.name