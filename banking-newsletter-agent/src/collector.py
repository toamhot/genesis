"""
Module de collecte des articles
Banking Newsletter Agent - Ares & Co

Ce module gère :
- La récupération des flux RSS
- Le scraping de pages web
- La normalisation des articles collectés
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from dateutil import parser as date_parser
import yaml
import hashlib
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


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

    def collect_rss(self, days_back: int = 30) -> List[Article]:
        """Collecte les articles depuis les flux RSS configurés"""
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        console.print("\n[bold blue]📡 Collecte des flux RSS...[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for feed_config in self.config.get('rss_feeds', []):
                task = progress.add_task(f"[cyan]{feed_config['name']}...", total=None)

                try:
                    feed = feedparser.parse(feed_config['url'])

                    for entry in feed.entries:
                        # Parser la date de publication
                        pub_date = self._parse_date(
                            entry.get('published') or entry.get('updated')
                        )

                        # Filtrer les articles trop anciens
                        if pub_date and pub_date < cutoff_date:
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

                        article = Article(
                            id=self._generate_id(entry.link),
                            title=entry.title,
                            url=entry.link,
                            source=feed_config['name'],
                            category=feed_config['category'],
                            published_date=pub_date,
                            content=content[:2000],  # Limiter la taille
                            summary=entry.get('summary', '')[:500],
                            priority=feed_config.get('priority', 3)
                        )
                        articles.append(article)

                    progress.update(task, description=f"[green]✓ {feed_config['name']} ({len(feed.entries)} articles)")

                except Exception as e:
                    progress.update(task, description=f"[red]✗ {feed_config['name']}: {str(e)[:50]}")

        console.print(f"\n[green]✓ {len(articles)} articles collectés depuis les flux RSS[/green]")
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
                    response = requests.get(source['url'], headers=headers, timeout=10)
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
