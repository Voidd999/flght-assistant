# chatbot_v2/routes/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from chatbot_v2.models import ChatState  
from chatbot_v2.agent import process_user_input 
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessageRequest(BaseModel):
    content: str = Field(..., description="The message content to send")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for context"
    )


class ChatMessageResponse(BaseModel):
    conversation_id: str
    response: str

chat_states: dict[str, ChatState] = {}


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(request: ChatMessageRequest) -> ChatMessageResponse:
    """Send a message to the chat service and get a response."""
    try:
        # Use a unique ID if none provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        if conversation_id not in chat_states:
            chat_states[conversation_id] = ChatState(conversation_id=conversation_id)
            logger.info(f"New conversation started with ID: {conversation_id}")
        else:
            logger.info(f"Continuing conversation with ID: {conversation_id}")

        state = chat_states[conversation_id]

        # Process message using agent logic
        response = await process_user_input(state, request.content)
        logger.info(f"Response generated for {conversation_id}: {response}")

        return ChatMessageResponse(conversation_id=conversation_id, response=response)
    except Exception as e:
        logger.error(f"Error in send_message: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Something went wrong. Please try again."
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
