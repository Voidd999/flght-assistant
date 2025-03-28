# Workflow Documentation

This document provides a comprehensive guide on how to create and implement new workflows in the chatbot system. We'll use the Flight Status workflow as a reference example.

## Table of Contents
1. [Workflow Structure](#workflow-structure)
2. [Creating a New Workflow](#creating-a-new-workflow)
3. [Implementing Tools](#implementing-tools)
4. [Dynamic Tool Registration](#dynamic-tool-registration)
5. [Best Practices](#best-practices)

## Workflow Structure

A workflow consists of three main components:
1. Workflow Definition (`workflow.py`)
2. Tools Implementation (`tools.py`)
3. Data Models (optional, can be in either file)

### Directory Structure
```
app/core/chatbot/tools/
├── your_workflow_name/
│   ├── __init__.py
│   ├── workflow.py
│   └── tools.py
```

## Creating a New Workflow

### 1. Workflow Definition (workflow.py)

Here's an example of a workflow definition using the Flight Status workflow:

```python
from app.core.chatbot.base_workflow import Workflow, WorkflowStep
from pydantic import BaseModel, Field
from typing import ClassVar, Type

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
        
        # Define workflow steps
        self.add_step(WorkflowStep(
            name="search",
            description="Search for flight status using either route or flight number",
            prompt_template="",
            next_steps=[],
            data_schema=None,
            tools=["search_flight_status_by_route", "search_flight_status_by_number", "display_flight_status"],
        ))

# Create workflow instance
workflow = FlightStatusWorkflow()
name = workflow.name 
```

### 2. Tools Implementation (tools.py)

Tools are the actual functions that perform the workflow's operations. Here's an example:

```python
from typing import Dict, Optional, Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from .workflow import name as workflow_name

@tool
async def search_flight_status_by_route(
    origin: str,
    destination: str,
    flight_date: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Search for flight status by specifying the origin airport, destination airport, and date.
    
    Args:
        origin: The departure airport code (e.g., 'RUH' for Riyadh)
        destination: The arrival airport code (e.g., 'JED' for Jeddah)
        flight_date: The date of the flight in YYYY-MM-DD format
    """
    # Implementation...
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "flight_status": flights,
                        "origin": origin,
                        "destination": destination,
                        "flight_date": flight_date
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content="Flight status information...",
                    tool_call_id=tool_call_id,
                    name="search_flight_status_by_route"
                )
            ]
        }
    )

def register_tools() -> Dict[str, callable]:
    """Register all tools for the workflow"""
    return {
        "search_flight_status_by_route": search_flight_status_by_route,
    }
```

## Dynamic Tool Registration

The system now features a dynamic tool registration mechanism that automatically discovers and registers tools from all workflow modules. This eliminates the need to manually update the graph.py file when adding new workflows.

### How It Works

1. **Automatic Discovery**: The `WorkflowManager` automatically scans the `app/core/chatbot/tools/` directory for workflow modules.
2. **Tool Registration**: For each workflow, it calls the `register_tools()` function to get the tools.
3. **Name Scoping**: Tool names are automatically scoped to their respective workflows to prevent name conflicts.
4. **Dynamic Updates**: The tool registry is automatically refreshed when new workflows are registered.

### Tool Name Scoping

To prevent tool name conflicts between different workflows, all tool names are automatically scoped to their workflow. For example, if both the flight_booking and flight_status workflows have a tool called "search", they will be registered as:

- `flight_booking.search`
- `flight_status.search`

This scoping happens automatically, so you don't need to prefix your tool names in the `register_tools()` function.

### Workflow Step Configuration

When defining workflow steps, you can use the unscoped tool names:

```python
self.add_step(WorkflowStep(
    name="search",
    description="Search for flights",
    prompt_template="",
    next_steps=["select"],
    tools=["search_flights"],  # This will be automatically scoped to "flight_booking.search_flights"
))
```

The system will automatically look up the correctly scoped tool name when executing the workflow.

## Best Practices

1. **Workflow Definition**:
   - Give clear, descriptive names to workflows and steps
   - Include comprehensive descriptions
   - Initialize state with all required variables
   - Define clear step transitions

2. **Tool Implementation**:
   - Use type hints for all parameters
   - Include detailed docstrings
   - Handle errors gracefully
   - Return standardized Command objects
   - Register all tools in the `register_tools()` function

3. **State Management**:
   - Keep track of workflow state in the `workflow_data` dictionary
   - Use consistent key names across tools
   - Clear state when workflow completes

4. **Error Handling**:
   - Validate input parameters
   - Provide clear error messages
   - Handle API failures gracefully

5. **Documentation**:
   - Document all parameters and return values
   - Include usage examples
   - Explain any special requirements or dependencies

6. **Tool Naming**:
   - Use descriptive, action-oriented names for tools (e.g., `search_flights`, `select_flight`)
   - Avoid generic names that might conflict with other workflows
   - Remember that tools are automatically scoped to their workflow

## Example Workflow Implementation

Here's a complete example of implementing a simple workflow:

1. Create the directory structure:
```bash
mkdir -p app/core/chatbot/tools/my_workflow
touch app/core/chatbot/tools/my_workflow/{__init__.py,workflow.py,tools.py}
```

2. Define the workflow (workflow.py):
```python
from app.core.chatbot.base_workflow import Workflow, WorkflowStep

class MyWorkflow(Workflow):
    def __init__(self):
        super().__init__(
            name="my_workflow",
            description="Description of what this workflow does",
            prompt_template=""
        )
        
        self.initial_state = {
            "key1": "",
            "key2": None
        }
        
        self.add_step(WorkflowStep(
            name="step1",
            description="First step description",
            prompt_template="",
            next_steps=["step2"],
            tools=["tool1", "tool2"]
        ))

workflow = MyWorkflow()
name = workflow.name
```

3. Implement the tools (tools.py):
```python
from typing import Dict, Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.tools.base import InjectedToolCallId
from .workflow import name as workflow_name

@tool
async def tool1(param1: str, state: Annotated[dict, InjectedState], tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    """
    Tool 1 description
    
    Args:
        param1: Description of param1
        state: Current workflow state
    
    Returns:
        Description of what this tool will return
    """
    return Command(
        update={
            "workflow_data": {
                workflow_name: {
                    "collected_data": {
                        "result": "some_result"
                    }
                }
            },
            "messages": [
                ToolMessage(
                    content="Operation completed",
                    tool_call_id=tool_call_id,
                    name="tool1"
                )
            ]
        }
    )

def register_tools() -> Dict[str, callable]:
    return {
        "tool1": tool1
    }
```

That's it! The system will automatically discover and register your workflow and tools. No need to modify any other files.
