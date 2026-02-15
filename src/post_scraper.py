"""Scrape a single LinkedIn post from its URL."""

import logging
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from src.linkedin_client import LinkedInPost

logger = logging.getLogger(__name__)

# Patterns to extract the post/activity ID from a LinkedIn URL
_POST_URL_PATTERNS = [
    re.compile(r"linkedin\.com/posts/[^/]+-(\d+)-"),
    re.compile(r"linkedin\.com/feed/update/urn:li:activity:(\d+)"),
    re.compile(r"linkedin\.com/feed/update/urn:li:ugcPost:(\d+)"),
    re.compile(r"linkedin\.com/pulse/([^/?]+)"),
]


def extract_post_id(url: str) -> str | None:
    """Extract the LinkedIn post/activity ID from a URL."""
    for pattern in _POST_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def normalize_linkedin_url(url: str) -> str:
    """Clean and normalize a LinkedIn post URL."""
    url = url.strip()
    # Remove tracking parameters
    if "?" in url:
        url = url.split("?")[0]
    return url


class PostScraper:
    """Scrape individual LinkedIn posts from their URLs.

    Uses two strategies:
    1. LinkedIn API (if authenticated) — richer data
    2. Public page scraping (og: meta tags) — no auth needed, limited data
    """

    def __init__(self, linkedin_api=None):
        self._api = linkedin_api

    def scrape(self, url: str) -> LinkedInPost | None:
        """Scrape a LinkedIn post from its URL.

        Returns a LinkedInPost or None if the post couldn't be fetched.
        """
        url = normalize_linkedin_url(url)
        logger.info("Scraping post: %s", url)

        # Strategy 1: Use LinkedIn API if available
        if self._api:
            post = self._scrape_via_api(url)
            if post:
                return post

        # Strategy 2: Scrape the public page via meta tags
        return self._scrape_via_meta(url)

    def scrape_many(self, urls: list[str]) -> list[LinkedInPost]:
        """Scrape multiple LinkedIn posts."""
        posts = []
        for url in urls:
            post = self.scrape(url)
            if post:
                posts.append(post)
        return posts

    def _scrape_via_api(self, url: str) -> LinkedInPost | None:
        """Try to fetch post data via the LinkedIn API client."""
        post_id = extract_post_id(url)
        if not post_id:
            logger.debug("Could not extract post ID from URL: %s", url)
            return None

        try:
            post_data = self._api.get_post(post_id)
            if not post_data:
                return None

            commentary = post_data.get("commentary", {})
            text = commentary.get("text", "") if commentary else ""

            actor = post_data.get("actor", {})
            author_name = actor.get("name", {}).get("text", "Unknown")
            author_headline = actor.get("description", {}).get("text", "")

            posted_at = None
            created_at = post_data.get("createdAt")
            if created_at:
                posted_at = datetime.fromtimestamp(
                    created_at / 1000, tz=timezone.utc
                )

            return LinkedInPost(
                author_name=author_name,
                author_headline=author_headline,
                author_profile_url="",
                text=text,
                posted_at=posted_at,
                post_url=url,
            )
        except Exception:
            logger.debug("API scraping failed for %s", url, exc_info=True)
            return None

    def _scrape_via_meta(self, url: str) -> LinkedInPost | None:
        """Scrape post data from the public page using og: meta tags.

        This works without authentication but provides less data.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract from OpenGraph meta tags
            title = self._get_meta(soup, "og:title") or ""
            description = self._get_meta(soup, "og:description") or ""

            # The og:title often contains "Author Name on LinkedIn: post preview"
            author_name = "Unknown"
            text = description
            if " on LinkedIn:" in title:
                author_name = title.split(" on LinkedIn:")[0].strip()
                text = title.split(" on LinkedIn:")[1].strip()
                if description and description not in text:
                    text = f"{text}\n\n{description}"
            elif " sur LinkedIn :" in title:
                author_name = title.split(" sur LinkedIn :")[0].strip()
                text = title.split(" sur LinkedIn :")[1].strip()
                if description and description not in text:
                    text = f"{text}\n\n{description}"
            elif " - " in title:
                author_name = title.split(" - ")[0].strip()

            # Extract document/media URLs from meta tags
            image_url = self._get_meta(soup, "og:image") or ""

            return LinkedInPost(
                author_name=author_name,
                author_headline="",
                author_profile_url="",
                text=text,
                posted_at=datetime.now(tz=timezone.utc),
                post_url=url,
            )

        except Exception:
            logger.warning("Failed to scrape post from %s", url, exc_info=True)
            return None

    @staticmethod
    def _get_meta(soup: BeautifulSoup, property_name: str) -> str | None:
        tag = soup.find("meta", property=property_name)
        if tag and tag.get("content"):
            return tag["content"]
        return None
