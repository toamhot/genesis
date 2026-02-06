"""Nomination detection module using keyword matching and optional LLM analysis."""

import json
import logging
import re
from dataclasses import dataclass

from config.settings import ANTHROPIC_API_KEY, NOMINATION_KEYWORDS, OPENAI_API_KEY
from src.linkedin_client import LinkedInPost

logger = logging.getLogger(__name__)


@dataclass
class Nomination:
    """Represents a detected nomination/appointment."""

    person_name: str
    person_headline: str
    person_profile_url: str
    new_role: str
    company: str
    nomination_type: str  # "new_position", "promotion", "appointment", "other"
    confidence: float  # 0.0 to 1.0
    source_text: str
    posted_at: str

    def summary(self) -> str:
        parts = [f"{self.person_name}"]
        if self.nomination_type == "promotion":
            parts.append("a été promu(e)")
        elif self.nomination_type == "new_position":
            parts.append("a pris un nouveau poste")
        elif self.nomination_type == "appointment":
            parts.append("a été nommé(e)")
        else:
            parts.append("a un changement de poste")

        if self.new_role:
            parts.append(f"en tant que {self.new_role}")
        if self.company:
            parts.append(f"chez {self.company}")

        return " ".join(parts)


class NominationDetector:
    """Detects nominations in LinkedIn posts using keyword matching and LLM."""

    def __init__(self, use_llm: bool = True):
        self._use_llm = use_llm and (ANTHROPIC_API_KEY or OPENAI_API_KEY)
        if self._use_llm:
            logger.info("LLM-based nomination detection enabled.")
        else:
            logger.info("Using keyword-based nomination detection only.")

    def detect(self, posts: list[LinkedInPost]) -> list[Nomination]:
        """Detect nominations across a list of posts."""
        nominations = []
        for post in posts:
            nomination = self._analyze_post(post)
            if nomination is not None:
                nominations.append(nomination)

        nominations.sort(key=lambda n: n.confidence, reverse=True)
        logger.info("Detected %d nominations out of %d posts.", len(nominations), len(posts))
        return nominations

    def _analyze_post(self, post: LinkedInPost) -> Nomination | None:
        """Analyze a single post for nomination content."""
        keyword_result = self._keyword_detection(post)

        if not keyword_result:
            return None

        if self._use_llm:
            llm_result = self._llm_detection(post)
            if llm_result is not None:
                return llm_result

        return keyword_result

    def _keyword_detection(self, post: LinkedInPost) -> Nomination | None:
        """Detect nominations using keyword matching."""
        text_lower = post.text.lower()
        matched_keywords = [kw for kw in NOMINATION_KEYWORDS if kw.lower() in text_lower]

        if not matched_keywords:
            return None

        confidence = min(len(matched_keywords) * 0.2, 0.8)
        nomination_type = self._infer_type_from_keywords(matched_keywords)
        new_role = self._extract_role(post.text)
        company = self._extract_company(post.text)

        return Nomination(
            person_name=post.author_name,
            person_headline=post.author_headline,
            person_profile_url=post.author_profile_url,
            new_role=new_role,
            company=company,
            nomination_type=nomination_type,
            confidence=confidence,
            source_text=post.text[:500],
            posted_at=post.posted_at.isoformat() if post.posted_at else "unknown",
        )

    def _infer_type_from_keywords(self, keywords: list[str]) -> str:
        """Infer nomination type from matched keywords."""
        keywords_lower = [k.lower() for k in keywords]
        joined = " ".join(keywords_lower)

        if any(w in joined for w in ["promu", "promue", "promotion", "promoted"]):
            return "promotion"
        if any(w in joined for w in ["nommé", "nommée", "nomination", "appointed", "appointment"]):
            return "appointment"
        if any(w in joined for w in ["rejoint", "intègre", "joined", "joining", "starting"]):
            return "new_position"
        return "other"

    def _extract_role(self, text: str) -> str:
        """Try to extract the role/title from the post text."""
        role_patterns = [
            r"(?:en tant que|comme|as|role of|poste de)\s+([A-ZÀ-Ü][^,.!\n]{3,50})",
            r"(?:nouveau poste|new role|new position)[:\s]+([A-ZÀ-Ü][^,.!\n]{3,50})",
            r"(?:nommé|nommée|appointed|promoted to)\s+([A-ZÀ-Ü][^,.!\n]{3,50})",
        ]
        for pattern in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_company(self, text: str) -> str:
        """Try to extract the company name from the post text."""
        company_patterns = [
            r"(?:chez|at|@|rejoint|joined|joining)\s+([A-ZÀ-Ü][\w\s&.-]{1,40}?)(?:\s*[!.,;]|\s+(?:en|pour|as|where|in)\b)",
            r"(?:chez|at|@)\s+([A-ZÀ-Ü][\w\s&.-]{1,40})",
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return ""

    def _llm_detection(self, post: LinkedInPost) -> Nomination | None:
        """Use an LLM to analyze the post for nomination content."""
        prompt = self._build_llm_prompt(post)

        try:
            if ANTHROPIC_API_KEY:
                return self._call_anthropic(prompt, post)
            elif OPENAI_API_KEY:
                return self._call_openai(prompt, post)
        except Exception:
            logger.warning("LLM analysis failed, falling back to keyword detection.", exc_info=True)

        return None

    def _build_llm_prompt(self, post: LinkedInPost) -> str:
        return f"""Analyze this LinkedIn post and determine if it announces a nomination,
new position, promotion, or appointment. Respond ONLY with a JSON object.

Post by {post.author_name} ({post.author_headline}):
\"\"\"
{post.text[:1000]}
\"\"\"

If this IS a nomination/appointment announcement, respond with:
{{
  "is_nomination": true,
  "person_name": "name of the person being nominated",
  "new_role": "the new role/title",
  "company": "the company name",
  "nomination_type": "new_position|promotion|appointment|other",
  "confidence": 0.0-1.0
}}

If this is NOT a nomination, respond with:
{{
  "is_nomination": false
}}"""

    def _call_anthropic(self, prompt: str, post: LinkedInPost) -> Nomination | None:
        """Call Anthropic API for nomination analysis."""
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return self._parse_llm_response(response.content[0].text, post)

    def _call_openai(self, prompt: str, post: LinkedInPost) -> Nomination | None:
        """Call OpenAI API for nomination analysis."""
        import openai

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        return self._parse_llm_response(response.choices[0].message.content, post)

    def _parse_llm_response(
        self, response_text: str, post: LinkedInPost
    ) -> Nomination | None:
        """Parse the LLM response into a Nomination object."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            if not data.get("is_nomination", False):
                return None

            return Nomination(
                person_name=data.get("person_name", post.author_name),
                person_headline=post.author_headline,
                person_profile_url=post.author_profile_url,
                new_role=data.get("new_role", ""),
                company=data.get("company", ""),
                nomination_type=data.get("nomination_type", "other"),
                confidence=float(data.get("confidence", 0.7)),
                source_text=post.text[:500],
                posted_at=post.posted_at.isoformat() if post.posted_at else "unknown",
            )
        except (json.JSONDecodeError, ValueError):
            logger.debug("Failed to parse LLM response: %s", response_text[:200])
            return None
