"""Main agent that orchestrates LinkedIn nomination detection."""

import logging
import time
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import (
    CHECK_PERIOD_DAYS,
    INBOX_POLL_INTERVAL_MINUTES,
    NOTION_API_KEY,
    OUTPUT_FORMAT,
)
from src.document_extractor import Attachment, DocumentExtractor
from src.linkedin_client import LinkedInClient, LinkedInPost
from src.nomination_detector import Nomination, NominationDetector
from src.notion_client import InboxEntry, NotionClient
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
        self._use_llm = use_llm
        self._client = LinkedInClient()
        self._detector = NominationDetector(use_llm=use_llm)
        self._reporter = Reporter(output_format=output_format)
        self._push_to_notion = push_to_notion and bool(NOTION_API_KEY)

    # ── Mode 1: Scan feed/contacts ──────────────────────────────────

    def run(self) -> list[Nomination]:
        """Execute the full nomination detection pipeline."""
        console.print(
            f"\n[bold blue]LinkedIn Nomination Agent[/bold blue] — "
            f"Scan des {self._days} derniers jours (mode: {self._scan_mode.value})\n"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Connexion à LinkedIn...", total=None)
            self._client.connect()
            progress.update(task, description="[green]Connecté à LinkedIn")

            progress.update(task, description="Collecte des publications...")
            posts = self._collect_posts(progress)
            progress.update(
                task,
                description=f"[green]{len(posts)} publications collectées",
            )

            progress.update(task, description="Analyse des nominations...")
            nominations = self._detector.detect(posts)
            progress.update(
                task,
                description=f"[green]{len(nominations)} nominations détectées",
            )

            if self._push_to_notion and nominations:
                progress.update(task, description="Envoi vers Notion...")
                self._send_to_notion(nominations, source="Feed scan")
                progress.update(task, description="[green]Envoyé vers Notion")

        self._reporter.report(nominations)
        return nominations

    # ── Mode 2: Ingest shared URLs ──────────────────────────────────

    def ingest_urls(
        self,
        urls: list[str],
        use_llm: bool = True,
        extract_documents: bool = True,
    ) -> list[Nomination]:
        """Ingest LinkedIn post URLs shared manually via 'Partager'."""
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
                    task, description=f"Scraping du post {i}/{len(urls)}..."
                )

                post = scraper.scrape(url)
                if not post:
                    console.print(f"  [yellow]Impossible de scraper: {url}[/yellow]")
                    continue

                post.post_url = url
                nominations = self._detector.detect([post])

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

                if nominations:
                    all_nominations.extend(nominations)
                    if self._push_to_notion:
                        for nom in nominations:
                            self._add_to_notion(
                                nom,
                                source="Lien partagé",
                                post_url=url,
                                attachments=attachments,
                            )
                else:
                    console.print(
                        f"  [dim]Pas de nomination détectée pour: "
                        f"{post.author_name}[/dim]"
                    )

            progress.update(
                task,
                description=f"[green]{len(all_nominations)} nomination(s) sur {len(urls)} lien(s)",
            )

        self._reporter.report(all_nominations)
        return all_nominations

    # ── Mode 3: Process Notion Inbox ────────────────────────────────

    def process_inbox(self, extract_documents: bool = True) -> list[Nomination]:
        """Process all pending entries from the Notion Inbox.

        Workflow:
        1. Query the Inbox DB for entries with status "Nouveau"
        2. For each entry: scrape → detect → extract docs → push to Genesis DB
        3. Update the Inbox entry status accordingly
        """
        console.print(
            "\n[bold blue]LinkedIn Nomination Agent[/bold blue] — "
            "Traitement de l'Inbox Notion\n"
        )

        notion = NotionClient()
        entries = notion.get_pending_inbox_entries()

        if not entries:
            console.print("[dim]Aucun nouveau lien dans l'Inbox.[/dim]\n")
            return []

        console.print(f"[cyan]{len(entries)} lien(s) à traiter[/cyan]\n")

        scraper = PostScraper()
        doc_extractor = DocumentExtractor() if extract_documents else None
        all_nominations: list[Nomination] = []

        for i, entry in enumerate(entries, 1):
            console.print(
                f"[bold]({i}/{len(entries)})[/bold] {entry.url[:80]}..."
                if len(entry.url) > 80
                else f"[bold]({i}/{len(entries)})[/bold] {entry.url}"
            )

            # Mark as "En cours"
            notion.update_inbox_status(entry.page_id, "En cours")

            try:
                # Scrape the post
                post = scraper.scrape(entry.url)
                if not post:
                    notion.update_inbox_status(
                        entry.page_id, "Erreur", "Impossible de scraper le post"
                    )
                    console.print("  [yellow]Scraping échoué[/yellow]")
                    continue

                post.post_url = entry.url

                # Detect nomination
                nominations = self._detector.detect([post])

                # Extract documents
                attachments: list[Attachment] = []
                if doc_extractor:
                    attachments = doc_extractor.extract_from_url(entry.url)
                    if attachments:
                        console.print(
                            f"  [green]{len(attachments)} document(s) téléchargé(s)[/green]"
                        )

                if nominations:
                    all_nominations.extend(nominations)
                    nom = nominations[0]

                    # Push to Genesis DB
                    notion.add_nomination(
                        nom,
                        source="Inbox",
                        post_url=entry.url,
                        attachments=attachments,
                    )

                    # Update inbox status
                    notion.update_inbox_status(
                        entry.page_id,
                        "Nomination",
                        nom.summary(),
                    )
                    console.print(f"  [green]Nomination: {nom.summary()}[/green]")
                else:
                    notion.update_inbox_status(
                        entry.page_id,
                        "Pas une nomination",
                        f"Post de {post.author_name} — aucune nomination détectée",
                    )
                    console.print(
                        f"  [dim]Pas une nomination ({post.author_name})[/dim]"
                    )

            except Exception as exc:
                logger.warning("Error processing inbox entry", exc_info=True)
                notion.update_inbox_status(
                    entry.page_id, "Erreur", str(exc)[:200]
                )
                console.print(f"  [red]Erreur: {exc}[/red]")

        console.print(
            f"\n[bold green]{len(all_nominations)} nomination(s) détectée(s) "
            f"sur {len(entries)} lien(s)[/bold green]\n"
        )

        self._reporter.report(all_nominations)
        return all_nominations

    def run_daemon(
        self,
        interval_minutes: int = INBOX_POLL_INTERVAL_MINUTES,
        extract_documents: bool = True,
    ) -> None:
        """Run the agent as a daemon, polling the Inbox periodically.

        This runs indefinitely until interrupted (Ctrl+C).
        """
        console.print(
            f"\n[bold blue]LinkedIn Nomination Agent — Mode Daemon[/bold blue]\n"
            f"Surveillance de l'Inbox Notion toutes les {interval_minutes} minutes.\n"
            f"Appuyez sur Ctrl+C pour arrêter.\n"
        )

        while True:
            try:
                self.process_inbox(extract_documents=extract_documents)
            except KeyboardInterrupt:
                console.print("\n[yellow]Arrêt du daemon.[/yellow]")
                break
            except Exception:
                logger.warning("Daemon cycle error", exc_info=True)
                console.print("[yellow]Erreur lors du cycle, nouvelle tentative...[/yellow]")

            console.print(
                f"[dim]Prochaine vérification dans {interval_minutes} min...[/dim]\n"
            )
            try:
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                console.print("\n[yellow]Arrêt du daemon.[/yellow]")
                break

    # ── Internals ───────────────────────────────────────────────────

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
            notion = NotionClient()

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
