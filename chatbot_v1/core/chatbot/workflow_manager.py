from typing import Dict, Optional, List, Any, Callable
from app.core.chatbot.state import State
from app.core.chatbot.base_workflow import Workflow, WorkflowStep
import importlib
from pathlib import Path
import logging
from langchain_core.tools import BaseTool, Tool

# Set up logging
logger = logging.getLogger(__name__)

# Export WorkflowStep for other modules to use
__all__ = ["workflow_manager", "WorkflowStep"]

class WorkflowManager:
    """Singleton class to manage workflow operations"""
    
    def __init__(self):
        """Initialize the workflow manager and register tools"""
        # Initialize tool registry
        self._tool_registry = {}
        
        # First import all workflow modules to ensure they're registered
        self._import_workflow_modules()
        
        # Then discover and register tools
        self._discover_and_register_tools()
    
    def _import_workflow_modules(self):
        """Import all workflow modules to ensure they're registered"""
        tools_dir = Path(__file__).parent / "tools"
        
        if not tools_dir.exists() or not tools_dir.is_dir():
            logger.warning(f"Tools directory not found at {tools_dir}")
            return
            
        # Iterate through all workflow directories
        for workflow_dir in tools_dir.iterdir():
            if not workflow_dir.is_dir() or workflow_dir.name.startswith('__'):
                continue
                
            # Try to import the workflow module
            try:
                # Construct the module path
                module_path = f"app.core.chatbot.tools.{workflow_dir.name}.workflow"
                
                # Import the module
                importlib.import_module(module_path)
                logger.info(f"Imported workflow module: {module_path}")
            except ImportError as e:
                logger.warning(f"Error importing workflow module {workflow_dir.name}: {e}")
    
    def _discover_and_register_tools(self):
        """Dynamically discover and register tools from all workflow modules"""
        # Get the base tools directory
        tools_dir = Path(__file__).parent / "tools"
        
        if not tools_dir.exists() or not tools_dir.is_dir():
            logger.warning(f"Tools directory not found at {tools_dir}")
            return
            
        # Track potential conflicts for logging
        tool_sources = {}
        registered_count = 0
        
        # Iterate through all workflow directories
        for workflow_dir in tools_dir.iterdir():
            if not workflow_dir.is_dir() or workflow_dir.name.startswith('__'):
                continue
                
            # Try to import the tools module for this workflow
            try:
                # Construct the module path
                module_path = f"app.core.chatbot.tools.{workflow_dir.name}.tools"
                
                # Import the module
                module = importlib.import_module(module_path)
                
                # Check if the module has a register_tools function
                if hasattr(module, 'register_tools'):
                    # Get the workflow name
                    workflow_name = workflow_dir.name
                    
                    # Get raw tools from module
                    tools = module.register_tools()
                    
                    # Convert to proper Tool instances
                    validated_tools = {}
                    for name, tool in tools.items():
                        if isinstance(tool, BaseTool):
                            validated_tools[name] = tool
                        else:
                            # Create Tool instance from raw function
                            validated_tools[name] = Tool(
                                name=name,
                                description=tool.__doc__ or "",
                                func=tool,
                                coroutine=tool if callable(tool) else None
                            )
                    
                    # Check for potential conflicts
                    for tool_name in validated_tools:
                        if tool_name in tool_sources:
                            logger.warning(f"Tool '{tool_name}' is defined in multiple workflows: {tool_sources[tool_name]} and {workflow_name}")
                        tool_sources[tool_name] = workflow_name
                    
                    # Register tools directly (scoping happens in get_scoped_tools)
                    self._tool_registry.update(validated_tools)
                    registered_count += len(validated_tools)
                    
                    logger.info(f"Registered {len(validated_tools)} tools for workflow: {workflow_name}")
                else:
                    logger.warning(f"No register_tools function found in {module_path}")
            except (ImportError, AttributeError) as e:
                logger.error(f"Error registering tools for {workflow_dir.name}: {e}")
                
        logger.info(f"Total tools registered: {registered_count} from {len(tool_sources)} unique tool names")
        
        # Log the registered workflows
        logger.info(f"Registered workflows: {self.workflow_names}")
    
    @property
    def tool_registry(self) -> Dict[str, Callable]:
        """Get the complete tool registry with scoped names"""
        return self._tool_registry
    
    @property
    def workflows(self) -> Dict[str, Workflow]:
        """Get all registered workflows"""
        return Workflow._workflows
    
    @property
    def workflow_names(self) -> List[str]:
        """Get list of available workflow names"""
        return Workflow.get_workflow_names()
    
    @property
    def workflow_descriptions(self) -> str:
        """Get formatted string of workflow descriptions"""
        return Workflow.get_workflow_descriptions()
   

    def get_workflow(self, workflow_name: str) -> Optional[Workflow]:
        """Get workflow by name"""
        return Workflow.get_workflow(workflow_name)
    
    def get_next_step(self, state: State, current_step: str, workflow_name: str) -> Optional[Dict[str, str]]:
        """Determine the next step in a workflow based on current state"""
        workflow = Workflow.get_workflow(workflow_name)
        if not workflow:
            return None
            
        return workflow.get_next_step(state, current_step)
        
    def refresh_tool_registry(self):
        """Refresh the tool registry to include tools from newly registered workflows"""
        self._tool_registry = {}
        self._discover_and_register_tools()
        return self._tool_registry

    def get_scoped_tools(self, workflow_name: str, tool_names: List[str]) -> Dict[str, Callable]:
        """Retrieve scoped tools for a workflow"""
        
        tools = {
            f"{workflow_name}.{base_name}": tool
            for base_name, tool in self._tool_registry.items()
            if base_name in tool_names
        }
        return tools

# Create singleton instance
workflow_manager = WorkflowManager() 