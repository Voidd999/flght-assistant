from typing import Dict, Optional
from flight_status.models.dataclasses import FlightStatus
from flight_status.data.mock_data import FLIGHT_STATUS_DB
from flight_status.utils.logger import logger

def lookup_flight_status(pnr: Optional[str] = None, details: Optional[Dict[str, str]] = None) -> Optional[FlightStatus]:
    if pnr:
        pnr = pnr.upper()
        if pnr and pnr in FLIGHT_STATUS_DB["PNR"]:
            flight_data = FLIGHT_STATUS_DB["PNR"][pnr]
            logger.info(f"PNR lookup successful: {pnr} -> {flight_data}")
            return FlightStatus(
                flight_number=flight_data["flight_number"],
                origin=flight_data["origin"],
                destination=flight_data["destination"],
                date=flight_data["date"],
                departure_time=flight_data["departure_time"],
                arrival_time=flight_data["arrival_time"],
                status=flight_data["status"],
                gate=flight_data.get("gate"),
                delay_minutes=flight_data.get("delay_minutes"),
                passengers=flight_data.get("passengers", [])
            )
        return None

    if details and details.get("date") and details.get("origin") and details.get("destination"):
        date = details["date"]
        origin = details["origin"]
        destination = details["destination"]
        flight_number = details.get("flight_number")
        route_key = f"{origin.title()}-{destination.title()}-{date}"
        if route_key in FLIGHT_STATUS_DB["FLIGHT"]:
            flights = FLIGHT_STATUS_DB["FLIGHT"][route_key]
            selected_flight = flights[0]
            if flight_number:
                for flight in flights:
                    if flight["flight_number"].lower() == flight_number.lower():
                        selected_flight = flight
                        break
            return FlightStatus(
                flight_number=selected_flight["flight_number"],
                origin=origin.title(),
                destination=destination.title(),
                date=date,
                departure_time=selected_flight["departure_time"],
                arrival_time=selected_flight["arrival_time"],
                status=selected_flight["status"],
                gate=selected_flight.get("gate"),
                delay_minutes=selected_flight.get("delay_minutes")
            )
    return None