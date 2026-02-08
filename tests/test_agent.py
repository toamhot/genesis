"""Tests for the base agent and specialized agents."""

import pytest

from genesis.agents import CoderAgent, PlannerAgent, ResearcherAgent, ReviewerAgent
from genesis.core.agent import AgentRole
from genesis.core.message import Message, MessageType


@pytest.fixture
def task_message():
    return Message(sender="team", recipient="test", content="Build a REST API", msg_type=MessageType.TASK)


@pytest.mark.asyncio
async def test_planner_produces_plan(task_message):
    planner = PlannerAgent()
    task_message.recipient = planner.name
    result = await planner.process(task_message)

    assert result.sender == "planner"
    assert result.msg_type == MessageType.RESULT
    assert "Plan for:" in result.content
    assert result.parent_id == task_message.id


@pytest.mark.asyncio
async def test_researcher_produces_findings(task_message):
    researcher = ResearcherAgent()
    task_message.recipient = researcher.name
    result = await researcher.process(task_message)

    assert result.sender == "researcher"
    assert "Research findings" in result.content


@pytest.mark.asyncio
async def test_coder_produces_implementation(task_message):
    coder = CoderAgent()
    task_message.recipient = coder.name
    result = await coder.process(task_message)

    assert result.sender == "coder"
    assert "Implementation" in result.content


@pytest.mark.asyncio
async def test_reviewer_produces_review(task_message):
    reviewer = ReviewerAgent()
    task_message.recipient = reviewer.name
    result = await reviewer.process(task_message)

    assert result.sender == "reviewer"
    assert result.msg_type == MessageType.FEEDBACK
    assert "Review result" in result.content


@pytest.mark.asyncio
async def test_agent_receive_and_run_once():
    agent = PlannerAgent()
    msg = Message(sender="team", recipient=agent.name, content="Do something", msg_type=MessageType.TASK)
    await agent.receive(msg)
    result = await agent.run_once()

    assert result is not None
    assert result.sender == "planner"
    assert len(agent.state.history) == 1


def test_agent_roles():
    assert PlannerAgent().role == AgentRole.PLANNER
    assert ResearcherAgent().role == AgentRole.RESEARCHER
    assert CoderAgent().role == AgentRole.CODER
    assert ReviewerAgent().role == AgentRole.REVIEWER
