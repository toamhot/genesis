# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

Genesis - A Python framework for creating and managing AI expert skills/personas that can be used with Claude. Each skill defines a specialized expert with domain-specific knowledge and communication style. Skills can be connected to document knowledge bases via Claude Projects.

## Build & Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the main script to see available skills
python main.py

# Use a skill's prompt with Claude
python -c "from src.skills import BCGCreditRiskExpert; print(BCGCreditRiskExpert().system_prompt)"

# Convert PowerPoint files to PDF (optional, improves text extraction)
python scripts/convert_ppt_to_pdf.py data/documents/
```

## Using Skills with Claude Projects

The recommended way to use skills with a document knowledge base:

1. **Create a Claude Project** at [claude.ai](https://claude.ai)
2. **Copy the system prompt** from `docs/system_prompt.txt`
3. **Upload your documents** (PDF, PPT, Word)
4. **Start chatting** with your expert

See `docs/claude_project_setup.md` for detailed instructions.

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
│   │   └── engine.py           # SkillEngine for managing skills
│   └── skills/
│       ├── base.py             # Abstract Skill base class
│       └── bcg_credit_risk/    # BCG Credit Risk Expert skill
│           ├── skill.py        # Skill implementation
│           └── prompts.py      # System prompts
├── docs/
│   ├── system_prompt.txt       # Ready-to-copy prompt for Claude Projects
│   └── claude_project_setup.md # Setup guide for Claude Projects
├── scripts/
│   └── convert_ppt_to_pdf.py   # PPT to PDF converter
├── data/
│   └── documents/              # Place your documents here
├── tests/                      # Test files
├── main.py                     # Example usage script
├── requirements.txt            # Dependencies
└── CLAUDE.md                   # This file
```

## Code Style

- Python 3.10+ required
- Use dataclasses for skill definitions
- Follow PEP 8 conventions
- Format with black, lint with ruff
- Type hints required for all functions

## Key Files

- `docs/system_prompt.txt` - Ready-to-use prompt for Claude Projects
- `docs/claude_project_setup.md` - Step-by-step Claude Project setup
- `src/skills/base.py` - Base Skill class that all skills inherit from
- `src/skills/bcg_credit_risk/prompts.py` - System prompt for BCG expert
- `src/core/engine.py` - SkillEngine for registering and using skills

## Creating a New Skill

1. Create a new directory under `src/skills/`
2. Create `skill.py` implementing the `Skill` base class
3. Create `prompts.py` with the system prompt
4. Register in `src/skills/__init__.py`
5. Export the prompt to `docs/` for Claude Projects usage
