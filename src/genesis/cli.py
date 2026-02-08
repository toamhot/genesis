"""CLI entry point for Genesis agent team."""

from __future__ import annotations

import asyncio
import sys

from genesis.agents import CoderAgent, PlannerAgent, ResearcherAgent, ReviewerAgent
from genesis.core import AgentTeam


def create_default_team() -> AgentTeam:
    """Create a team with the four default agents."""
    team = AgentTeam(name="Genesis Team")
    team.add(PlannerAgent())
    team.add(ResearcherAgent())
    team.add(CoderAgent())
    team.add(ReviewerAgent())
    return team


async def run_task(task: str) -> None:
    """Run a task through the default agent team."""
    team = create_default_team()
    print(f"Team: {team}")
    print(f"Task: {task}")
    print("-" * 60)

    result = await team.run(task)

    print()
    for msg in result.outputs:
        print(f"--- {msg.sender} ({msg.msg_type.value}) ---")
        print(msg.content)
        print()

    print("=" * 60)
    print(f"Task completed — {len(result.outputs)} agent outputs")
    print(f"Summary:\n{result.summary}")


def main() -> None:
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Build a simple web API with health check endpoint"
    asyncio.run(run_task(task))


if __name__ == "__main__":
    main()
