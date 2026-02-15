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

# Ingest shared LinkedIn links (manual curation via "Partager")
python main.py --url https://linkedin.com/posts/...
python main.py --url https://linkedin.com/posts/... --notion
python main.py --file liens.txt --notion --output html
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
│   ├── post_scraper.py          # Single post scraper (from shared URLs)
│   ├── nomination_detector.py   # NLP nomination detection (keywords + LLM)
│   ├── document_extractor.py    # Download attachments (PDF, images, etc.)
│   ├── notion_client.py         # Notion database integration
│   └── reporter.py              # Output formatting (console/JSON/HTML)
├── tests/
│   ├── test_nomination_detector.py
│   ├── test_post_scraper.py
│   └── test_document_extractor.py
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
- `src/post_scraper.py` — Scrape individual posts from shared URLs
- `src/document_extractor.py` — Download attached documents (PDF, images, etc.)
- `src/notion_client.py` — Push nominations to a Notion database
- `config/settings.py` — All configuration loaded from environment
