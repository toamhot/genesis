# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

Genesis - A Python framework for creating and managing AI expert skills/personas that can be used with Claude. Each skill defines a specialized expert with domain-specific knowledge and communication style.

## Build & Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main script to see available skills
python main.py

# Use a skill's prompt with Claude
python -c "from src.skills import BCGCreditRiskExpert; print(BCGCreditRiskExpert().system_prompt)"
```

## Testing

```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest --cov=src tests/
```

## Project Structure

```
genesis/
├── src/
│   ├── core/
│   │   └── engine.py        # SkillEngine for managing skills
│   └── skills/
│       ├── base.py          # Abstract Skill base class
│       └── bcg_credit_risk/ # BCG Credit Risk Expert skill
│           ├── skill.py     # Skill implementation
│           └── prompts.py   # System prompts
├── tests/                   # Test files
├── main.py                  # Example usage script
├── requirements.txt         # Dependencies
└── CLAUDE.md               # This file
```

## Code Style

- Python 3.10+ required
- Use dataclasses for skill definitions
- Follow PEP 8 conventions
- Format with black, lint with ruff
- Type hints required for all functions

## Key Files

- `src/skills/base.py` - Base Skill class that all skills inherit from
- `src/skills/bcg_credit_risk/prompts.py` - System prompt for BCG expert
- `src/core/engine.py` - SkillEngine for registering and using skills
- `main.py` - Example demonstrating how to use skills

## Creating a New Skill

1. Create a new directory under `src/skills/`
2. Create `skill.py` implementing the `Skill` base class
3. Create `prompts.py` with the system prompt
4. Register in `src/skills/__init__.py`
