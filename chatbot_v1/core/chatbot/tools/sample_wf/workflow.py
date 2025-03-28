from app.core.chatbot.base_workflow import Workflow, WorkflowStep
from pydantic import BaseModel, Field
from typing import ClassVar, Type
from app.core.chatbot.state import State

class MealOrderData(BaseModel):
    meal_type: str = Field(..., required=True)
    quantity: int = Field(..., required=True)

class OrderMealsWorkflow(Workflow):
    def __init__(self):
        super().__init__(
            name="order_meals",
            description="Use this workflow if the user wants to order meals",
            prompt_template=""
        )
        
        # Set initial state
        self.initial_state = {
            "meal_type": "",
            "quantity": 0,
            "total_amount": 0
        }
        
        # Define workflow steps
        self.add_step(WorkflowStep(
            name="collect_meal_order",
            description="Collect the meal type and quantity from the user",
            prompt_template="",
            next_steps=["order_summary"],
            data_schema=MealOrderData,
            tools=["collect_meal_order"],
        ))
        
        self.add_step(WorkflowStep(
            name="order_summary",
            description="Show the order summary to the user",
            prompt_template="",
            next_steps=["do_order"],
            data_schema=None,
            tools=["order_summary"],
            value_calculations={
                "total_amount": "meal_type.get('price', 0.0) * quantity"
            },
        ))
        
        self.add_step(WorkflowStep(
            name="do_order",
            description="Confirm the order with the user and show the final order details",
            prompt_template="",
            tools=[],
            next_steps=[],
            data_schema=None,
            requires_confirmation=True,
            is_terminal=True
        ))

# Create workflow instance
workflow = OrderMealsWorkflow() 
name = workflow.name