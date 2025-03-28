from langchain_core.messages import AIMessage
import re
from langchain_core.messages.modifier import RemoveMessage
from langgraph.prebuilt.chat_agent_executor import AgentState


def clean_messages(messages):
  cleaned_messages = []
  for msg in messages:
      if isinstance(msg, AIMessage):
          cleaned_content = remove_thinking_tags(msg.content)
          # Create copy with updated content
          new_msg = msg.model_copy()
          new_msg.content = cleaned_content
          cleaned_messages.append(new_msg)
      else:
          cleaned_messages.append(msg)
      
  return cleaned_messages
  

def remove_thinking_tags(content: str) -> str:
    """Remove <thinking> tags and their content from the response."""
    if not content:
        return content
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()

def remove_failed_tool_call_attempt(state: AgentState):
    messages = state["messages"]
    # Remove all messages from the most recent
    # instance of AIMessage onwards.
    last_ai_message_index = next(
        i
        for i, msg in reversed(list(enumerate(messages)))
        if isinstance(msg, AIMessage)
    )
    messages_to_remove = messages[last_ai_message_index:]
    return {"messages": [RemoveMessage(id=m.id) for m in messages_to_remove]}
