"""
Module d'enrichissement des articles sélectionnés — V3
Banking Newsletter Agent - Ares & Co

Ce module intervient APRÈS la curation (donc sur ~12-20 articles, pas 500).
Pour chaque article retenu :
1. Tente de récupérer le contenu complet via l'URL directe (articles en accès libre)
2. Si paywall ou échec, cherche des extraits supplémentaires via recherche web
3. Passe le contenu enrichi à Claude pour un résumé amélioré

Objectif : transformer les résumés RSS (2-3 phrases pauvres) en résumés riches
conformes au CDC (4-6 lignes, chiffres, implications stratégiques).
"""

import os
import re
import time
import requests
from typing import List, Optional, Dict
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from analyzer import AnalyzedArticle
from curator import CuratedSelection
from persona import get_article_summary_guidelines, get_bloc_prompt, SENIOR_PARTNER_PERSONA

console = Console()

# User-Agent réaliste pour éviter les blocages basiques
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Domaines connus pour être derrière un paywall strict
PAYWALL_DOMAINS = {
    "lesechos.fr", "lagefi.fr", "ft.com", "wsj.com",
    "bloomberg.com", "reuters.com", "lemonde.fr",
    "challenges.fr", "lefigaro.fr", "latribune.fr",
}

# Sélecteurs CSS courants pour le contenu article
CONTENT_SELECTORS = [
    "article",
    '[itemprop="articleBody"]',
    ".article-body",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".story-body",
    "#article-body",
    ".content-body",
    "main .content",
]


class Enricher:
    """Enrichisseur d'articles post-curation"""

    # Limites
    MAX_CONTENT_LENGTH = 5000  # Caractères max à envoyer à Claude
    MIN_USEFUL_CONTENT = 200   # En dessous, le contenu n'est pas exploitable
    REQUEST_TIMEOUT = 10       # Secondes
    DELAY_BETWEEN_REQUESTS = 1  # Politeness delay (secondes)

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
        })
        # Stats
        self.stats = {
            "total": 0,
            "enriched_direct": 0,
            "enriched_search": 0,
            "already_rich": 0,
            "failed": 0,
            "summaries_improved": 0,
        }

    def _is_paywall_domain(self, url: str) -> bool:
        """Vérifie si l'URL est sur un domaine paywall connu."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            return any(pw in domain for pw in PAYWALL_DOMAINS)
        except Exception:
            return False

    def _is_summary_already_rich(self, article: AnalyzedArticle) -> bool:
        """
        Vérifie si le résumé actuel est déjà de bonne qualité.
        Un résumé riche contient des chiffres ET dépasse 150 caractères.
        """
        summary = article.ai_summary
        has_numbers = bool(re.search(r'\d+[%€$MG]|\d+\s*(?:milliards?|millions?|Md|M€|Mds)', summary))
        is_long_enough = len(summary) > 200
        has_implication = any(w in summary.lower() for w in [
            "pour les banques", "implication", "conséquence", "impact",
            "ce qui signifie", "cela implique", "en conséquence",
            "pour les établissements", "pour un dirigeant",
        ])
        return is_long_enough and has_numbers and has_implication

    def _fetch_article_content(self, url: str) -> Optional[str]:
        """
        Tente de récupérer le contenu complet d'un article via son URL.
        Retourne le texte nettoyé ou None si échec/paywall.
        """
        if not url or url == "":
            return None

        try:
            response = self.session.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()

            # Vérifier le Content-Type
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Supprimer les éléments non-contenu
            for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                                       "aside", "form", "iframe", "noscript"]):
                tag.decompose()

            # Essayer les sélecteurs de contenu courants
            content = None
            for selector in CONTENT_SELECTORS:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator="\n", strip=True)
                    if len(text) > self.MIN_USEFUL_CONTENT:
                        content = text
                        break

            # Fallback : prendre tous les <p> du body
            if not content:
                paragraphs = soup.find_all("p")
                text = "\n".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30)
                if len(text) > self.MIN_USEFUL_CONTENT:
                    content = text

            if content:
                # Détecter les paywalls (contenu tronqué)
                paywall_indicators = [
                    "abonnez-vous", "subscribe", "créer un compte",
                    "contenu réservé aux abonnés", "pour lire la suite",
                    "article réservé", "accès limité",
                ]
                content_lower = content.lower()
                if any(ind in content_lower for ind in paywall_indicators) and len(content) < 800:
                    return None  # Probablement tronqué par un paywall

                # Tronquer si trop long
                return content[:self.MAX_CONTENT_LENGTH]

            return None

        except requests.exceptions.RequestException:
            return None
        except Exception:
            return None

    def _search_web_extracts(self, title: str, source: str) -> Optional[str]:
        """
        Cherche des extraits supplémentaires via une recherche web.
        Utilise Google Search (gratuit, sans API) pour trouver des résumés alternatifs.
        """
        try:
            # Construire la requête de recherche
            query = f"{title} {source} banque site:lesechos.fr OR site:agefi.fr OR site:latribune.fr"
            search_url = "https://www.google.com/search"
            params = {"q": query, "hl": "fr", "num": 5}

            response = self.session.get(
                search_url,
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # Extraire les snippets Google
            snippets = []
            for div in soup.find_all("div", class_=["BNeawe", "s3v9rd"]):
                text = div.get_text(strip=True)
                if len(text) > 50 and title.split()[0].lower() in text.lower():
                    snippets.append(text)

            # Aussi chercher dans les balises meta description des résultats
            for span in soup.find_all("span"):
                text = span.get_text(strip=True)
                if len(text) > 80 and any(w in text.lower() for w in title.lower().split()[:3]):
                    snippets.append(text)

            if snippets:
                combined = "\n".join(snippets[:3])
                return combined[:2000]

            return None

        except Exception:
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5)
    )
    def _improve_summary(
        self,
        article: AnalyzedArticle,
        enriched_content: str,
        bloc_id: str
    ) -> Optional[str]:
        """
        Utilise Claude pour améliorer le résumé avec le contenu enrichi.
        Le prompt est adapté au bloc (profondeur différente).
        """
        if not self.client:
            return None

        title = article.title_fr or article.article.title
        current_summary = article.ai_summary
        bloc_prompt = get_bloc_prompt(bloc_id)

        prompt = f"""Tu dois AMÉLIORER le résumé suivant d'un article de newsletter bancaire, en t'appuyant
sur du contenu enrichi récupéré depuis l'article source.

TITRE : {title}
SOURCE : {article.article.source}

RÉSUMÉ ACTUEL (à améliorer) :
{current_summary}

CONTENU ENRICHI (extrait de l'article source) :
{enriched_content[:3000]}

CONSIGNES DE RÉÉCRITURE :
{bloc_prompt}

RÈGLES :
- Garder la même structure que le résumé actuel, mais l'enrichir
- AJOUTER des chiffres concrets si le contenu enrichi en contient (montants, %, dates)
- AJOUTER l'implication stratégique pour les banques françaises en dernière phrase
- NE PAS dépasser 6 lignes / 120 mots
- NE PAS inventer d'information absente du contenu source
- Français intégral
- Ton Senior Partner (assertif, pas de hedge)

Réponds UNIQUEMENT avec le résumé amélioré, sans préambule ni commentaire."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                system=SENIOR_PARTNER_PERSONA,
                messages=[{"role": "user", "content": prompt}]
            )
            improved = message.content[0].text.strip()

            # Validation basique : le résumé amélioré doit être plus riche
            if len(improved) > len(current_summary) * 0.7 and len(improved) < 800:
                return improved

            return None

        except Exception as e:
            console.print(f"  [red]✗ Erreur amélioration résumé: {str(e)[:60]}[/red]")
            return None

    def enrich_article(
        self,
        article: AnalyzedArticle,
        bloc_id: str
    ) -> bool:
        """
        Enrichit un article individuel. Retourne True si le résumé a été amélioré.
        """
        title = article.title_fr or article.article.title
        url = article.article.url

        # Étape 1 : vérifier si le résumé est déjà riche
        if self._is_summary_already_rich(article):
            self.stats["already_rich"] += 1
            return False

        enriched_content = None

        # Étape 2 : tenter la récupération directe
        if not self._is_paywall_domain(url):
            enriched_content = self._fetch_article_content(url)
            if enriched_content:
                self.stats["enriched_direct"] += 1

        # Étape 3 : si pas de contenu direct, chercher via le web
        if not enriched_content:
            time.sleep(self.DELAY_BETWEEN_REQUESTS)
            enriched_content = self._search_web_extracts(
                title, article.article.source
            )
            if enriched_content:
                self.stats["enriched_search"] += 1

        # Étape 4 : si on a du contenu enrichi, améliorer le résumé
        if enriched_content and len(enriched_content) > self.MIN_USEFUL_CONTENT:
            improved = self._improve_summary(article, enriched_content, bloc_id)
            if improved:
                article.ai_summary = improved
                self.stats["summaries_improved"] += 1
                return True

        self.stats["failed"] += 1
        return False

    def enrich_selection(
        self,
        selection: CuratedSelection,
        bloc_order: Optional[List[str]] = None
    ) -> CuratedSelection:
        """
        Enrichit tous les articles d'une sélection curée.
        Modifie la sélection in-place et la retourne.
        """
        if bloc_order is None:
            bloc_order = ["essentiel", "strategies_marches", "nouveaux_modeles", "regulation"]

        blocs = getattr(selection, 'blocs', {})
        total_articles = sum(len(blocs.get(b, [])) for b in bloc_order)

        if total_articles == 0:
            return selection

        console.print(f"\n[bold blue]🔍 Enrichissement de {total_articles} articles sélectionnés...[/bold blue]")
        self.stats["total"] = total_articles

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Enrichissement", total=total_articles)

            for bloc_id in bloc_order:
                articles = blocs.get(bloc_id, [])
                for article in articles:
                    title = (article.title_fr or article.article.title)[:50]
                    progress.update(task, description=f"[dim]{title}...[/dim]")

                    improved = self.enrich_article(article, bloc_id)

                    if improved:
                        progress.console.print(
                            f"  [green]✓ Enrichi: {title}[/green]"
                        )

                    progress.advance(task)
                    time.sleep(self.DELAY_BETWEEN_REQUESTS)

        self._display_stats()
        return selection

    def _display_stats(self):
        """Affiche les statistiques d'enrichissement."""
        s = self.stats
        console.print(f"\n[bold green]✅ Enrichissement terminé[/bold green]")
        console.print(f"   {s['total']} articles traités :")
        console.print(f"   • {s['already_rich']} déjà riches (inchangés)")
        console.print(f"   • {s['enriched_direct']} enrichis via URL directe")
        console.print(f"   • {s['enriched_search']} enrichis via recherche web")
        console.print(f"   • {s['summaries_improved']} résumés améliorés par Claude")
        console.print(f"   • {s['failed']} non enrichis (paywall/indisponible)")
