# Mock flight status database
FLIGHT_STATUS_DB = {
    "PNR": {
        "EK123456": {
            "flight_number": "EK008",
            "origin": "London",
            "destination": "Dubai",
            "date": "03/15/2025",
            "departure_time": "09:40",
            "arrival_time": "20:30",
            "status": "On Time",
            "gate": "A12",
            "passengers": ["John Smith"],
        },
        "BA789012": {
            "flight_number": "BA107",
            "origin": "London",
            "destination": "Dubai",
            "date": "03/15/2025",
            "departure_time": "13:20",
            "arrival_time": "00:10 +1",
            "status": "Delayed",
            "delay_minutes": 45,
            "gate": "B5",
            "passengers": ["Jane Doe", "Bob Wilson"],
        },
    },
    "FLIGHT": {
        "London-Dubai-03/15/2025": [
            {
                "flight_number": "EK008",
                "departure_time": "09:40",
                "arrival_time": "20:30",
                "status": "On Time",
                "gate": "A12",
            },
            {
                "flight_number": "BA107",
                "departure_time": "13:20",
                "arrival_time": "00:10 +1",
                "status": "Delayed",
                "delay_minutes": 45,
                "gate": "B5",
            },
        ],
        "London-Paris-03/15/2025": [
            {
                "flight_number": "BA332",
                "departure_time": "10:15",
                "arrival_time": "12:30",
                "status": "On Time",
                "gate": "C3",
            }
        ],
    },
}
