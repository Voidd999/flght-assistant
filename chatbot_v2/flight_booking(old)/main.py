import asyncio
from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from chatbot_v2.models import ChatState  # Import from models.py
from chatbot_v2.agent import process_user_input  # Import only process_user_input from agent.py

app = FastAPI(title="Flynas Chatbot API")

chat_states: Dict[str, ChatState] = {}

class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest) -> Dict[str, Any]:
    conversation_id = request.conversation_id or "default"
    if conversation_id not in chat_states:
        chat_states[conversation_id] = ChatState()
        initial_response = "Hey there! How can I assist you today? 😊✈️"
        chat_states[conversation_id].add_message("assistant", initial_response)
    else:
        initial_response = None
    state = chat_states[conversation_id]
    response = await process_user_input(state, request.message)
    chat_states[conversation_id] = state
    return {
        "conversation_id": conversation_id,
        "response": response,
        "initial": initial_response if initial_response else None
    }

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation_id = None
    try:
        while True:
            data = await websocket.receive_json()
            conversation_id = data.get("conversation_id", "default")
            message = data.get("message")
            if not message:
                await websocket.send_json({"error": "No message provided"})
                continue
            if conversation_id not in chat_states:
                chat_states[conversation_id] = ChatState()
                initial_response = "Hey there! How can I assist you today? 😊✈️"
                chat_states[conversation_id].add_message("assistant", initial_response)
                await websocket.send_json({
                    "conversation_id": conversation_id,
                    "response": initial_response,
                    "initial": True
                })
            else:
                initial_response = None
            state = chat_states[conversation_id]
            response = await process_user_input(state, message)
            chat_states[conversation_id] = state
            await websocket.send_json({
                "conversation_id": conversation_id,
                "response": response,
                "initial": False if initial_response is None else True
            })
    except Exception as e:
        if conversation_id:
            await websocket.send_json({"error": str(e)})
        await websocket.close()

@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)