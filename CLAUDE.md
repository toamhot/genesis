# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

Genesis — LinkedIn Nomination Agent: an automated agent that scans your LinkedIn contacts' posts to detect nominations, promotions, and new role announcements from the past week.

## Build & Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your LinkedIn credentials and optional LLM API keys

# Run the agent
python main.py

# Run with options
python main.py --mode feed --days 7 --output console
python main.py --mode contacts --output json
python main.py --mode both --output html --no-llm
```

## Testing

```bash
# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Project Structure

```
genesis/
├── main.py                      # Entry point (CLI)
├── config/
│   └── settings.py              # Configuration & environment vars
├── src/
│   ├── agent.py                 # Main orchestrator agent
│   ├── linkedin_client.py       # LinkedIn API client
│   ├── nomination_detector.py   # NLP nomination detection (keywords + LLM)
│   └── reporter.py              # Output formatting (console/JSON/HTML)
├── tests/
│   └── test_nomination_detector.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Code Style

- Python 3.12+
- Type hints throughout
- Dataclasses for data models
- Logging via stdlib `logging`

## Key Files

- `main.py` — CLI entry point with argparse
- `src/agent.py` — Orchestrator that ties LinkedIn client, detector, and reporter together
- `src/nomination_detector.py` — Core detection logic (keyword matching + optional LLM)
- `config/settings.py` — All configuration loaded from environment
