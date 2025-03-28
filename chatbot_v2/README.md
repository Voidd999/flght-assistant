Flynas Chatbot v2

A centralized AI-powered chatbot for Flynas, built with FastAPI and LangGraph. This application provides flight-related services such as booking flights and checking flight status, leveraging a modular workflow system and LLM-based intent routing.

## Features

- **Flight Booking**: Book flights with a conversational interface, including flight selection and passenger details.
- **Flight Status**: Check the status of flights using PNR or flight details (assumed implemented).
- **Multi-Workflow Support**: Extensible architecture with a central agent routing user inputs to appropriate workflows.
- **FastAPI Endpoints**: RESTful API for initiating and continuing conversations.
- **State Management**: In-memory conversation state (with plans for database/cache in production).

## Project Structure

```
├── chatbot_v2/
│   │   ├── __init__.py
│   │   ├── agent.py                # Central LangGraph agent
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── llm_manager.py          # LLM configuration (assumed)
│   │   ├── state_manager.py        # Optional shared state module
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── logger.py          # Logging utility
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # /chat endpoints
│   │   │   └── new.py             # /new endpoints
│   │   ├── flight_booking/
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # CLI for flight booking (optional)
│   │   │   ├── config/
│   │   │   │   ├── __init__.py
│   │   │   │   └── settings.py    # LLM settings for booking
│   │   │   ├── data/
│   │   │   │   ├── __init__.py
│   │   │   │   └── mock_data.py   # Mock flight data
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── dataclasses.py # ChatState and PassengerInfo
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── flight_lookup.py # Flight data retrieval
│   │   │   │   └── llm_processor.py # Booking logic
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       └── logger.py      # Booking-specific logger
│   │   └── flight_status/         # Similar structure to flight_booking (assumed)
│   └── requirements.txt           # Python dependencies
└── README.md                      # This file
```

## Prerequisites

- Python 3.10+
- Git
- An OpenAI API key (or Azure OpenAI credentials) for LLM integration

## Running the Application

### Option 1: Run as CLI (via `agent.py`)

For testing the chatbot in a console:

1. Navigate to the backend directory:
   ```bash
   cd chatbot_v2
   ```
2. Run the agent:
   ```bash
   python agent.py
   ```
3. Interact with the chatbot:
   - Type "book a flight" to start booking.
   - Type "exit" to quit.

### Option 2: Run as FastAPI Server

To run the full API with endpoints:

1. Start the server:
   ```bash
    python chatbot_v2/main.py
   ```
2. Access the API:
   - **Health Check**: `GET http://localhost:8000/health`
   - **Start Conversation**:

     ```bash
     curl -X POST "http://localhost:8000/new/start" -H "Content-Type: application/json" -d '{"initial_message": "book a flight"}'
     ```

     Response: `{"conversation_id": "<uuid>", "response": "Of course, I’d be happy to help..."}`
   - **Continue Conversation**:

     ```bash
     curl -X POST "http://localhost:8000/new/chat" -H "Content-Type: application/json" -d '{"message": "London", "conversation_id": "<uuid>"}'
     ```
   - **Alternative Chat Endpoint**:

     ```bash
     curl -X POST "http://localhost:8000/chat/message" -H "Content-Type: application/json" -d '{"content": "book a flight"}'
     ```

## API Endpoints

- **`/chat/message` (POST)**: Send a message to the chatbot, optionally with a `conversation_id`. Creates a new conversation if none provided.
- **`/chat/health` (GET)**: Check server health.
- **`/new/start` (POST)**: Start a new conversation with an optional initial message, language, location, and timezone.
- **`/new/chat` (POST)**: Continue an existing conversation by providing a `conversation_id` and message.
