"""AgentTeam orchestrator — coordinates agents and routes messages."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from genesis.core.agent import Agent
from genesis.core.message import Message, MessageType

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """The final output produced by the team for a given task."""

    task: str
    outputs: list[Message]
    success: bool = True
    summary: str = ""


class AgentTeam:
    """Orchestrates a group of agents working together on tasks.

    The team manages message routing between agents and coordinates
    the overall workflow: plan -> research -> code -> review.
    """

    def __init__(self, name: str = "Genesis Team") -> None:
        self.name = name
        self._agents: dict[str, Agent] = {}
        self._message_log: list[Message] = []
        self._max_rounds: int = 10

    def add(self, agent: Agent) -> AgentTeam:
        """Add an agent to the team. Returns self for chaining."""
        if agent.name in self._agents:
            raise ValueError(f"Agent with name {agent.name!r} already exists in the team")
        self._agents[agent.name] = agent
        logger.info("Added agent %s (%s) to team %s", agent.name, agent.role.value, self.name)
        return self

    def remove(self, name: str) -> Agent:
        """Remove and return an agent by name."""
        if name not in self._agents:
            raise KeyError(f"No agent named {name!r} in the team")
        return self._agents.pop(name)

    @property
    def agents(self) -> list[Agent]:
        """All agents currently in the team."""
        return list(self._agents.values())

    def get(self, name: str) -> Agent:
        """Get an agent by name."""
        return self._agents[name]

    async def send(self, message: Message) -> None:
        """Route a message to its recipient agent."""
        self._message_log.append(message)
        recipient = self._agents.get(message.recipient)
        if recipient is None:
            logger.warning("No agent named %r to receive message", message.recipient)
            return
        await recipient.receive(message)

    async def broadcast(self, sender: str, content: str, msg_type: MessageType = MessageType.STATUS) -> None:
        """Send a message from one agent to all others."""
        for name, agent in self._agents.items():
            if name != sender:
                msg = Message(sender=sender, recipient=name, content=content, msg_type=msg_type)
                await self.send(msg)

    async def run(self, task: str) -> TaskResult:
        """Run the team on a task using the standard pipeline.

        Pipeline: planner -> researcher -> coder -> reviewer.
        Agents that are not present in the team are skipped.
        """
        outputs: list[Message] = []
        pipeline = ["planner", "researcher", "coder", "reviewer"]
        active_agents = [self._agents[r] for r in pipeline if r in self._agents]

        if not active_agents:
            active_agents = list(self._agents.values())

        logger.info("Team %s starting task: %s", self.name, task[:80])

        previous_output = task
        for agent in active_agents:
            msg = Message(
                sender="team",
                recipient=agent.name,
                content=previous_output,
                msg_type=MessageType.TASK,
            )
            await self.send(msg)
            result = await agent.run_once()
            if result is not None:
                result_msgs = result if isinstance(result, list) else [result]
                outputs.extend(result_msgs)
                previous_output = result_msgs[-1].content

        summary = outputs[-1].content if outputs else "No output produced."
        return TaskResult(task=task, outputs=outputs, summary=summary)

    async def discuss(self, topic: str, rounds: int = 3) -> list[Message]:
        """Run a multi-round discussion between all agents on a topic.

        Each round, every agent sees the conversation so far and can contribute.
        """
        conversation: list[Message] = []
        current_content = topic

        for round_num in range(rounds):
            for agent in self._agents.values():
                msg = Message(
                    sender="team",
                    recipient=agent.name,
                    content=f"[Round {round_num + 1}] {current_content}",
                    msg_type=MessageType.QUESTION,
                    metadata={"round": round_num + 1, "conversation_length": len(conversation)},
                )
                await self.send(msg)
                result = await agent.run_once()
                if result is not None:
                    result_msgs = result if isinstance(result, list) else [result]
                    conversation.extend(result_msgs)
                    current_content = result_msgs[-1].content

        return conversation

    def __repr__(self) -> str:
        agent_list = ", ".join(a.name for a in self._agents.values())
        return f"AgentTeam(name={self.name!r}, agents=[{agent_list}])"
