"""Configuration settings for the LinkedIn Nomination Agent."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

# LinkedIn credentials
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# LLM API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Agent settings
CHECK_PERIOD_DAYS = int(os.getenv("CHECK_PERIOD_DAYS", "7"))
MAX_POSTS_PER_CONTACT = int(os.getenv("MAX_POSTS_PER_CONTACT", "10"))
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "console")  # console, json, html

# Nomination detection keywords (French + English)
NOMINATION_KEYWORDS_FR = [
    "nommé", "nommée", "nomination", "promu", "promue", "promotion",
    "nouveau poste", "nouvelle fonction", "prise de fonction",
    "rejoint", "a rejoint", "intègre", "j'intègre",
    "nouveau défi", "nouvelle aventure", "nouvelle étape",
    "heureux d'annoncer", "heureuse d'annoncer",
    "fier d'annoncer", "fière d'annoncer",
    "ravi d'annoncer", "ravie d'annoncer",
    "thrilled to announce", "excited to share",
    "directeur", "directrice", "vice-président", "vice-présidente",
    "CEO", "CTO", "CFO", "COO", "CMO",
    "head of", "responsable de", "manager",
    "associé", "associée", "partner",
]

NOMINATION_KEYWORDS_EN = [
    "appointed", "appointment", "promoted", "promotion",
    "new role", "new position", "new chapter",
    "joined", "joining", "starting",
    "thrilled to announce", "excited to announce",
    "pleased to announce", "happy to share",
    "proud to announce", "delighted to share",
    "new journey", "new adventure", "new challenge",
    "director", "vice president", "vp",
    "chief", "head of", "lead",
    "partner", "managing director",
]

NOMINATION_KEYWORDS = NOMINATION_KEYWORDS_FR + NOMINATION_KEYWORDS_EN
