"""Planner agent — breaks down tasks into actionable steps."""

from __future__ import annotations

from genesis.core.agent import Agent, AgentRole
from genesis.core.message import Message, MessageType


class PlannerAgent(Agent):
    """Analyzes a task and produces a structured plan.

    The planner is typically the first agent in the pipeline. It receives
    a high-level task description and decomposes it into concrete steps
    for the other agents to execute.
    """

    def __init__(self, name: str = "planner") -> None:
        super().__init__(name=name, role=AgentRole.PLANNER, description="Breaks down tasks into actionable steps")

    async def process(self, message: Message) -> Message:
        task = message.content
        steps = self._decompose(task)
        plan = self._format_plan(task, steps)

        return Message(
            sender=self.name,
            recipient=message.sender,
            content=plan,
            msg_type=MessageType.RESULT,
            parent_id=message.id,
            metadata={"steps": steps},
        )

    def _decompose(self, task: str) -> list[str]:
        """Break a task into logical steps.

        This is a rule-based decomposition. In a production system this
        would call an LLM or planning algorithm.
        """
        steps = []
        task_lower = task.lower()

        steps.append(f"Analyze requirements: {task[:100]}")

        if any(kw in task_lower for kw in ("research", "find", "search", "look up")):
            steps.append("Gather relevant information and references")

        if any(kw in task_lower for kw in ("build", "create", "implement", "code", "develop", "write")):
            steps.append("Design the solution architecture")
            steps.append("Implement the core functionality")
            steps.append("Add error handling and edge cases")

        if any(kw in task_lower for kw in ("test", "verify", "validate")):
            steps.append("Write tests for the implementation")

        if any(kw in task_lower for kw in ("fix", "bug", "debug", "error")):
            steps.append("Reproduce and isolate the issue")
            steps.append("Identify the root cause")
            steps.append("Apply the fix")

        steps.append("Review and validate the result")
        return steps

    def _format_plan(self, task: str, steps: list[str]) -> str:
        lines = [f"Plan for: {task}", ""]
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. {step}")
        lines.append(f"\nTotal steps: {len(steps)}")
        return "\n".join(lines)
