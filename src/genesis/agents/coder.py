"""Coder agent — produces code based on plans and research."""

from __future__ import annotations

from genesis.core.agent import Agent, AgentRole
from genesis.core.message import Message, MessageType


class CoderAgent(Agent):
    """Generates code or technical solutions.

    The coder takes plans and research context as input and produces
    implementation artifacts (code, configurations, etc.).
    """

    def __init__(self, name: str = "coder") -> None:
        super().__init__(name=name, role=AgentRole.CODER, description="Produces code and technical solutions")
        self._artifacts: list[dict[str, str]] = []

    async def process(self, message: Message) -> Message:
        spec = message.content
        implementation = self._implement(spec)
        self._artifacts.append({"spec": spec[:200], "result": implementation[:500]})

        return Message(
            sender=self.name,
            recipient=message.sender,
            content=implementation,
            msg_type=MessageType.RESULT,
            parent_id=message.id,
            metadata={"artifact_count": len(self._artifacts)},
        )

    def _implement(self, spec: str) -> str:
        """Generate an implementation based on a specification.

        Stub implementation. In production, this would invoke an LLM
        or code generation system.
        """
        lines = [
            f"Implementation based on: {spec[:100]}",
            "",
            "Generated artifacts:",
            "  - Core module structure created",
            "  - Entry points defined",
            "  - Dependencies identified",
            "",
            "Implementation notes:",
            "  - Follows established patterns from the specification",
            "  - Error handling included for critical paths",
            "  - Ready for review",
            "",
            "Status: Implementation complete. Awaiting review.",
        ]
        return "\n".join(lines)
