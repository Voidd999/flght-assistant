# chatbot_v2/routes/new.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from chatbot_v2.models import ChatState 
from chatbot_v2.agent import process_user_input  
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/new", tags=["new"])


class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    country: Optional[str] = "Unknown"
    city: Optional[str] = "Unknown"


class StartRequest(BaseModel):
    initial_message: Optional[str] = Field(
        None, description="Optional initial message to start the conversation"
    )
    language: Optional[str] = Field(
        "en-US", description="Language preference for the conversation"
    )
    location: Optional[LocationRequest] = Field(
        None, description="User's location information"
    )
    timezone: Optional[str] = Field(None, description="User's timezone")


class StartResponse(BaseModel):
    conversation_id: str
    response: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


# Global state storage (for simplicity; in production, use a database or cache)
chat_states: dict[str, ChatState] = {}


@router.post("/start", response_model=StartResponse)
async def start_conversation(request: StartRequest):
    """
    Initiates a new conversation.
    - Generates a unique conversation_id
    - Optionally processes an initial message
    """
    try:
        conversation_id = str(uuid.uuid4())
        state = ChatState(conversation_id=conversation_id)
        chat_states[conversation_id] = state
        logger.info(f"New conversation started with ID: {conversation_id}")

        response = None
        if request.initial_message and request.initial_message != "--":
            response = await process_user_input(state, request.initial_message)
            logger.info(f"Initial message processed for {conversation_id}: {response}")
        else:
            initial_response = "Hey there! How can I assist you today? 😊✈️"
            state.add_message("assistant", initial_response)
            response = initial_response
            logger.info(f"Default greeting sent for {conversation_id}")

        # Store metadata
        state.workflow_state["language"] = request.language
        state.workflow_state["location"] = (
            request.location.dict() if request.location else None
        )
        state.workflow_state["timezone"] = request.timezone
        logger.debug(
            f"Metadata stored for {conversation_id}: language={request.language}, location={request.location}, timezone={request.timezone}"
        )

        return StartResponse(conversation_id=conversation_id, response=response)
    except Exception as e:
        logger.error(f"Error in start_conversation: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start conversation")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a message in an existing conversation"""
    try:
        if request.conversation_id not in chat_states:
            logger.warning(f"Conversation not found: {request.conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")

        state = chat_states[request.conversation_id]
        logger.info(f"Processing message for conversation {request.conversation_id}")
        response = await process_user_input(state, request.message)
        logger.info(f"Response generated for {request.conversation_id}: {response}")

        return ChatResponse(response=response, conversation_id=request.conversation_id)
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message")
