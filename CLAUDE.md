# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

Genesis - A multi-agent team framework for collaborative task solving. It provides a base `Agent` class, four specialized agents (Planner, Researcher, Coder, Reviewer), and an `AgentTeam` orchestrator that coordinates them through a message-passing pipeline.

## Build & Development

```bash
# Install dependencies (dev mode)
pip install -e ".[dev]"

# Run the CLI with a task
genesis "Build a REST API"
# or
python -m genesis.cli "Build a REST API"
```

## Testing

```bash
# Run tests
pytest

# Run tests with verbose output
pytest -v
```

## Project Structure

```
genesis/
├── src/genesis/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── core/
│   │   ├── agent.py         # Base Agent class and AgentRole enum
│   │   ├── message.py       # Message and MessageType for inter-agent comms
│   │   └── team.py          # AgentTeam orchestrator
│   └── agents/
│       ├── planner.py        # PlannerAgent — decomposes tasks into steps
│       ├── researcher.py     # ResearcherAgent — gathers information
│       ├── coder.py          # CoderAgent — produces implementations
│       └── reviewer.py       # ReviewerAgent — reviews and approves work
├── tests/
│   ├── test_message.py
│   ├── test_agent.py
│   └── test_team.py
└── pyproject.toml
```

## Code Style

- Python 3.10+, async/await throughout
- Type hints on all public APIs
- `from __future__ import annotations` in every module

## Key Files

- `src/genesis/core/team.py` — the main orchestrator, start here
- `src/genesis/core/agent.py` — base class to extend for custom agents
- `src/genesis/cli.py` — CLI entry point
