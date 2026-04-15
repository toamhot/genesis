"""
Module de collecte des articles via NewsAPI.org
Banking Newsletter Agent - Ares & Co

Ce module interroge l'API NewsAPI pour récupérer des articles
provenant de sources payantes (FT, WSJ, Les Echos, Reuters, Agefi).
"""

import os
import hashlib
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from rich.console import Console

from collector import Article

console = Console()

# Domaines de sources payantes ciblées
PAYWALLED_DOMAINS = [
    "ft.com",
    "lesechos.fr",
    "wsj.com",
    "reuters.com",
    "agefi.fr",
]

# Mots-clés bancaires / finance
KEYWORDS = (
    "banking OR banque OR finance OR BCE OR ECB OR BNP "
    'OR "Societe Generale"'
)

NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"


def _generate_id(url: str) -> str:
    """Génère un ID unique pour un article basé sur son URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def collect_newsapi(days_back: int = 30, page_size: int = 100) -> List[Article]:
    """
    Collecte des articles bancaires / finance depuis NewsAPI.org.

    Args:
        days_back: Nombre de jours en arrière pour la recherche.
        page_size: Nombre d'articles par page (max 100 pour NewsAPI).

    Returns:
        Liste d'objets Article.
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        console.print("[yellow]⚠ NEWSAPI_KEY non définie — collecte NewsAPI ignorée.[/yellow]")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    domains = ",".join(PAYWALLED_DOMAINS)

    articles: List[Article] = []
    page = 1

    console.print("\n[bold blue]📡 Collecte NewsAPI (sources payantes)...[/bold blue]")
    console.print(f"[dim]Domaines : {domains}[/dim]")
    console.print(f"[dim]Période  : derniers {days_back} jours (depuis {from_date})[/dim]\n")

    while True:
        params = {
            "q": KEYWORDS,
            "domains": domains,
            "from": from_date,
            "language": "fr,en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "page": page,
            "apiKey": api_key,
        }

        try:
            response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            console.print(f"[red]✗ Erreur NewsAPI (page {page}): {exc}[/red]")
            break

        if data.get("status") != "ok":
            error_msg = data.get("message", "Erreur inconnue")
            console.print(f"[red]✗ NewsAPI a répondu avec une erreur : {error_msg}[/red]")
            break

        raw_articles = data.get("articles", [])
        if not raw_articles:
            break

        for item in raw_articles:
            url = item.get("url", "")
            if not url:
                continue

            # Parser la date de publication
            pub_date: Optional[datetime] = None
            pub_str = item.get("publishedAt")
            if pub_str:
                try:
                    pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    pub_date = pub_date.replace(tzinfo=None)
                except (ValueError, TypeError):
                    pass

            # Contenu : NewsAPI tronque souvent à ~200 chars, on prend ce qui est dispo
            content = item.get("content") or item.get("description") or ""
            summary = item.get("description") or ""
            title = item.get("title") or ""
            source_name = (item.get("source") or {}).get("name", "NewsAPI")

            article = Article(
                id=_generate_id(url),
                title=title,
                url=url,
                source=source_name,
                category="finance",
                published_date=pub_date,
                content=content[:2000],
                summary=summary[:500] if summary else title[:500],
                priority=2,
            )
            articles.append(article)

        # Pagination : NewsAPI free tier limite à 100 résultats total
        total_results = data.get("totalResults", 0)
        fetched_so_far = page * page_size
        if fetched_so_far >= total_results:
            break
        page += 1

    console.print(f"[green]✓ {len(articles)} articles collectés depuis NewsAPI[/green]")
    return articles
