from app.core.chatbot.base_workflow import Workflow, WorkflowStep
from pydantic import BaseModel, Field
from typing import ClassVar, Type
from app.core.chatbot.state import State

class ClaimNumberData(BaseModel):
    claim_number: str = Field(..., required=True)

class BaggageTrackingWorkflow(Workflow):
    def __init__(self):
        super().__init__(
            name="baggage_tracking",
            description="""
            Use this workflow if the user wants to track baggage claim status,
            You need to collect the claim number from the user first, then check the status of the baggage claim.
            """,
            prompt_template="",
        )
        
        # Set initial state
        self.initial_state = {
            "claim_number": "",
            "status": "",
            "compensation_amount": 0.0
        }
        
        # Define workflow steps
        # self.add_step(WorkflowStep(
        #     name="collect_claim",
        #     description="Collect the baggage claim number from the user",
        #     prompt_template="",
        #     next_steps=["check_status"],
        #     data_schema=ClaimNumberData,
        #     tools=["collect_claim_number"],
        # ))
        
        # self.add_step(WorkflowStep(
        #     name="check_status",
        #     description="Check baggage claim status using provided claim number",
        #     prompt_template="",
        #     next_steps=[],
        #     data_schema=None,
        #     tools=["check_baggage_status"],
        #     value_calculations={
        #         "status": "baggage_system_response.get('status', 'pending')",
        #         "compensation_amount": "baggage_system_response.get('compensation', 0.0)"
        #     },
        #     is_terminal=True
        # ))
        
        self.add_step(WorkflowStep(
            name="check_status",
            description="Check baggage claim status using provided claim number",
            prompt_template="",
            next_steps=[],
            data_schema=None,
            tools=["collect_claim_number", "check_baggage_status"],
            value_calculations={
                "status": "baggage_system_response.get('status', 'pending')",
                "compensation_amount": "baggage_system_response.get('compensation', 0.0)"
            },
            is_terminal=True
        ))

# Create workflow instance
workflow = BaggageTrackingWorkflow() 
name = workflow.name