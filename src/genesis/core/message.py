"""Message system for inter-agent communication."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageType(Enum):
    """Types of messages exchanged between agents."""

    TASK = "task"
    RESULT = "result"
    QUESTION = "question"
    ANSWER = "answer"
    FEEDBACK = "feedback"
    STATUS = "status"


@dataclass
class Message:
    """A message exchanged between agents in the team."""

    sender: str
    recipient: str
    content: str
    msg_type: MessageType
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_id: str | None = None

    def reply(self, sender: str, content: str, msg_type: MessageType | None = None) -> Message:
        """Create a reply to this message."""
        return Message(
            sender=sender,
            recipient=self.sender,
            content=content,
            msg_type=msg_type or MessageType.ANSWER,
            parent_id=self.id,
        )

    def __str__(self) -> str:
        return f"[{self.msg_type.value}] {self.sender} -> {self.recipient}: {self.content[:80]}"
