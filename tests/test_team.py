"""Tests for the AgentTeam orchestrator."""

import pytest

from genesis.agents import CoderAgent, PlannerAgent, ResearcherAgent, ReviewerAgent
from genesis.core.message import Message, MessageType
from genesis.core.team import AgentTeam


@pytest.fixture
def full_team():
    team = AgentTeam(name="Test Team")
    team.add(PlannerAgent())
    team.add(ResearcherAgent())
    team.add(CoderAgent())
    team.add(ReviewerAgent())
    return team


def test_add_and_list_agents(full_team):
    assert len(full_team.agents) == 4
    names = {a.name for a in full_team.agents}
    assert names == {"planner", "researcher", "coder", "reviewer"}


def test_add_duplicate_raises():
    team = AgentTeam()
    team.add(PlannerAgent())
    with pytest.raises(ValueError, match="already exists"):
        team.add(PlannerAgent())


def test_remove_agent():
    team = AgentTeam()
    team.add(PlannerAgent())
    removed = team.remove("planner")
    assert removed.name == "planner"
    assert len(team.agents) == 0


def test_remove_missing_raises():
    team = AgentTeam()
    with pytest.raises(KeyError):
        team.remove("ghost")


def test_get_agent(full_team):
    planner = full_team.get("planner")
    assert planner.name == "planner"


def test_chaining():
    team = AgentTeam()
    result = team.add(PlannerAgent()).add(CoderAgent())
    assert result is team
    assert len(team.agents) == 2


@pytest.mark.asyncio
async def test_send_message(full_team):
    msg = Message(sender="team", recipient="planner", content="hello", msg_type=MessageType.TASK)
    await full_team.send(msg)
    assert len(full_team._message_log) == 1


@pytest.mark.asyncio
async def test_run_full_pipeline(full_team):
    result = await full_team.run("Create a hello world app")

    assert result.success
    assert result.task == "Create a hello world app"
    assert len(result.outputs) == 4  # one per agent
    assert result.summary  # non-empty


@pytest.mark.asyncio
async def test_run_partial_team():
    team = AgentTeam()
    team.add(PlannerAgent())
    team.add(ReviewerAgent())

    result = await team.run("Plan something")
    assert result.success
    assert len(result.outputs) == 2


@pytest.mark.asyncio
async def test_discuss(full_team):
    conversation = await full_team.discuss("Should we use REST or GraphQL?", rounds=2)
    assert len(conversation) == 8  # 4 agents * 2 rounds


def test_repr(full_team):
    r = repr(full_team)
    assert "Test Team" in r
    assert "planner" in r
