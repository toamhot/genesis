"""
Module de collecte des articles
Banking Newsletter Agent - Ares & Co

Ce module gère :
- La récupération des flux RSS
- Le scraping de pages web
- La normalisation des articles collectés
"""

import time
import logging
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import yaml
import hashlib
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

console = Console()
logger = logging.getLogger(__name__)

# Exceptions réseau transitoires
NETWORK_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    ConnectionError,
    TimeoutError,
)


def _fetch_feed_with_retry(url: str, max_retries: int = 5) -> feedparser.FeedParserDict:
    """Parse un flux RSS avec retry sur erreurs réseau"""
    for attempt in range(max_retries):
        feed = feedparser.parse(url)
        # feedparser ne lève pas d'exception en cas d'erreur réseau,
        # il retourne un bozo avec bozo_exception
        if feed.bozo and hasattr(feed, 'bozo_exception'):
            exc = feed.bozo_exception
            if isinstance(exc, (IOError, OSError, TimeoutError)):
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    console.print(f"[yellow]  ⚠ Erreur réseau RSS ({attempt+1}/{max_retries}), retry dans {wait}s...[/yellow]")
                    time.sleep(wait)
                    continue
        return feed
    return feed  # Retourner le dernier résultat même en erreur


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(NETWORK_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def _fetch_web_with_retry(url: str, headers: dict, timeout: int = 20) -> requests.Response:
    """Requête HTTP avec retry sur erreurs réseau"""
    return requests.get(url, headers=headers, timeout=timeout)


class DateValidator:
    """Validateur de dates pour les articles"""

    @staticmethod
    def normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Normalise une datetime en supprimant les informations de timezone.
        Permet de comparer des dates timezone-aware et timezone-naive.
        """
        if dt is None:
            return None
        if dt.tzinfo is not None:
            # Convertir en UTC puis supprimer la timezone
            return dt.replace(tzinfo=None)
        return dt

    def __init__(self, target_month: Optional[datetime] = None, days_back: int = 30):
        """
        Initialise le validateur de dates.

        Args:
            target_month: Mois cible pour la newsletter (par défaut: mois précédent)
            days_back: Nombre de jours en arrière pour la collecte
        """
        if target_month is None:
            # Par défaut, le mois précédent
            target_month = datetime.now() - relativedelta(months=1)

        self.target_month = target_month
        self.target_year = target_month.year
        self.target_month_num = target_month.month

        # Période de collecte : du 1er du mois cible jusqu'à aujourd'hui
        self.start_date = datetime(self.target_year, self.target_month_num, 1)
        self.end_date = datetime.now()

        # Alternative : période glissante
        self.cutoff_date = datetime.now() - timedelta(days=days_back)

        self.stats = {
            "total": 0,
            "valid": 0,
            "no_date": 0,
            "too_old": 0,
            "future": 0
        }

    def validate(self, pub_date: Optional[datetime], strict: bool = False) -> Tuple[bool, str]:
        """
        Valide si une date d'article est dans la période acceptable.

        Args:
            pub_date: Date de publication de l'article
            strict: Si True, rejette les articles sans date

        Returns:
            Tuple (is_valid, reason)
        """
        self.stats["total"] += 1

        # Pas de date
        if pub_date is None:
            self.stats["no_date"] += 1
            if strict:
                return False, "no_date"
            return True, "no_date_accepted"  # Accepter avec avertissement

        # Normaliser la date pour comparaison (supprimer timezone)
        pub_date_normalized = self.normalize_datetime(pub_date)
        now = datetime.now()

        # Date dans le futur (erreur de parsing probable)
        if pub_date_normalized > now + timedelta(days=1):
            self.stats["future"] += 1
            return False, "future_date"

        # Date trop ancienne
        if pub_date_normalized < self.cutoff_date:
            self.stats["too_old"] += 1
            return False, f"too_old ({pub_date.strftime('%d/%m/%Y')})"

        self.stats["valid"] += 1
        return True, "valid"

    def is_in_target_month(self, pub_date: Optional[datetime]) -> bool:
        """Vérifie si l'article est dans le mois cible"""
        if pub_date is None:
            return False
        pub_date_normalized = self.normalize_datetime(pub_date)
        return (pub_date_normalized.year == self.target_year and
                pub_date_normalized.month == self.target_month_num)

    def get_stats_summary(self) -> str:
        """Retourne un résumé des statistiques de validation"""
        return (
            f"Total: {self.stats['total']} | "
            f"Valides: {self.stats['valid']} | "
            f"Sans date: {self.stats['no_date']} | "
            f"Trop anciens: {self.stats['too_old']} | "
            f"Futurs: {self.stats['future']}"
        )


@dataclass
class Article:
    """Structure d'un article collecté"""
    id: str
    title: str
    url: str
    source: str
    category: str
    published_date: Optional[datetime]
    content: str
    summary: str
    priority: int

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.published_date:
            data['published_date'] = self.published_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Article':
        if data.get('published_date'):
            data['published_date'] = datetime.fromisoformat(data['published_date'])
        return cls(**data)


class Collector:
    """Collecteur d'articles depuis diverses sources"""

    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config = self._load_config(config_path)
        self.articles: List[Article] = []

    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration des sources"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _generate_id(self, url: str) -> str:
        """Génère un ID unique pour un article basé sur son URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse une date depuis différents formats"""
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str)
        except (ValueError, TypeError):
            return None

    def collect_rss(self, days_back: int = 30, strict_date: bool = False) -> List[Article]:
        """
        Collecte les articles depuis les flux RSS configurés.

        Args:
            days_back: Nombre de jours en arrière pour la collecte
            strict_date: Si True, rejette les articles sans date
        """
        articles = []
        rejected_count = 0

        # Initialiser le validateur de dates
        self.date_validator = DateValidator(days_back=days_back)

        console.print("\n[bold blue]📡 Collecte des flux RSS...[/bold blue]\n")
        console.print(f"[dim]Période: derniers {days_back} jours (depuis {self.date_validator.cutoff_date.strftime('%d/%m/%Y')})[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for feed_config in self.config.get('rss_feeds', []):
                task = progress.add_task(f"[cyan]{feed_config['name']}...", total=None)
                feed_articles = 0
                feed_rejected = 0

                try:
                    feed = _fetch_feed_with_retry(feed_config['url'])

                    for entry in feed.entries:
                        # Parser la date de publication
                        pub_date = self._parse_date(
                            entry.get('published') or entry.get('updated')
                        )

                        # Valider la date
                        is_valid, reason = self.date_validator.validate(pub_date, strict=strict_date)
                        if not is_valid:
                            feed_rejected += 1
                            rejected_count += 1
                            continue

                        # Extraire le contenu
                        content = ""
                        if hasattr(entry, 'content'):
                            content = entry.content[0].value if entry.content else ""
                        elif hasattr(entry, 'summary'):
                            content = entry.summary

                        # Nettoyer le HTML du contenu
                        if content:
                            soup = BeautifulSoup(content, 'html.parser')
                            content = soup.get_text(separator=' ', strip=True)

                        # Extraire et nettoyer le résumé
                        summary = entry.get('summary', '') or entry.get('description', '')
                        if summary:
                            soup = BeautifulSoup(summary, 'html.parser')
                            summary = soup.get_text(separator=' ', strip=True)

                        # Fallback: utiliser le titre si pas de contenu ni résumé
                        if not content and not summary:
                            summary = entry.title

                        article = Article(
                            id=self._generate_id(entry.link),
                            title=entry.title,
                            url=entry.link,
                            source=feed_config['name'],
                            category=feed_config['category'],
                            published_date=pub_date,
                            content=content[:2000] if content else summary[:2000],
                            summary=summary[:500] if summary else entry.title[:500],
                            priority=feed_config.get('priority', 3)
                        )
                        articles.append(article)
                        feed_articles += 1

                    # Afficher le résultat avec les rejets éventuels
                    if feed_rejected > 0:
                        progress.update(task, description=f"[green]✓ {feed_config['name']} ({feed_articles} articles, {feed_rejected} hors période)[/green]")
                    else:
                        progress.update(task, description=f"[green]✓ {feed_config['name']} ({feed_articles} articles)[/green]")

                except Exception as e:
                    progress.update(task, description=f"[red]✗ {feed_config['name']}: {str(e)[:50]}")

        console.print(f"\n[green]✓ {len(articles)} articles collectés depuis les flux RSS[/green]")
        if rejected_count > 0:
            console.print(f"[yellow]⚠ {rejected_count} articles rejetés (hors période ou date invalide)[/yellow]")
        console.print(f"[dim]{self.date_validator.get_stats_summary()}[/dim]")
        return articles

    def collect_web(self, days_back: int = 30) -> List[Article]:
        """Collecte les articles depuis les pages web (scraping)"""
        articles = []

        console.print("\n[bold blue]🌐 Scraping des pages web...[/bold blue]\n")

        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; AresCoNewsletterBot/1.0)'
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for source in self.config.get('web_sources', []):
                task = progress.add_task(f"[cyan]{source['name']}...", total=None)

                try:
                    response = _fetch_web_with_retry(source['url'], headers=headers, timeout=10)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Chercher les éléments d'actualité (sélecteur configurable)
                    selector = source.get('selector', 'article')
                    items = soup.select(selector)[:20]  # Limiter à 20 items

                    for item in items:
                        # Extraire titre et lien
                        title_elem = item.select_one('h2, h3, h4, .title, a')
                        link_elem = item.select_one('a[href]')

                        if not title_elem or not link_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')

                        # Construire l'URL complète si relative
                        if url and not url.startswith('http'):
                            from urllib.parse import urljoin
                            url = urljoin(source['url'], url)

                        if not url or not title:
                            continue

                        # Extraire le résumé si disponible
                        summary_elem = item.select_one('p, .summary, .excerpt')
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""

                        article = Article(
                            id=self._generate_id(url),
                            title=title,
                            url=url,
                            source=source['name'],
                            category=source['category'],
                            published_date=None,  # Difficile à extraire sans structure standard
                            content=summary,
                            summary=summary[:500],
                            priority=source.get('priority', 3)
                        )
                        articles.append(article)

                    progress.update(task, description=f"[green]✓ {source['name']} ({len(items)} articles)")

                except Exception as e:
                    progress.update(task, description=f"[red]✗ {source['name']}: {str(e)[:50]}")

        console.print(f"\n[green]✓ {len(articles)} articles collectés par scraping[/green]")
        return articles

    def collect_all(self, days_back: int = 30) -> List[Article]:
        """Collecte tous les articles depuis toutes les sources"""
        console.print("\n[bold magenta]🚀 Démarrage de la collecte...[/bold magenta]")
        console.print(f"[dim]Période : {days_back} derniers jours[/dim]\n")

        # Collecter depuis toutes les sources
        rss_articles = self.collect_rss(days_back)
        web_articles = self.collect_web(days_back)

        # Fusionner et dédupliquer
        all_articles = rss_articles + web_articles

        # Dédupliquer par ID (basé sur l'URL)
        seen_ids = set()
        unique_articles = []
        for article in all_articles:
            if article.id not in seen_ids:
                seen_ids.add(article.id)
                unique_articles.append(article)

        self.articles = unique_articles

        console.print(f"\n[bold green]✅ Collecte terminée : {len(unique_articles)} articles uniques[/bold green]")

        return unique_articles


if __name__ == "__main__":
    # Test du collecteur
    collector = Collector()
    articles = collector.collect_all(days_back=7)

    console.print("\n[bold]Aperçu des articles collectés :[/bold]")
    for article in articles[:5]:
        console.print(f"  • [cyan]{article.source}[/cyan]: {article.title[:60]}...")
