"""LinkedIn client for fetching contacts and their recent posts."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from linkedin_api import Linkedin

from config.settings import (
    CHECK_PERIOD_DAYS,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    MAX_POSTS_PER_CONTACT,
)

logger = logging.getLogger(__name__)


@dataclass
class LinkedInPost:
    """Represents a LinkedIn post from a contact."""

    author_name: str
    author_headline: str
    author_profile_url: str
    text: str
    posted_at: datetime | None
    post_url: str = ""
    reactions_count: int = 0
    comments_count: int = 0


@dataclass
class LinkedInContact:
    """Represents a LinkedIn contact."""

    first_name: str
    last_name: str
    headline: str = ""
    profile_id: str = ""
    profile_url: str = ""
    posts: list[LinkedInPost] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class LinkedInClient:
    """Client to interact with LinkedIn and fetch contacts' posts."""

    def __init__(
        self, email: str = LINKEDIN_EMAIL, password: str = LINKEDIN_PASSWORD
    ):
        if not email or not password:
            raise ValueError(
                "LinkedIn credentials are required. "
                "Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in your .env file."
            )
        self._email = email
        self._password = password
        self._api: Linkedin | None = None

    def connect(self) -> None:
        """Authenticate to LinkedIn."""
        logger.info("Connecting to LinkedIn...")
        self._api = Linkedin(self._email, self._password)
        logger.info("Successfully connected to LinkedIn.")

    @property
    def api(self) -> Linkedin:
        if self._api is None:
            self.connect()
        return self._api

    def get_contacts(self) -> list[LinkedInContact]:
        """Fetch the user's LinkedIn connections."""
        logger.info("Fetching LinkedIn contacts...")
        connections = self.api.get_profile_connections()
        contacts = []
        for conn in connections:
            contact = LinkedInContact(
                first_name=conn.get("firstName", ""),
                last_name=conn.get("lastName", ""),
                headline=conn.get("headline", ""),
                profile_id=conn.get("public_id", conn.get("entityUrn", "")),
                profile_url=f"https://www.linkedin.com/in/{conn.get('public_id', '')}",
            )
            contacts.append(contact)
        logger.info("Found %d contacts.", len(contacts))
        return contacts

    def get_feed_posts(self, days: int = CHECK_PERIOD_DAYS) -> list[LinkedInPost]:
        """Fetch recent posts from the user's LinkedIn feed.

        This is the primary method for finding nominations - it reads
        the feed which contains posts from connections.
        """
        logger.info("Fetching LinkedIn feed posts from the last %d days...", days)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

        posts = []
        try:
            feed = self.api.get_feed_posts(limit=100)
            for item in feed:
                post = self._parse_feed_item(item)
                if post is None:
                    continue
                if post.posted_at and post.posted_at < cutoff:
                    continue
                posts.append(post)
        except Exception:
            logger.exception("Error fetching feed posts")

        logger.info("Retrieved %d feed posts from the last %d days.", len(posts), days)
        return posts

    def get_contact_posts(
        self,
        contact: LinkedInContact,
        days: int = CHECK_PERIOD_DAYS,
        max_posts: int = MAX_POSTS_PER_CONTACT,
    ) -> list[LinkedInPost]:
        """Fetch recent posts from a specific contact."""
        logger.info("Fetching posts for %s...", contact.full_name)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)

        posts = []
        try:
            profile_posts = self.api.get_profile_posts(
                contact.profile_id, post_count=max_posts
            )
            for item in profile_posts:
                post = self._parse_post_item(item, contact)
                if post is None:
                    continue
                if post.posted_at and post.posted_at < cutoff:
                    continue
                posts.append(post)
        except Exception:
            logger.exception("Error fetching posts for %s", contact.full_name)

        return posts

    def _parse_feed_item(self, item: dict) -> LinkedInPost | None:
        """Parse a feed item into a LinkedInPost."""
        try:
            actor = item.get("actor", {})
            author_name = actor.get("name", {}).get("text", "Unknown")
            author_headline = actor.get("description", {}).get("text", "")

            commentary = item.get("commentary", {})
            text = commentary.get("text", "") if commentary else ""
            if not text:
                return None

            posted_at = None
            created_at = item.get("createdAt")
            if created_at:
                posted_at = datetime.fromtimestamp(
                    created_at / 1000, tz=timezone.utc
                )

            social_counts = item.get("socialDetail", {})
            reactions = social_counts.get("totalSocialActivityCounts", {})

            return LinkedInPost(
                author_name=author_name,
                author_headline=author_headline,
                author_profile_url="",
                text=text,
                posted_at=posted_at,
                reactions_count=reactions.get("numLikes", 0),
                comments_count=reactions.get("numComments", 0),
            )
        except Exception:
            logger.debug("Failed to parse feed item", exc_info=True)
            return None

    def _parse_post_item(
        self, item: dict, contact: LinkedInContact
    ) -> LinkedInPost | None:
        """Parse a profile post item into a LinkedInPost."""
        try:
            commentary = item.get("commentary", {})
            text = commentary.get("text", "") if commentary else ""
            if not text:
                return None

            posted_at = None
            created_at = item.get("createdAt")
            if created_at:
                posted_at = datetime.fromtimestamp(
                    created_at / 1000, tz=timezone.utc
                )

            return LinkedInPost(
                author_name=contact.full_name,
                author_headline=contact.headline,
                author_profile_url=contact.profile_url,
                text=text,
                posted_at=posted_at,
            )
        except Exception:
            logger.debug("Failed to parse post item", exc_info=True)
            return None
