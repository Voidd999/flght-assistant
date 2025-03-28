import json
from typing import Dict, List, Optional, Type, Literal, Annotated
from pydantic import BaseModel
from langchain_core.tools import BaseTool, tool
from typing import Any
from langgraph.types import Command
from langgraph.prebuilt import InjectedState
from langchain_core.messages import ToolMessage
import aiohttp
from datetime import datetime, date
from langchain_core.tools.base import InjectedToolCallId
import logging

logger = logging.getLogger(__name__)

class FlightStatusByRouteRequest(BaseModel):
    origin: str
    destination: str
    flightDate: str
    flightNumber: str = ""
    statusBy: str = "route"
    cultureCode: str = "en-US"

class FlightStatusByNumberRequest(BaseModel):
    flightNumber: str
    flightDate: str
    statusBy: str = "flightNumber"
    cultureCode: str = "en-US"

class FlightSearchInfo(BaseModel):
    search_type: str  # 'route' or 'flight_number'
    origin: Optional[str] = None
    destination: Optional[str] = None
    flight_number: Optional[str] = None
    flight_date: str

def format_flight_info(flight_data: dict) -> str:
    """Format flight information into a readable string"""
    segments = flight_data.get("Segments", [])
    if not segments:
        return "No flight information available"

    flight_info = []
    flight_info.append(f"Flight: {flight_data['FlightNumbers']}")
    flight_info.append(f"From: {flight_data['OriginName']} ({flight_data['OriginCode']})")
    flight_info.append(f"To: {flight_data['DestinationName']} ({flight_data['DestinationCode']})")
    flight_info.append(f"Departure: {flight_data['DepartureTime']}")
    flight_info.append(f"Arrival: {flight_data['ArrivalTime']}")

    if len(segments) > 1:
        flight_info.append("\nConnection Details:")
        for i, segment in enumerate(segments, 1):
            flight_info.append(f"\nSegment {i}:")
            flight_info.append(f"Aircraft: {segment['AirCraftType']}")
            flight_info.append(f"From: {segment['DepartureStationName']} ({segment['DepartureStation']})")
            flight_info.append(f"To: {segment['ArrivalStationName']} ({segment['ArrivalStation']})")
            flight_info.append(f"Departure: {segment['STD'].split('T')[1][:5]}")
            flight_info.append(f"Arrival: {segment['STA'].split('T')[1][:5]}")
    else:
        segment = segments[0]
        flight_info.append(f"Aircraft: {segment['AirCraftType']}")

    return "\n".join(flight_info)

def validate_date(date_str: str) -> bool:
    """Validate if the date string is in YYYY-MM-DD format and not in the past"""
    try:
        flight_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        return flight_date >= today
    except ValueError:
        return False

@tool
async def collect_info(
  state: Annotated[dict, InjectedState],
  tool_call_id: Annotated[str, InjectedToolCallId],  
  flight_date: Optional[str] = None,
  origin: Optional[str] = None,
  destination: Optional[str] = None,
  flight_number: Optional[str] = None,
  ) -> Command:
    """
    Collect the required information from the user, Try to determine if the user wants to search by route (origin/destination) or by flight number
    
    Args:
        flight_date: The date of the flight in YYYY-MM-DD format
        origin: The departure airport code (e.g., 'RUH' for Riyadh)
        destination: The arrival airport code (e.g., 'JED' for Jeddah)
        flight_number: The flight number (e.g., '61' or 'XY61')
        
    Returns:
        Collected information and prompts for any missing required data.
    """
    logger.info(f"TOOL: collect_info")
    
    workflow_name = state.get("current_workflow")
    
    return Command(
            name="collect_info",
            update={
                "workflow_data": {
                    workflow_name: {
                        "collected_data": {
                            "flight_date": flight_date,
                            "origin": origin,
                            "destination": destination,
                            "flight_number": flight_number
                        }
                    }
                },
                "messages": [
                    ToolMessage(
                        content="I have collected all required information for your flight status search.",
                        tool_call_id=tool_call_id,
                        name="collect_info"
                    )
                ]
            }
        )

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
    Use this when the user provides origin and destination cities/airports.
    
    Args:
        origin: The departure airport code (e.g., 'RUH' for Riyadh)
        destination: The arrival airport code (e.g., 'JED' for Jeddah)
        flight_date: The date of the flight in YYYY-MM-DD format
    
    Returns:
        Flight status information including flight numbers, departure/arrival times, and connection details if any.
    """
    
    logger.info(f"TOOL: search_flight_status_by_route")
    
    workflow_name = state.get("current_workflow")
    
    # Prepare request data
    request_data = FlightStatusByRouteRequest(
        origin=origin.upper(),
        destination=destination.upper(),
        flightDate=flight_date
    )
    
    try:
        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.flynas.com/Umbraco/api/FlightStatusApi/GetFlightStatusByRoute",
                json=request_data.model_dump()
            ) as response:
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status
                    )
                flights = await response.json()
        
        if not flights:
            return Command(
                name="search_flight_status_by_route",
                update={
                    "messages": [
                        ToolMessage(
                            content=f"No flights found for the route {origin} to {destination} on {flight_date}",
                            tool_call_id=tool_call_id,
                            name="search_flight_status_by_route"
                        )
                    ]
                }
            )
        
        # Format flight information
        flight_info = []
        for flight in flights[:5]:  # Limit to first 5 flights
            flight_info.append(format_flight_info(flight))
        
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
                        content="Found the following flights status:\n\n".join(flight_info),
                        tool_call_id=tool_call_id,
                        name="search_flight_status_by_route"
                    )
                ]
            }
        )
    except Exception as e:
        return Command(
            name="search_flight_status_by_route",
            update={
                "messages": [
                    ToolMessage(
                        content=f"Error searching for flights: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="search_flight_status_by_route"
                    )
                ]
            }
        )

@tool
async def search_flight_status_by_number(
    flight_number: str,
    flight_date: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Search for flight status using a specific flight number and date.
    Use this when the user provides a flight number (with or without the 'XY' prefix).
    
    Args:
        flight_number: The flight number (e.g., '61' or 'XY61')
        flight_date: The date of the flight in YYYY-MM-DD format
    
    Returns:
        Detailed flight status information including departure/arrival times and connection details if any.
    """
    
    logger.info(f"TOOL: search_flight_status_by_number")
    
    workflow_name = state.get("current_workflow")
    
    # Clean flight number (remove "XY" if present)
    flight_number = flight_number.upper().replace("XY", "").strip()
    
    # Prepare request data
    request_data = FlightStatusByNumberRequest(
        flightNumber=flight_number,
        flightDate=flight_date,
    )
    
    try:
        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://www.flynas.com/Umbraco/api/FlightStatusApi/GetFlightStatusByFlightNo",
                json=request_data.model_dump()
            ) as response:
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=response.status
                    )
                flights = await response.json()
        
        if not flights:
            return Command(
                name="search_flight_status_by_number",
                update={
                    "messages": [
                        ToolMessage(
                            content=f"No flights found for flight number XY {flight_number} on {flight_date}",
                            tool_call_id=tool_call_id,
                            name="search_flight_status_by_number"
                        )
                    ]
                }
            )
        
        # Format flight information
        flight_info = []
        for flight in flights:
            flight_info.append(format_flight_info(flight))
        
        return Command(
            update={
                "workflow_data": {
                    workflow_name: {
                        "collected_data": {
                            "flight_status": flights,
                            "flight_number": flight_number,
                            "flight_date": flight_date
                        }
                    }
                },
                "messages": [
                    ToolMessage(
                        content="Found the following flights:\n\n".join(flight_info),
                        tool_call_id=tool_call_id,
                        name="search_flight_status_by_number"
                    )
                ]
            }
        )
    except Exception as e:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Error searching for flight: {str(e)}",
                        tool_call_id=tool_call_id,
                        name="search_flight_status_by_number"
                    )
                ]
            }
        )

@tool
async def display_flight_status(
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Display the flight status information to the user in a formatted way.
    Shows flight details including flight numbers, times, aircraft type, and connection details if any.
    Automatically called after a successful flight status search.
    """
    
    logger.info(f"TOOL: display_flight_status")
    
    workflow_name = state.get("current_workflow")
    workflow_data = state.get("workflow_data", {}).get(workflow_name, {})
    collected_data = workflow_data.get("collected_data", {})
    flight_status = collected_data.get("flight_status", [])
    
    if not flight_status:
        return Command(
            name="display_flight_status",
            update={
                "messages": [
                    ToolMessage(
                        content="No flight status information available.",
                        tool_call_id=tool_call_id,
                        name="display_flight_status"
                    )
                ]
            }
        )
    
    # Format flight information
    flight_info = []
    for flight in flight_status[:5]:  # Limit to first 5 flights
        flight_info.append(format_flight_info(flight))
    
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content="The flight status is as follows:\n\n".join(flight_info),
                    tool_call_id=tool_call_id,
                    name="display_flight_status"
                )
            ]
        }
    )

def register_tools() -> Dict[str, BaseTool]:
    """Register all tools for the flight status workflow"""
    return {
        "search_flight_status_by_route": search_flight_status_by_route,
        "search_flight_status_by_number": search_flight_status_by_number,
        "display_flight_status": display_flight_status,
        "collect_info": collect_info,
    } 