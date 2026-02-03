#!/usr/bin/env python3
"""
Diagnostic des sources RSS
Banking Newsletter Agent - Ares & Co

Vérifie la disponibilité et le contenu des flux RSS configurés.
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime

import feedparser
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def load_sources(config_path: str = "config/sources.yaml") -> dict:
    """Charge la configuration des sources"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_rss_feed(name: str, url: str, timeout: int = 15) -> dict:
    """Teste un flux RSS et retourne son statut"""
    result = {
        "name": name,
        "url": url,
        "status": "unknown",
        "articles": 0,
        "last_date": None,
        "error": None
    }

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers)

        if response.status_code == 200:
            feed = feedparser.parse(response.content)

            if feed.bozo and not feed.entries:
                result["status"] = "invalid"
                result["error"] = "Format RSS invalide"
            elif len(feed.entries) == 0:
                result["status"] = "empty"
                result["error"] = "Flux vide"
            else:
                result["status"] = "ok"
                result["articles"] = len(feed.entries)

                # Dernière date de publication
                if feed.entries and hasattr(feed.entries[0], 'published_parsed'):
                    try:
                        pub = feed.entries[0].published_parsed
                        result["last_date"] = datetime(*pub[:6])
                    except:
                        pass
        elif response.status_code == 403:
            result["status"] = "blocked"
            result["error"] = "Accès refusé (403)"
        elif response.status_code == 404:
            result["status"] = "not_found"
            result["error"] = "URL introuvable (404)"
        else:
            result["status"] = "error"
            result["error"] = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = "Timeout"
    except requests.exceptions.ConnectionError as e:
        if "Proxy" in str(e):
            result["status"] = "proxy"
            result["error"] = "Bloqué par proxy"
        else:
            result["status"] = "connection"
            result["error"] = "Erreur connexion"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:30]

    return result


def check_web_source(name: str, url: str, timeout: int = 15) -> dict:
    """Teste une source web (scraping)"""
    result = {
        "name": name,
        "url": url,
        "status": "unknown",
        "error": None
    }

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers)

        if response.status_code == 200:
            result["status"] = "ok"
        else:
            result["status"] = "error"
            result["error"] = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = "Timeout"
    except requests.exceptions.ConnectionError as e:
        if "Proxy" in str(e):
            result["status"] = "proxy"
            result["error"] = "Bloqué par proxy"
        else:
            result["status"] = "connection"
            result["error"] = "Erreur connexion"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:30]

    return result


def main():
    """Point d'entrée principal"""
    console.print(Panel(
        "[bold blue]Diagnostic des Sources RSS[/bold blue]\n"
        "Banking Newsletter Agent - Ares & Co",
        style="blue"
    ))

    # Charger la configuration
    project_dir = Path(__file__).parent.parent
    config_path = project_dir / "config" / "sources.yaml"

    if not config_path.exists():
        console.print(f"[red]Fichier de configuration introuvable: {config_path}[/red]")
        sys.exit(1)

    sources = load_sources(str(config_path))

    # Tester les flux RSS
    console.print("\n[bold]Test des flux RSS...[/bold]\n")

    rss_results = []
    for feed in sources.get("rss_feeds", []):
        console.print(f"  Testing {feed['name']}...", end=" ")
        result = check_rss_feed(feed["name"], feed["url"])
        result["category"] = feed.get("category", "")
        result["priority"] = feed.get("priority", 3)
        rss_results.append(result)

        if result["status"] == "ok":
            console.print(f"[green]OK ({result['articles']} articles)[/green]")
        elif result["status"] == "proxy":
            console.print(f"[yellow]Proxy[/yellow]")
        else:
            console.print(f"[red]{result['error']}[/red]")

    # Tester les sources web
    console.print("\n[bold]Test des sources web...[/bold]\n")

    web_results = []
    for source in sources.get("web_sources", []):
        console.print(f"  Testing {source['name']}...", end=" ")
        result = check_web_source(source["name"], source["url"])
        web_results.append(result)

        if result["status"] == "ok":
            console.print("[green]OK[/green]")
        elif result["status"] == "proxy":
            console.print("[yellow]Proxy[/yellow]")
        else:
            console.print(f"[red]{result['error']}[/red]")

    # Tableau récapitulatif
    console.print("\n")

    table = Table(title="Récapitulatif des Sources RSS")
    table.add_column("Source", style="cyan")
    table.add_column("Catégorie")
    table.add_column("Statut")
    table.add_column("Articles", justify="right")
    table.add_column("Dernière MAJ")

    status_style = {
        "ok": "[green]OK[/green]",
        "empty": "[yellow]Vide[/yellow]",
        "invalid": "[red]Invalide[/red]",
        "blocked": "[red]Bloqué[/red]",
        "not_found": "[red]404[/red]",
        "timeout": "[yellow]Timeout[/yellow]",
        "proxy": "[yellow]Proxy[/yellow]",
        "connection": "[red]Connexion[/red]",
        "error": "[red]Erreur[/red]",
        "unknown": "[dim]?[/dim]"
    }

    for r in rss_results:
        last_date = r["last_date"].strftime("%d/%m/%Y") if r["last_date"] else "-"
        table.add_row(
            r["name"],
            r["category"],
            status_style.get(r["status"], r["status"]),
            str(r["articles"]) if r["articles"] else "-",
            last_date
        )

    console.print(table)

    # Statistiques
    ok_count = sum(1 for r in rss_results if r["status"] == "ok")
    proxy_count = sum(1 for r in rss_results if r["status"] == "proxy")
    error_count = len(rss_results) - ok_count - proxy_count

    console.print(f"\n[bold]Résumé:[/bold]")
    console.print(f"  [green]OK[/green]: {ok_count}/{len(rss_results)}")
    if proxy_count:
        console.print(f"  [yellow]Proxy (non testable)[/yellow]: {proxy_count}")
    if error_count:
        console.print(f"  [red]Erreur[/red]: {error_count}")

    # Recommandations
    if proxy_count == len(rss_results):
        console.print("\n[yellow]Note: Tous les flux sont bloqués par le proxy.[/yellow]")
        console.print("[yellow]Testez sur une machine avec accès internet direct.[/yellow]")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
