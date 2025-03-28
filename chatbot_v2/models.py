from dataclasses import dataclass, field
from collections import deque
from typing import Optional, Dict, Any
import uuid

@dataclass
class ChatState:
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    history: list[dict[str, str]] = field(default_factory=list)
    active_workflow: Optional[str] = None
    workflow_state: dict[str, Any] = field(default_factory=dict)
    dependency_queue: deque = field(default_factory=deque)

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def add_dependency(self, dependency: str):
        if dependency not in self.dependency_queue:
            self.dependency_queue.append(dependency)