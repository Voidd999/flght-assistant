import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from app.core.chatbot.utils.redis_client import get_redis_client

# Constants
CONVERSATION_TTL = 60 * 60 * 24  # 24 hours in seconds
CONVERSATION_PREFIX = "conv:"
ENTITY_PREFIX = "entity:"

class ChatMemory:
    def __init__(self):
        pass

    def _get_conversation_key(self, conversation_id: str) -> str:
        return f"{CONVERSATION_PREFIX}{conversation_id}"

    
    def _get_entity_key(self, conversation_id: str) -> str:
        return f"{ENTITY_PREFIX}{conversation_id}"

    def _serialize_message(self, message: BaseMessage) -> Dict[str, Any]:
        data = {
            "type": message.__class__.__name__,
            "content": message.content,
            "additional_kwargs": message.additional_kwargs
        }
        # Include tool_call_id for ToolMessage, if available
        if isinstance(message, ToolMessage):
            data["tool_call_id"] = getattr(message, "tool_call_id", "")
        return data

    def _deserialize_message(self, message_dict: Dict[str, Any]) -> BaseMessage:
        message_type = message_dict["type"]
        if message_type == "HumanMessage":
            return HumanMessage(
                content=message_dict["content"],
                additional_kwargs=message_dict["additional_kwargs"]
            )
        elif message_type == "AIMessage":
            return AIMessage(
                content=message_dict["content"],
                additional_kwargs=message_dict["additional_kwargs"]
            )
        elif message_type == "ToolMessage":
            # Get tool_call_id from the serialized data or default to an empty string.
            tool_call_id = message_dict.get("tool_call_id", "")
            return ToolMessage(
                content=message_dict["content"],
                additional_kwargs=message_dict["additional_kwargs"],
                tool_call_id=tool_call_id
            )
        else:
            raise ValueError(f"Unknown message type: {message_type}")

    async def load_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load the conversation state for a given conversation ID."""
        REDIS_CLIENT = get_redis_client()
        conv_key = self._get_conversation_key(conversation_id)
        entity_key = self._get_entity_key(conversation_id)
        
        # Get conversation history
        conv_data = REDIS_CLIENT.get(conv_key)
        if not conv_data:
            return None
        
        conv_state = json.loads(conv_data)
        
        # Deserialize messages
        if "messages" in conv_state:
            conv_state["messages"] = [
                self._deserialize_message(msg) for msg in conv_state["messages"]
            ]
        
        # Get entity memory
        entity_data = REDIS_CLIENT.get(entity_key)
        if entity_data:
            conv_state["entities"] = json.loads(entity_data)
            
        return conv_state

    async def save_conversation_state(self, conversation_id: str, state: Dict[str, Any]) -> None:
        """Save the conversation state for a given conversation ID."""
        REDIS_CLIENT = get_redis_client()
        conv_key = self._get_conversation_key(conversation_id)
        entity_key = self._get_entity_key(conversation_id)
        
        # Prepare conversation state for serialization
        serialized_state = state.copy()
        if "messages" in serialized_state:
            serialized_state["messages"] = [
                self._serialize_message(msg) for msg in serialized_state["messages"]
            ]
        
        # Extract entities if present
        entities = serialized_state.pop("entities", None)
        
        # Save conversation state
        REDIS_CLIENT.set(
            conv_key,
            json.dumps(serialized_state),
            ex=CONVERSATION_TTL
        )
        
        # Save entities separately if present
        if entities:
            REDIS_CLIENT.setex(
                entity_key,
                CONVERSATION_TTL,
                json.dumps(entities)
            )

    async def clear_conversation_state(self, conversation_id: str) -> None:
        """Remove the conversation state for a given conversation ID."""
        REDIS_CLIENT = get_redis_client()
        conv_key = self._get_conversation_key(conversation_id)
        entity_key = self._get_entity_key(conversation_id)
        
        REDIS_CLIENT.delete(conv_key)
        REDIS_CLIENT.delete(entity_key)

    async def extend_conversation_ttl(self, conversation_id: str) -> None:
        """Extend the TTL of a conversation, typically called after each interaction."""
        REDIS_CLIENT = get_redis_client()
        conv_key = self._get_conversation_key(conversation_id)
        entity_key = self._get_entity_key(conversation_id)
        
        REDIS_CLIENT.expire(conv_key, CONVERSATION_TTL)
        REDIS_CLIENT.expire(entity_key, CONVERSATION_TTL)

    async def get_active_conversations(self) -> list[str]:
        """Get a list of all active conversation IDs."""
        REDIS_CLIENT = get_redis_client()
        pattern = f"{CONVERSATION_PREFIX}*"
        keys = REDIS_CLIENT.keys(pattern)
        return [key.decode('utf-8').replace(CONVERSATION_PREFIX, '') for key in keys]

    async def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations. Returns number of conversations cleaned up."""
        REDIS_CLIENT = get_redis_client()
        active_convs = self.get_active_conversations()
        cleaned = 0
        
        for conv_id in active_convs:
            conv_key = self._get_conversation_key(conv_id)
            if not REDIS_CLIENT.ttl(conv_key):
                self.clear_conversation_state(conv_id)
                cleaned += 1
                
        return cleaned 