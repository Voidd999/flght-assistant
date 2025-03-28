from typing import Dict, Optional, List, Type, Any, Protocol, ClassVar, Callable, Literal
from pydantic import BaseModel
from app.core.chatbot.state import State
from langgraph.graph import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_core.tools import Tool
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langgraph.graph import END
from app.core.chatbot.llm_manager import LLMManager
from datetime import datetime
from zoneinfo import ZoneInfo

import os
import logging

logger = logging.getLogger(__name__)

class WorkflowStep(BaseModel):
    name: str
    description: str
    prompt_template: str
    next_steps: List[str]
    data_schema: Optional[Type[BaseModel]] = None
    tools: List[str]
    is_terminal: bool = False
    requires_confirmation: bool = False
    confirmation_prompt: str = ""
    value_calculations: Dict[str, str] = {}  # {"total_amount": "flight_price * passengers"}

class WorkflowNodeCallable(Protocol):
    def __call__(self, state: State) -> Dict[str, Any]: ...

class Workflow:
    # Class variable to store all registered workflows
    _workflows: ClassVar[Dict[str, "Workflow"]] = {}
    
    def __init__(self, name: str, description: str, prompt_template: str):
        self.name = name
        self.prompt_template = prompt_template
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.initial_state: Dict[str, Any] = {}
        
       # Register this workflow instance (from each workflow.py file)
        self._workflows[name] = self
        
        # Refresh the tool registry if workflow_manager is available
        try:
            from app.core.chatbot.workflow_manager import workflow_manager
            if hasattr(workflow_manager, 'refresh_tool_registry'):
                workflow_manager.refresh_tool_registry()
        except (ImportError, AttributeError):
            # This happens during initial import, which is fine
            logger.warning("Workflow manager not found")
            pass

    def init_workflow_node(self, state: State) -> Dict[str, Any]:
        """Initialize workflow state"""
        print(f"node: {self.name}")
        
        if not self.steps:
            raise ValueError(f"No steps defined for workflow {self.name}")
        
        return {
            "current_workflow": self.name,
            "workflow_data": {
                self.name: {
                    "current_step": next(iter(self.steps.values())).name,
                    "collected_data": self.initial_state.copy()
                }
            }
        }

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        if step.name in self.steps:
            raise ValueError(f"Step {step.name} already exists in workflow {self.name}")
        self.steps[step.name] = step

    def get_next_step(self, state: State, current_step: str) -> Optional[str]:
        """Get the next step in the workflow based on current state"""
        workflow_state = state.get("workflow_data", {})
        collected_data = workflow_state.get(self.name, {}).get("collected_data", {})
        current_step_config = self.steps.get(current_step)

        if not current_step_config:
            return None

        # Validate using step's data schema if defined
        if current_step_config.data_schema is not None:
            try:
                required_fields = []
                for fld_name, fld in current_step_config.data_schema.model_fields.items():
                    if fld.json_schema_extra.get("required", False):
                        required_fields.append(fld_name)
                # Check if all required fields are present and non-empty
                missing_fields = [
                    field for field in required_fields 
                    if field not in collected_data or collected_data[field] in (None, "", [])
                ]
                if missing_fields:
                    print(f"Missing required fields: {missing_fields}")
                    return None

            except Exception as e:
                print(f"Schema validation error: {e}")
                return None
        
        # Check if step requires confirmation
        # if current_step_config.requires_confirmation:
        #     confirmed = collected_data.get("user_confirmation_received", False)
        #     if not confirmed:
        #         return None
        
        # Handle terminal step
        if current_step_config.is_terminal:
            print(f"Terminal step: {current_step_config.name}")
            return current_step_config.name
        
        # Get next step
        next_step_name = (
            current_step_config.next_steps[0] if current_step_config.next_steps else None
            if isinstance(current_step_config.next_steps, list)
            else current_step_config.next_steps
        )
        print(f"Next step: {next_step_name}")
        return next_step_name if next_step_name else None

    def calculate_values(self, step: WorkflowStep, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived values based on step configuration"""
        calculated_values = {}
        for field, expr in step.value_calculations.items():
            try:
                value = eval(expr, {}, collected_data)
                calculated_values[field] = value
            except Exception as e:
                print(f"Error calculating value for {field}: {e}")
        return calculated_values

    def build_workflow_prompt(self, state: State, step_name: str, workflow_name: str) -> str:
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            print(f"Warning: Workflow {workflow_name} not found")
            return ""
        
        workflow_prompt = workflow.prompt_template
        workflow_description = workflow.description
        workflow_state = state.get("workflow_data", {}).get(workflow_name, {})
        collected_data = workflow_state.get("collected_data", {})
        current_step = workflow.steps[step_name]
        step_prompt = current_step.prompt_template
        
        steps = []
        for _, step in workflow.steps.items():
            confirmation_note = ""
            final_step_note = "This is the final step." if step.is_terminal else ""
            special_instructions = (confirmation_note + final_step_note) or "None"
            tools_list = step.tools if step.tools else []
            # if step.requires_confirmation:
            #     tools_list.append("ask_for_confirmation")
            steps.append(f"- {step.name}: {step.description}. Special instructions: {special_instructions}. Available tools for this step: [{', '.join(tools_list)}]".strip())
            
            
        # Get current time in user's timezone, defaulting to UTC if not available
        current_time = datetime.now(ZoneInfo(state.get("timezone", "UTC")))

        # Handle location data safely - ensure it's always a dict
        location = state.get("location") or {}
        location_details = {
            "city": location.get('city', 'Not provided'),
            "country": location.get('country', 'Not provided'),
            "latitude": location.get('latitude', 'Not provided'),
            "longitude": location.get('longitude', 'Not provided')
        }
        
        timezone = state.get("timezone", "UTC")
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # pending_user_confirmation = collected_data.get("pending_user_confirmation", False)
        # if pending_user_confirmation:
        #     confirmation_note = "You are waiting for user confirmation. You need to call the ask_for_confirmation tool to get the user's confirmation only after you have successfully called any other provided tools."
        # else:
        #     confirmation_note = ""
        
        confirmation_note = ""
        formated_steps = '\n'.join(steps)
        
        
        final_prompt = f"""
        {workflow_description}
        {workflow_prompt}
        
        This workflow consists of the following steps:
        {formated_steps}
        
        The current step is: {current_step.name}, You can only call the tools for this step. {step_prompt}
        You've collected the following data so far for this workflow:
        {collected_data}

        {confirmation_note}
        Below is the general information about the user:
        - Location: 
            - City: {location_details['city']}
            - Country: {location_details['country']}
        Current Time ({timezone}): {current_time_str}
        """
        
        return final_prompt
    
    @classmethod
    def get_workflow(cls, workflow_name: str) -> Optional["Workflow"]:
        """Get a workflow by name"""
        return cls._workflows.get(workflow_name)

    @classmethod
    def get_workflow_names(cls) -> List[str]:
        """Get list of all registered workflow names"""
        return list(cls._workflows.keys())

    @classmethod
    def get_workflow_descriptions(cls) -> str:
        """Get formatted string of all workflow descriptions"""
        return "\n".join([
            f"- {wf.name}: {wf.description}" 
            for wf in cls._workflows.values()
        ])

    @classmethod
    def get_workflow_nodes(cls) -> Dict[str, WorkflowNodeCallable]:
        """Get mapping of workflow names to their initialization nodes"""
        return {
            name: wf.init_workflow_node 
            for name, wf in cls._workflows.items()
        } 