from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4
from app.core.chatbot.service import ChatService, LocationRequest

# Initialize router
router = APIRouter(
    prefix="/new",
    tags=["new"]
)

class StartRequest(BaseModel):
    initial_message: Optional[str] = Field(None, description="Optional initial message to start the conversation")
    language: Optional[str] = Field("en-US", description="Language preference for the conversation")
    location: Optional[LocationRequest] = Field(None, description="User's location information")
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

chat_service = ChatService()

@router.post("/start", response_model=StartResponse)
async def start_conversation(request: StartRequest):
    """
    Initiates a new conversation.
    - Generates a unique conversation_id
    - Optionally processes an initial message
    """
    try:
        
        response = None
        # Process the initial message using the chat service
        (chat_response, conversation_id) = await chat_service.process_message(
            message=request.initial_message,
            conversation_id=None,
            language=request.language if hasattr(request, 'language') else "en-US",
            location=request.location.model_dump() if hasattr(request, 'location') and request.location else None,
            timezone=request.timezone if hasattr(request, 'timezone') else None
        )
        if isinstance(chat_response, dict) and "error" in chat_response:
            raise HTTPException(status_code=500, detail=chat_response["error"])
        
        response = chat_response
            
        return StartResponse(
            conversation_id=conversation_id,
            response=response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a message in an existing conversation
    """
    try:
        (response, conversation_id) = await chat_service.process_message(
            message=request.message,
            conversation_id=request.conversation_id
        )
        if isinstance(response, dict) and "error" in response:
            raise HTTPException(status_code=500, detail=response["error"])
        
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 