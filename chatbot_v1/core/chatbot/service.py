import os
from typing import Dict, Optional, Any
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import logging
from .graph import graph
from langsmith import traceable
from .configuration import ChatConfig
from .state import State, Location
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from uuid import uuid4

logger = logging.getLogger(__name__)


class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    country: str
    city: str

class ChatRequest(BaseModel):
    initial_message: str
    language: str = "en-US"
    location: Optional[LocationRequest] = None
    timezone: Optional[str] = None


class ChatService:

    @traceable(name="process_message")
    async def process_message(
        self, 
        message: str, 
        conversation_id: Optional[str] = None,
        language: Optional[str] = "en-US",
        location: Optional[Dict[str, Any]] = None,
        timezone: Optional[str] = None
    ):
        """Process incoming chat messages with memory management"""
        error_message = "I can't process your request right now. Please try again later."
        try:
            redis_url = os.getenv("REDIS_URL")
            async with AsyncRedisSaver.from_conn_string(redis_url) as checkpointer:
                await checkpointer.asetup()

                # Initialize graph if not already initialized
                ai_graph = await graph(checkpointer)
                    
                logger.info('=== NEW API CALL ===')
                
                result = None
                if not conversation_id:
                    conversation_id = str(uuid4())
                    
                    # Convert location dict to Pydantic model if needed
                    if location:
                        location = Location(**location)
                        
                    # Initialize new state properly as dict-like
                    state = State()
                    state["language"] = language
                    state["location"] = location
                    state["timezone"] = timezone
                    state["messages"] = []
                                    
                    if message and message.strip() != "":
                        # Add the new message to state using dict access
                        logger.info(f"Human message: {message}")
                        state["messages"] = [HumanMessage(content=message)]
                    
                    
                    # Convert UUID to integer for thread_id
                    config = ChatConfig(
                        thread_id=conversation_id
                    )
                    
                    # Invoke the graph with async execution
                    try:
                        result = await ai_graph.ainvoke(state, config.model_dump())
                    except Exception as e:
                        logger.error(f"AI Error: {e}")
                        return {error_message, conversation_id}
                else:                    
                    try:
                        config = ChatConfig(thread_id=conversation_id)
                        logger.info(f"Human message: {message}")
                        input = {"messages": [HumanMessage(content=message)]}
                        result = await ai_graph.ainvoke(input, config.model_dump())
                    except Exception as e:
                        logger.error(f"AI Error: {e}")
                        return {error_message, conversation_id}
                
                # Add safety check for empty messages
                if not result.get("messages"):
                    logger.error(f"AI Error: No response generated")
                    return {error_message, conversation_id}
                
                # Extract AI response
                last_message = result["messages"][-1]                

                return (last_message.content, conversation_id)
                    
        except Exception as e:
            import traceback
            logger.error(f"Error processing message: {traceback.format_exc()}")
            logger.error(f"Error processing message: {e}")
            error_msg = str(e)
            return {"error": error_msg}