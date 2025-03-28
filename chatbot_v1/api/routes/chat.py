from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.chatbot.service import ChatService

# Create router with prefix and tags
router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

# Models for request/response
class ChatMessageRequest(BaseModel):
    content: str = Field(..., description="The message content to send")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID for context")

chat_service = ChatService()

@router.post("/message")
async def send_message(request: ChatMessageRequest) -> str:
    """
    Send a message to the chat service and get a response.
    The message can be either a regular text message or a form submission in JSON format.
    """
    try:
        conversation = await chat_service.process_message(request.content, request.conversation_id)
        return conversation
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Then later, during application startup:
# await chat_service.initialize_graph() 