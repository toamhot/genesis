"""Main agent that orchestrates LinkedIn nomination detection."""

import logging
from enum import Enum

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import CHECK_PERIOD_DAYS, OUTPUT_FORMAT
from src.linkedin_client import LinkedInClient, LinkedInPost
from src.nomination_detector import Nomination, NominationDetector
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
    ):
        self._scan_mode = scan_mode
        self._days = days
        self._client = LinkedInClient()
        self._detector = NominationDetector(use_llm=use_llm)
        self._reporter = Reporter(output_format=output_format)

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

        # Step 4: Generate report
        self._reporter.report(nominations)

        return nominations

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
