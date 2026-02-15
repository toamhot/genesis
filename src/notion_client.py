"""Notion integration for storing nomination data and managing the Inbox."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from notion_client import Client as NotionAPI

from config.settings import (
    NOTION_API_KEY,
    NOTION_DATABASE_ID,
    NOTION_INBOX_DATABASE_ID,
)
from src.document_extractor import Attachment
from src.nomination_detector import Nomination

logger = logging.getLogger(__name__)

# Schema for the Genesis Nominations database
DATABASE_PROPERTIES = {
    "Nom": {"title": {}},
    "Rôle": {"rich_text": {}},
    "Entreprise": {"rich_text": {}},
    "Type": {
        "select": {
            "options": [
                {"name": "Nouveau poste", "color": "blue"},
                {"name": "Promotion", "color": "green"},
                {"name": "Nomination", "color": "purple"},
                {"name": "Autre", "color": "gray"},
            ]
        }
    },
    "Confiance": {"number": {"format": "percent"}},
    "Date du post": {"date": {}},
    "Lien LinkedIn": {"url": {}},
    "Profil LinkedIn": {"url": {}},
    "Headline": {"rich_text": {}},
    "Extrait": {"rich_text": {}},
    "Documents": {"files": {}},
    "Date d'ajout": {"date": {}},
    "Source": {
        "select": {
            "options": [
                {"name": "Feed scan", "color": "blue"},
                {"name": "Contact scan", "color": "green"},
                {"name": "Lien partagé", "color": "orange"},
                {"name": "Inbox", "color": "yellow"},
            ]
        }
    },
}

# Schema for the Inbox database
INBOX_PROPERTIES = {
    "URL": {"title": {}},
    "Statut": {
        "select": {
            "options": [
                {"name": "Nouveau", "color": "default"},
                {"name": "En cours", "color": "yellow"},
                {"name": "Nomination", "color": "green"},
                {"name": "Pas une nomination", "color": "gray"},
                {"name": "Erreur", "color": "red"},
            ]
        }
    },
    "Notes": {"rich_text": {}},
    "Date d'ajout": {"date": {}},
    "Résultat": {"rich_text": {}},
}

TYPE_LABELS = {
    "new_position": "Nouveau poste",
    "promotion": "Promotion",
    "appointment": "Nomination",
    "other": "Autre",
}


@dataclass
class InboxEntry:
    """Represents an entry in the Notion Inbox."""

    page_id: str
    url: str
    notes: str = ""


class NotionClient:
    """Client for storing nominations in a Notion database."""

    def __init__(
        self,
        api_key: str = NOTION_API_KEY,
        database_id: str = NOTION_DATABASE_ID,
        inbox_database_id: str = NOTION_INBOX_DATABASE_ID,
    ):
        if not api_key:
            raise ValueError(
                "Notion API key is required. Set NOTION_API_KEY in your .env file.\n"
                "Create an integration at https://www.notion.so/my-integrations"
            )
        self._client = NotionAPI(auth=api_key)
        self._database_id = database_id
        self._inbox_database_id = inbox_database_id

    # ── Database setup ──────────────────────────────────────────────

    def setup_database(self, parent_page_id: str) -> str:
        """Create the Genesis nominations database in Notion."""
        logger.info("Creating Genesis database in Notion...")

        response = self._client.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": "Genesis - Nominations LinkedIn"}}],
            properties=DATABASE_PROPERTIES,
        )

        db_id = response["id"]
        self._database_id = db_id
        logger.info("Nominations database created: %s", db_id)
        return db_id

    def setup_inbox(self, parent_page_id: str) -> str:
        """Create the Inbox database in Notion.

        The Inbox is where users paste LinkedIn URLs for the agent to process.

        Args:
            parent_page_id: The Notion page ID where the database will be created.

        Returns:
            The newly created Inbox database ID.
        """
        logger.info("Creating Inbox database in Notion...")

        response = self._client.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": "Genesis - Inbox LinkedIn"}}],
            properties=INBOX_PROPERTIES,
            description=[
                {
                    "type": "text",
                    "text": {
                        "content": (
                            "Collez vos liens LinkedIn ici. "
                            "L'agent les traitera automatiquement."
                        )
                    },
                }
            ],
        )

        db_id = response["id"]
        self._inbox_database_id = db_id
        logger.info("Inbox database created: %s", db_id)
        return db_id

    # ── Inbox management ────────────────────────────────────────────

    def get_pending_inbox_entries(self) -> list[InboxEntry]:
        """Fetch all Inbox entries with status 'Nouveau' (pending processing)."""
        if not self._inbox_database_id:
            raise ValueError(
                "No Inbox database ID. Set NOTION_INBOX_DATABASE_ID in .env "
                "or run --setup-inbox first."
            )

        response = self._client.databases.query(
            database_id=self._inbox_database_id,
            filter={
                "property": "Statut",
                "select": {"equals": "Nouveau"},
            },
            sorts=[{"property": "Date d'ajout", "direction": "ascending"}],
        )

        entries = []
        for page in response.get("results", []):
            props = page["properties"]

            # Extract URL from title
            title_parts = props.get("URL", {}).get("title", [])
            url = title_parts[0]["plain_text"] if title_parts else ""

            # Extract notes
            notes_parts = props.get("Notes", {}).get("rich_text", [])
            notes = notes_parts[0]["plain_text"] if notes_parts else ""

            if url and "linkedin.com" in url:
                entries.append(InboxEntry(
                    page_id=page["id"],
                    url=url.strip(),
                    notes=notes,
                ))

        logger.info("Found %d pending entries in Inbox.", len(entries))
        return entries

    def update_inbox_status(
        self,
        page_id: str,
        status: str,
        result_text: str = "",
    ) -> None:
        """Update the status of an Inbox entry after processing.

        Args:
            page_id: The Notion page ID of the inbox entry.
            status: One of: "En cours", "Nomination", "Pas une nomination", "Erreur"
            result_text: Summary text to store in the "Résultat" field.
        """
        properties: dict = {
            "Statut": {"select": {"name": status}},
        }

        if result_text:
            properties["Résultat"] = {
                "rich_text": [{"text": {"content": result_text[:2000]}}]
            }

        self._client.pages.update(page_id=page_id, properties=properties)
        logger.debug("Inbox entry %s updated to '%s'", page_id, status)

    # ── Nominations ─────────────────────────────────────────────────

    def add_nomination(
        self,
        nomination: Nomination,
        source: str = "Lien partagé",
        post_url: str = "",
        attachments: list[Attachment] | None = None,
    ) -> str:
        """Add a nomination entry to the Notion database.

        Returns the created page ID.
        """
        if not self._database_id:
            raise ValueError(
                "No database ID configured. Set NOTION_DATABASE_ID in .env "
                "or call setup_database() first."
            )

        properties = {
            "Nom": {"title": [{"text": {"content": nomination.person_name}}]},
            "Rôle": {"rich_text": [{"text": {"content": nomination.new_role}}]},
            "Entreprise": {"rich_text": [{"text": {"content": nomination.company}}]},
            "Type": {"select": {"name": TYPE_LABELS.get(nomination.nomination_type, "Autre")}},
            "Confiance": {"number": nomination.confidence},
            "Headline": {"rich_text": [{"text": {"content": nomination.person_headline}}]},
            "Extrait": {
                "rich_text": [{"text": {"content": nomination.source_text[:2000]}}]
            },
            "Date d'ajout": {
                "date": {"start": datetime.now(tz=timezone.utc).isoformat()}
            },
            "Source": {"select": {"name": source}},
        }

        if nomination.posted_at and nomination.posted_at != "unknown":
            properties["Date du post"] = {"date": {"start": nomination.posted_at}}

        if post_url:
            properties["Lien LinkedIn"] = {"url": post_url}

        if nomination.person_profile_url:
            properties["Profil LinkedIn"] = {"url": nomination.person_profile_url}

        # Add file attachments (external URLs only — Notion API limitation)
        if attachments:
            file_entries = []
            for att in attachments:
                file_entries.append({
                    "name": att.filename,
                    "type": "external",
                    "external": {"url": att.url},
                })
            if file_entries:
                properties["Documents"] = {"files": file_entries}

        response = self._client.pages.create(
            parent={"database_id": self._database_id},
            properties=properties,
            children=[
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": nomination.summary()}}]
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": nomination.source_text[:2000]}}
                        ]
                    },
                },
            ],
        )

        page_id = response["id"]
        logger.info(
            "Added nomination to Notion: %s (page %s)",
            nomination.person_name,
            page_id,
        )
        return page_id

    def add_nominations(
        self,
        nominations: list[Nomination],
        source: str = "Feed scan",
    ) -> list[str]:
        """Add multiple nominations to Notion. Returns list of page IDs."""
        page_ids = []
        for nom in nominations:
            try:
                page_id = self.add_nomination(nom, source=source)
                page_ids.append(page_id)
            except Exception:
                logger.warning(
                    "Failed to add nomination for %s to Notion",
                    nom.person_name,
                    exc_info=True,
                )
        logger.info("Added %d/%d nominations to Notion.", len(page_ids), len(nominations))
        return page_ids

    def find_existing(self, person_name: str, posted_at: str) -> bool:
        """Check if a nomination already exists in the database (dedup)."""
        if not self._database_id:
            return False

        try:
            response = self._client.databases.query(
                database_id=self._database_id,
                filter={
                    "and": [
                        {"property": "Nom", "title": {"equals": person_name}},
                        {"property": "Date du post", "date": {"equals": posted_at[:10]}},
                    ]
                },
            )
            return len(response.get("results", [])) > 0
        except Exception:
            logger.debug("Dedup check failed", exc_info=True)
            return False
