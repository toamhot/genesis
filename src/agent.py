"""Main agent that orchestrates LinkedIn nomination detection."""

import logging
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import CHECK_PERIOD_DAYS, NOTION_API_KEY, OUTPUT_FORMAT
from src.document_extractor import Attachment, DocumentExtractor
from src.linkedin_client import LinkedInClient, LinkedInPost
from src.nomination_detector import Nomination, NominationDetector
from src.post_scraper import PostScraper
from src.reporter import Reporter

logger = logging.getLogger(__name__)
console = Console()


class ScanMode(str, Enum):
    """How the agent collects posts to analyze."""

    FEED = "feed"  # Scan the LinkedIn feed (faster, less complete)
    CONTACTS = "contacts"  # Scan each contact's posts (thorough, slower)
    BOTH = "both"  # Combine both methods


class LinkedInNominationAgent:
    """Agent that scans LinkedIn contacts for nominations and role changes."""

    def __init__(
        self,
        scan_mode: ScanMode = ScanMode.FEED,
        use_llm: bool = True,
        output_format: str = OUTPUT_FORMAT,
        days: int = CHECK_PERIOD_DAYS,
        push_to_notion: bool = False,
    ):
        self._scan_mode = scan_mode
        self._days = days
        self._client = LinkedInClient()
        self._detector = NominationDetector(use_llm=use_llm)
        self._reporter = Reporter(output_format=output_format)
        self._push_to_notion = push_to_notion and bool(NOTION_API_KEY)

    def run(self) -> list[Nomination]:
        """Execute the full nomination detection pipeline.

        Returns the list of detected nominations.
        """
        console.print(
            f"\n[bold blue]LinkedIn Nomination Agent[/bold blue] — "
            f"Scan des {self._days} derniers jours (mode: {self._scan_mode.value})\n"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Connect to LinkedIn
            task = progress.add_task("Connexion à LinkedIn...", total=None)
            self._client.connect()
            progress.update(task, description="[green]Connecté à LinkedIn")

            # Step 2: Collect posts
            progress.update(task, description="Collecte des publications...")
            posts = self._collect_posts(progress)
            progress.update(
                task,
                description=f"[green]{len(posts)} publications collectées",
            )

            # Step 3: Detect nominations
            progress.update(task, description="Analyse des nominations...")
            nominations = self._detector.detect(posts)
            progress.update(
                task,
                description=f"[green]{len(nominations)} nominations détectées",
            )

            # Step 4: Push to Notion if enabled
            if self._push_to_notion and nominations:
                progress.update(task, description="Envoi vers Notion...")
                self._send_to_notion(nominations, source="Feed scan")
                progress.update(task, description="[green]Envoyé vers Notion")

        # Step 5: Generate report
        self._reporter.report(nominations)

        return nominations

    def ingest_urls(
        self,
        urls: list[str],
        use_llm: bool = True,
        extract_documents: bool = True,
    ) -> list[Nomination]:
        """Ingest LinkedIn post URLs shared manually via 'Share via'.

        This is the primary method for the manual curation workflow:
        1. User copies a LinkedIn post link
        2. Runs: python main.py --url <link>
        3. Agent scrapes the post, detects nomination, extracts docs, pushes to Notion

        Returns the list of detected nominations.
        """
        console.print(
            f"\n[bold blue]LinkedIn Nomination Agent[/bold blue] — "
            f"Ingestion de {len(urls)} lien(s)\n"
        )

        scraper = PostScraper()
        doc_extractor = DocumentExtractor() if extract_documents else None
        all_nominations: list[Nomination] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Traitement des liens...", total=None)

            for i, url in enumerate(urls, 1):
                progress.update(
                    task,
                    description=f"Scraping du post {i}/{len(urls)}...",
                )

                # 1. Scrape the post
                post = scraper.scrape(url)
                if not post:
                    console.print(f"  [yellow]Impossible de scraper: {url}[/yellow]")
                    continue

                post.post_url = url

                # 2. Detect nomination
                nominations = self._detector.detect([post])

                # 3. Extract documents
                attachments: list[Attachment] = []
                if doc_extractor:
                    progress.update(
                        task,
                        description=f"Extraction des documents ({i}/{len(urls)})...",
                    )
                    attachments = doc_extractor.extract_from_url(url)
                    if attachments:
                        console.print(
                            f"  [green]{len(attachments)} document(s) téléchargé(s)[/green]"
                        )

                # 4. Push to Notion
                if nominations:
                    all_nominations.extend(nominations)
                    if self._push_to_notion:
                        progress.update(
                            task,
                            description=f"Envoi vers Notion ({i}/{len(urls)})...",
                        )
                        for nom in nominations:
                            self._add_to_notion(
                                nom,
                                source="Lien partagé",
                                post_url=url,
                                attachments=attachments,
                            )
                else:
                    # Even if no nomination detected, save to Notion as reference
                    console.print(
                        f"  [dim]Pas de nomination détectée pour: "
                        f"{post.author_name}[/dim]"
                    )

            progress.update(
                task,
                description=f"[green]{len(all_nominations)} nomination(s) détectée(s) "
                f"sur {len(urls)} lien(s)",
            )

        # Generate report
        self._reporter.report(all_nominations)

        return all_nominations

    def _collect_posts(self, progress) -> list[LinkedInPost]:
        """Collect posts based on the configured scan mode."""
        posts: list[LinkedInPost] = []
        seen_texts: set[str] = set()

        if self._scan_mode in (ScanMode.FEED, ScanMode.BOTH):
            feed_posts = self._client.get_feed_posts(days=self._days)
            for post in feed_posts:
                key = post.text[:100]
                if key not in seen_texts:
                    seen_texts.add(key)
                    posts.append(post)

        if self._scan_mode in (ScanMode.CONTACTS, ScanMode.BOTH):
            contacts = self._client.get_contacts()
            for i, contact in enumerate(contacts):
                progress.update(
                    progress.task_ids[0],
                    description=f"Scan du contact {i + 1}/{len(contacts)}: {contact.full_name}",
                )
                contact_posts = self._client.get_contact_posts(
                    contact, days=self._days
                )
                for post in contact_posts:
                    key = post.text[:100]
                    if key not in seen_texts:
                        seen_texts.add(key)
                        posts.append(post)

        return posts

    def _send_to_notion(
        self, nominations: list[Nomination], source: str = "Feed scan"
    ) -> None:
        """Push nominations to Notion database."""
        try:
            from src.notion_client import NotionClient

            notion = NotionClient()
            notion.add_nominations(nominations, source=source)
        except Exception:
            logger.warning("Failed to push to Notion", exc_info=True)
            console.print("[yellow]Erreur lors de l'envoi vers Notion[/yellow]")

    def _add_to_notion(
        self,
        nomination: Nomination,
        source: str = "Lien partagé",
        post_url: str = "",
        attachments: list[Attachment] | None = None,
    ) -> None:
        """Add a single nomination to Notion with its attachments."""
        try:
            from src.notion_client import NotionClient

            notion = NotionClient()

            # Dedup: skip if already exists
            if notion.find_existing(nomination.person_name, nomination.posted_at):
                console.print(
                    f"  [dim]Déjà dans Notion: {nomination.person_name}[/dim]"
                )
                return

            notion.add_nomination(
                nomination,
                source=source,
                post_url=post_url,
                attachments=attachments or [],
            )
        except Exception:
            logger.warning("Failed to add to Notion", exc_info=True)
            console.print("[yellow]Erreur lors de l'ajout à Notion[/yellow]")
