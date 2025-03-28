from app.core.chatbot.base_workflow import Workflow, WorkflowStep
from pydantic import BaseModel, Field
from typing import ClassVar, Type
from app.core.chatbot.state import State

class FlightStatusWorkflow(Workflow):
    def __init__(self):
        super().__init__(
            name="flight_status",
            description="""
            Use this workflow if the user wants to check flight status, 
            user can check the status of a flight by providing the origin, destination and flight date,
            or by providing the flight number and flight date.
            """,
            prompt_template=""""""
        )
        
        # Set initial state
        self.initial_state = {
            "origin": "",
            "destination": "",
            "flight_date": "",
            "flight_number": "",
            "flight_status": None
        }
        
        self.add_step(WorkflowStep(
            name="search",
            description="Search for flight status using either route or flight number",
            prompt_template="",
            # next_steps=["show_status"],
            next_steps=[],
            data_schema=None,
            tools=["search_flight_status_by_route", "search_flight_status_by_number", "display_flight_status"],
        ))

# Create workflow instance
workflow = FlightStatusWorkflow()
name = workflow.name 