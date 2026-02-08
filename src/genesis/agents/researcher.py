"""Researcher agent — gathers and synthesizes information."""

from __future__ import annotations

from genesis.core.agent import Agent, AgentRole
from genesis.core.message import Message, MessageType


class ResearcherAgent(Agent):
    """Gathers context, references, and background information.

    The researcher processes tasks or questions by collecting relevant
    data points and synthesizing them into a concise briefing for
    downstream agents.
    """

    def __init__(self, name: str = "researcher") -> None:
        super().__init__(name=name, role=AgentRole.RESEARCHER, description="Gathers and synthesizes information")
        self._knowledge_base: dict[str, str] = {}

    async def process(self, message: Message) -> Message:
        topic = message.content
        findings = self._research(topic)
        self._knowledge_base[message.id] = findings

        return Message(
            sender=self.name,
            recipient=message.sender,
            content=findings,
            msg_type=MessageType.RESULT,
            parent_id=message.id,
            metadata={"source": "internal_analysis"},
        )

    def _research(self, topic: str) -> str:
        """Analyze a topic and produce findings.

        This is a stub implementation. In production, this would
        query knowledge bases, APIs, or an LLM.
        """
        keywords = self._extract_keywords(topic)
        lines = [
            f"Research findings for: {topic[:100]}",
            "",
            f"Key concepts identified: {', '.join(keywords)}",
            "",
            "Analysis:",
            f"  - The topic involves {len(keywords)} main concepts",
            f"  - Recommended approach: systematic breakdown of {keywords[0] if keywords else 'the problem'}",
            "  - Relevant areas to investigate further have been noted",
            "",
            "Status: Research phase complete. Ready for implementation.",
        ]
        return "\n".join(lines)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "can", "shall",
                      "to", "of", "in", "for", "on", "with", "at", "by", "from",
                      "it", "this", "that", "and", "or", "but", "not", "if", "then"}
        words = text.lower().split()
        keywords = [w.strip(".,!?;:()[]{}\"'") for w in words if w.lower().strip(".,!?;:()[]{}\"'") not in stop_words]
        return keywords[:10]
