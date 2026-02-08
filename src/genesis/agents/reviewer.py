"""Reviewer agent — evaluates work and provides feedback."""

from __future__ import annotations

from genesis.core.agent import Agent, AgentRole
from genesis.core.message import Message, MessageType


class ReviewerAgent(Agent):
    """Reviews outputs from other agents and provides feedback.

    The reviewer is typically the last agent in the pipeline. It checks
    the quality of the work done so far and either approves it or
    requests changes.
    """

    def __init__(self, name: str = "reviewer") -> None:
        super().__init__(name=name, role=AgentRole.REVIEWER, description="Reviews work and provides feedback")
        self._reviews: list[dict[str, str]] = []

    async def process(self, message: Message) -> Message:
        content = message.content
        review = self._review(content)
        self._reviews.append({"input": content[:200], "review": review})

        return Message(
            sender=self.name,
            recipient=message.sender,
            content=review,
            msg_type=MessageType.FEEDBACK,
            parent_id=message.id,
            metadata={"approved": True, "review_count": len(self._reviews)},
        )

    def _review(self, content: str) -> str:
        """Review content and produce feedback.

        Stub implementation. In production, this would use an LLM
        to perform thorough code/content review.
        """
        checks = self._run_checks(content)
        status = "APPROVED" if all(checks.values()) else "CHANGES REQUESTED"

        lines = [
            f"Review result: {status}",
            "",
            "Checks performed:",
        ]
        for check_name, passed in checks.items():
            mark = "PASS" if passed else "FAIL"
            lines.append(f"  [{mark}] {check_name}")

        lines.extend([
            "",
            "Summary:",
            f"  - {sum(checks.values())}/{len(checks)} checks passed",
            f"  - Overall status: {status}",
        ])
        return "\n".join(lines)

    def _run_checks(self, content: str) -> dict[str, bool]:
        """Run quality checks on content."""
        return {
            "completeness": len(content) > 20,
            "clarity": "error" not in content.lower() or "handling" in content.lower(),
            "structure": "\n" in content,
            "actionable": any(kw in content.lower() for kw in ("implement", "creat", "generat", "complet", "ready", "status")),
        }
