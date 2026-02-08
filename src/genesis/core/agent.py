"""Base agent class for the Genesis agent team framework."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from genesis.core.message import Message, MessageType


class AgentRole(Enum):
    """Predefined roles an agent can fulfill within a team."""

    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    CUSTOM = "custom"


@dataclass
class AgentState:
    """Tracks the internal state of an agent."""

    status: str = "idle"
    current_task: str | None = None
    history: list[Message] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Abstract base class for all agents in the team.

    Each agent has a name, a role, and can process messages
    asynchronously. Agents communicate through a shared message bus
    managed by the AgentTeam orchestrator.
    """

    def __init__(self, name: str, role: AgentRole, description: str = "") -> None:
        self.name = name
        self.role = role
        self.description = description or f"{role.value} agent"
        self.state = AgentState()
        self._inbox: asyncio.Queue[Message] = asyncio.Queue()

    @abstractmethod
    async def process(self, message: Message) -> Message | list[Message] | None:
        """Process an incoming message and optionally return response(s).

        This is the main logic of the agent. Subclasses must implement this
        to define how the agent handles each message it receives.
        """

    async def receive(self, message: Message) -> None:
        """Receive a message into the agent's inbox."""
        self.state.history.append(message)
        await self._inbox.put(message)

    async def run_once(self) -> Message | list[Message] | None:
        """Process the next message from the inbox."""
        message = await self._inbox.get()
        self.state.status = "working"
        self.state.current_task = message.content[:100]
        try:
            result = await self.process(message)
            return result
        finally:
            self.state.status = "idle"
            self.state.current_task = None

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, role={self.role.value!r})"
