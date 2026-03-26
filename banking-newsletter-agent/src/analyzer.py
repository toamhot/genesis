"""
Module d'analyse des articles avec Claude API
Banking Newsletter Agent - Ares & Co

Ce module gère :
- L'analyse et le résumé des articles via Claude
- Le scoring de pertinence
- La catégorisation automatique
"""

import os
import time
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import logging
import anthropic
import httpx
from httpx import Timeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from collector import Article
from persona import get_analysis_system_prompt, get_article_summary_guidelines

console = Console()
logger = logging.getLogger(__name__)

# Exceptions réseau transitoires qui méritent un retry
TRANSIENT_EXCEPTIONS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    ConnectionError,
    TimeoutError,
)


def clean_json_response(response: str) -> str:
    """
    Nettoie une réponse JSON de Claude pour la rendre parsable.
    Gère les cas courants de malformation.
    """
    text = response.strip()

    # Retirer les blocs de code markdown
    if "```" in text:
        # Extraire le contenu entre les backticks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()

    # Trouver le début du JSON (premier { ou [)
    json_start = -1
    for i, c in enumerate(text):
        if c in '{[':
            json_start = i
            break

    if json_start > 0:
        text = text[json_start:]

    # Trouver la fin du JSON (dernier } ou ])
    json_end = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] in '}]':
            json_end = i + 1
            break

    if json_end > 0:
        text = text[:json_end]

    # Remplacer les guillemets simples par des doubles (attention aux apostrophes)
    # Seulement si le JSON est vraiment malformé avec des single quotes
    if "'" in text and '"' not in text[:50]:
        text = text.replace("'", '"')

    # Retirer les virgules trailing avant } ou ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    return text


@dataclass
class AnalyzedArticle:
    """Article enrichi avec l'analyse Claude"""
    article: Article
    ai_summary: str
    relevance_score: float  # 0-10
    assigned_category: str
    key_facts: List[str]
    entities: List[str]  # Banques, régulateurs, personnes mentionnées
    sentiment: str  # positive, negative, neutral
    newsletter_priority: int  # 1-5, 1 = très important
    title_fr: str = ""  # Titre traduit en français si source anglaise


class Analyzer:
    """Analyseur d'articles utilisant Claude API avec persona Senior Partner"""

    # System prompt enrichi avec la persona Senior Partner
    SYSTEM_PROMPT = get_analysis_system_prompt() + """

RÈGLES CRITIQUES DE TRADUCTION ET FORMAT :
- TOUS les contenus doivent être EN FRANÇAIS, même si l'article source est en anglais
- Le champ "title_fr" DOIT OBLIGATOIREMENT contenir le titre TRADUIT EN FRANÇAIS
- Exemple: "ECB maintains interest rates" → title_fr: "La BCE maintient ses taux d'intérêt"

Pour chaque article, tu dois :
1. TRADUIRE le titre en français dans "title_fr" (OBLIGATOIRE)
2. Rédiger un résumé STRATÉGIQUE (2-3 phrases) - pas juste factuel, mais avec les implications
3. Évaluer la pertinence pour un CEO/CFO de banque française (score 0-10)
4. Identifier la catégorie principale
5. Extraire les faits clés ACTIONNABLES pour un dirigeant
6. Identifier les entités mentionnées (banques, régulateurs, personnes clés)
7. Déterminer le sentiment (impact sur le secteur)
8. Attribuer une priorité newsletter (1=critique/stratégique, 5=informatif)

Catégories possibles :
- regulation : Évolutions réglementaires (Bâle, DORA, MiCA, etc.)
- monetary_policy : Politique monétaire BCE, taux d'intérêt
- french_banks : Actualités des banques françaises
- innovation : Fintech, digital banking, IA
- ma : Fusions, acquisitions, restructurations
- market : Tendances générales du marché
- regulateur : Actualités des régulateurs (BCE, EBA, ACPR, AMF)
- fintech : Actualités fintech et néobanques

Réponds UNIQUEMENT en JSON valide, avec TOUT le contenu EN FRANÇAIS."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Clé API Anthropic requise. "
                "Définir ANTHROPIC_API_KEY ou passer api_key au constructeur."
            )
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            timeout=Timeout(120.0, connect=10.0),
        )
        self.model = "claude-sonnet-4-20250514"

    def _sample_articles_by_period(
        self,
        articles: List[Article],
        max_articles: int,
        num_periods: int = 4
    ) -> List[Article]:
        """
        Échantillonne les articles de manière équilibrée sur la période.

        Divise le mois en plusieurs périodes (par défaut 4 semaines) et prend
        un nombre proportionnel d'articles de chaque période pour assurer
        une couverture temporelle équilibrée.

        Args:
            articles: Liste de tous les articles collectés
            max_articles: Nombre maximum d'articles à retourner
            num_periods: Nombre de périodes pour diviser le mois (défaut: 4)

        Returns:
            Liste d'articles échantillonnés de manière équilibrée
        """
        from datetime import datetime, timedelta
        from collections import defaultdict

        # Séparer les articles avec et sans date
        articles_with_date = [a for a in articles if a.published_date]
        articles_without_date = [a for a in articles if not a.published_date]

        if not articles_with_date:
            # Pas de dates, prendre simplement les premiers
            return articles[:max_articles]

        # Trouver la plage de dates
        dates = [a.published_date for a in articles_with_date]
        # Normaliser les dates (enlever timezone si présent)
        dates_normalized = []
        for d in dates:
            if d.tzinfo is not None:
                d = d.replace(tzinfo=None)
            dates_normalized.append(d)

        min_date = min(dates_normalized)
        max_date = max(dates_normalized)

        # Calculer la durée de chaque période
        total_days = (max_date - min_date).days + 1
        period_days = max(1, total_days // num_periods)

        # Grouper les articles par période
        periods = defaultdict(list)
        for article in articles_with_date:
            pub_date = article.published_date
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)
            days_from_start = (pub_date - min_date).days
            period_idx = min(days_from_start // period_days, num_periods - 1)
            periods[period_idx].append(article)

        # Calculer combien d'articles prendre de chaque période
        articles_per_period = max_articles // num_periods
        remainder = max_articles % num_periods

        # Sélectionner les articles de chaque période
        selected = []
        for period_idx in range(num_periods):
            period_articles = periods.get(period_idx, [])
            # Trier par date décroissante dans chaque période
            period_articles.sort(
                key=lambda x: x.published_date.replace(tzinfo=None) if x.published_date.tzinfo else x.published_date,
                reverse=True
            )

            # Nombre d'articles à prendre de cette période
            take = articles_per_period + (1 if period_idx < remainder else 0)
            selected.extend(period_articles[:take])

        # Si on n'a pas assez, compléter avec les articles sans date
        if len(selected) < max_articles and articles_without_date:
            remaining = max_articles - len(selected)
            selected.extend(articles_without_date[:remaining])

        # Log de la répartition
        console.print(f"  [dim]Répartition: {len(periods)} périodes, {[len(periods.get(i, [])) for i in range(num_periods)]} articles/période[/dim]")

        return selected

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def _call_claude(self, prompt: str, max_tokens: int = 2048) -> str:
        """Appelle Claude API avec retry automatique sur erreurs réseau transitoires"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except anthropic.BadRequestError as e:
            console.print(f"[red]✗ BadRequestError Claude API: {str(e)[:120]}[/red]")
            raise  # Ne pas retrier, erreur non-transitoire
        except TRANSIENT_EXCEPTIONS as e:
            console.print(f"[yellow]⚠ Erreur réseau Claude API (retry auto): {type(e).__name__}: {str(e)[:80]}[/yellow]")
            raise  # Laisser tenacity gérer le retry

    def analyze_article(self, article: Article) -> AnalyzedArticle:
        """Analyse un article individuel avec Claude"""
        prompt = f"""Analyse cet article d'actualité bancaire :

**Titre original** : {article.title}
**Source** : {article.source}
**Date** : {article.published_date.strftime('%Y-%m-%d') if article.published_date else 'Non spécifiée'}
**Contenu** : {article.content[:1000] if article.content else article.summary}

IMPORTANT: Si le titre est en anglais, tu DOIS le traduire en français dans "title_fr".
IMPORTANT: Le résumé DOIT contenir AU MOINS 1 chiffre concret (montant, %, ratio, date).
IMPORTANT: La dernière phrase du résumé DOIT répondre au "so what?" pour un DG de banque française.

Réponds en JSON avec cette structure exacte :
{{
    "title_fr": "TITRE TRADUIT EN FRANÇAIS (obligatoire même si le titre original est déjà en français)",
    "summary": "Résumé en français (2-3 phrases analytiques, AVEC au moins 1 chiffre)",
    "relevance_score": 7.5,
    "category": "regulation",
    "key_facts": ["fait clé 1 en français", "fait clé 2 en français"],
    "entities": ["BCE", "BNP Paribas"],
    "sentiment": "neutral",
    "newsletter_priority": 2
}}"""

        try:
            response = self._call_claude(prompt)

            # Parser le JSON avec nettoyage robuste
            clean_response = clean_json_response(response)
            analysis = json.loads(clean_response)

            return AnalyzedArticle(
                article=article,
                ai_summary=analysis.get("summary", ""),
                relevance_score=float(analysis.get("relevance_score", 5)),
                assigned_category=analysis.get("category", article.category),
                key_facts=analysis.get("key_facts", []),
                entities=analysis.get("entities", []),
                sentiment=analysis.get("sentiment", "neutral"),
                newsletter_priority=int(analysis.get("newsletter_priority", 3)),
                title_fr=analysis.get("title_fr", article.title)
            )

        except json.JSONDecodeError as e:
            console.print(f"[yellow]⚠ Erreur parsing JSON pour {article.title[:40]}...[/yellow]")
            # Retourner une analyse par défaut
            return self._fallback_analysis(article)

        except anthropic.BadRequestError as e:
            console.print(f"[red]✗ BadRequest pour {article.title[:40]}: {str(e)[:80]}[/red]")
            console.print(f"[dim]  → Analyse fallback appliquée (scoring basique)[/dim]")
            return self._fallback_analysis(article)

        except Exception as e:
            console.print(f"[red]✗ Erreur analyse {article.title[:40]}: {str(e)[:50]}[/red]")
            raise

    def _fallback_analysis(self, article: Article) -> AnalyzedArticle:
        """Crée une analyse par défaut quand l'API échoue (scoring basique sans IA)"""
        return AnalyzedArticle(
            article=article,
            ai_summary=article.summary[:200] if article.summary else article.content[:200] if article.content else "",
            relevance_score=5.0,
            assigned_category=article.category,
            key_facts=[],
            entities=[],
            sentiment="neutral",
            newsletter_priority=3,
            title_fr=article.title
        )

    def analyze_batch(
        self,
        articles: List[Article],
        max_articles: Optional[int] = None
    ) -> List[AnalyzedArticle]:
        """Analyse un lot d'articles"""
        if max_articles:
            articles = articles[:max_articles]

        console.print(f"\n[bold blue]🔍 Analyse de {len(articles)} articles avec Claude...[/bold blue]\n")

        analyzed = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Analyse en cours...", total=len(articles))

            for article in articles:
                try:
                    result = self.analyze_article(article)
                    analyzed.append(result)
                    progress.update(
                        task,
                        advance=1,
                        description=f"[cyan]{article.title[:40]}..."
                    )
                except Exception as e:
                    console.print(f"[red]Erreur: {e}[/red]")
                    progress.update(task, advance=1)

        console.print(f"\n[bold green]✅ {len(analyzed)} articles analysés[/bold green]")

        return analyzed

    def analyze_batch_optimized(
        self,
        articles: List[Article],
        batch_size: int = 3,  # Réduit de 5 à 3 pour éviter troncature
        max_articles: int = 100
    ) -> List[AnalyzedArticle]:
        """
        Analyse optimisée par lots pour réduire les appels API.
        Envoie plusieurs articles dans un seul prompt.

        Args:
            articles: Liste des articles à analyser
            batch_size: Nombre d'articles par lot
            max_articles: Nombre maximum d'articles à analyser (pour éviter rate limiting)
        """
        # Limiter le nombre d'articles avec une répartition temporelle équilibrée
        if len(articles) > max_articles:
            console.print(f"[yellow]⚠ {len(articles)} articles collectés, sélection de {max_articles} avec répartition temporelle[/yellow]")
            articles = self._sample_articles_by_period(articles, max_articles)
            console.print(f"  [dim]→ Articles répartis sur la période du mois[/dim]")

        console.print(f"\n[bold blue]🔍 Analyse optimisée de {len(articles)} articles...[/bold blue]\n")

        analyzed = []
        rate_limit_backoff = 30  # Backoff adaptatif pour rate limit (augmente à chaque hit)

        # Diviser en lots
        batches = [articles[i:i + batch_size] for i in range(0, len(articles), batch_size)]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Analyse par lots...", total=len(batches))

            for batch_num, batch in enumerate(batches):
                try:
                    batch_results = self._analyze_batch_single_call(batch)
                    analyzed.extend(batch_results)
                except (anthropic.APIConnectionError, httpx.ConnectError, ConnectionError, TimeoutError) as e:
                    console.print(f"[yellow]⚠ Perte de connexion lot {batch_num+1}: {type(e).__name__}[/yellow]")
                    console.print(f"[yellow]  → Attente de 15s avant reconnexion...[/yellow]")
                    time.sleep(15)
                    # Réessayer le lot après reconnexion
                    try:
                        batch_results = self._analyze_batch_single_call(batch)
                        analyzed.extend(batch_results)
                        console.print(f"[green]  → Reconnexion réussie, lot {batch_num+1} analysé[/green]")
                    except Exception as retry_e:
                        console.print(f"[red]✗ Échec après reconnexion: {str(retry_e)[:80]}[/red]")
                        # Fallback : analyser individuellement avec délais plus longs
                        for article in batch:
                            try:
                                time.sleep(3)
                                result = self.analyze_article(article)
                                analyzed.append(result)
                            except Exception as ind_e:
                                console.print(f"[red]  → {article.title[:30]}: {str(ind_e)[:50]}[/red]")
                except anthropic.BadRequestError as e:
                    console.print(f"[yellow]⚠ BadRequest lot {batch_num+1}: {str(e)[:100]}[/yellow]")
                    console.print(f"[dim]  → Fallback: analyse individuelle avec contenu tronqué...[/dim]")
                    for article in batch:
                        try:
                            time.sleep(1)
                            result = self.analyze_article(article)
                            analyzed.append(result)
                        except anthropic.BadRequestError:
                            console.print(f"[dim]  → Fallback basique pour: {article.title[:40]}[/dim]")
                            analyzed.append(self._fallback_analysis(article))
                        except Exception as ind_e:
                            console.print(f"[red]  → {article.title[:30]}: {str(ind_e)[:50]}[/red]")
                            analyzed.append(self._fallback_analysis(article))
                except anthropic.RateLimitError as e:
                    console.print(f"[yellow]⚠ Rate limit atteint, pause de {rate_limit_backoff}s...[/yellow]")
                    time.sleep(rate_limit_backoff)
                    rate_limit_backoff = min(rate_limit_backoff * 2, 300)  # Double à chaque hit, max 5min
                    # Réessayer après pause
                    try:
                        batch_results = self._analyze_batch_single_call(batch)
                        analyzed.extend(batch_results)
                        rate_limit_backoff = max(rate_limit_backoff // 2, 30)  # Réduire si succès
                    except Exception as retry_e:
                        console.print(f"[red]✗ Échec après retry: {str(retry_e)[:80]}[/red]")
                except anthropic.APIError as e:
                    console.print(f"[red]✗ Erreur API: {str(e)[:100]}[/red]")
                    # Fallback : analyser individuellement avec délai
                    for article in batch:
                        try:
                            time.sleep(1)
                            result = self.analyze_article(article)
                            analyzed.append(result)
                        except Exception as ind_e:
                            console.print(f"[red]  → {article.title[:30]}: {str(ind_e)[:50]}[/red]")
                            analyzed.append(self._fallback_analysis(article))
                except Exception as e:
                    console.print(f"[yellow]⚠ Erreur lot {batch_num+1}: {str(e)[:80]}[/yellow]")
                    # Fallback : analyser individuellement
                    for article in batch:
                        try:
                            time.sleep(0.5)
                            result = self.analyze_article(article)
                            analyzed.append(result)
                        except Exception as ind_e:
                            console.print(f"[red]  → Échec: {str(ind_e)[:50]}[/red]")
                            analyzed.append(self._fallback_analysis(article))

                progress.update(task, advance=1)

                # Petit délai entre les lots pour éviter rate limiting
                if batch_num < len(batches) - 1:
                    time.sleep(1)

        console.print(f"\n[bold green]✅ {len(analyzed)} articles analysés[/bold green]")
        return analyzed

    def _analyze_batch_single_call(self, articles: List[Article]) -> List[AnalyzedArticle]:
        """Analyse plusieurs articles en un seul appel API"""
        articles_text = "\n\n---\n\n".join([
            f"**Article {i+1}**\n"
            f"ID: {a.id}\n"
            f"Titre: {a.title}\n"
            f"Source: {a.source}\n"
            f"Date: {a.published_date.strftime('%Y-%m-%d') if a.published_date else 'N/A'}\n"
            f"Contenu: {(a.content or a.summary)[:800]}"
            for i, a in enumerate(articles)
        ])

        prompt = f"""Analyse ces {len(articles)} articles d'actualité bancaire.

RÈGLES CRITIQUES :
1. TOUS les contenus (title_fr, summary, key_facts) DOIVENT être EN FRANÇAIS
2. Le champ "title_fr" DOIT contenir une TRADUCTION FRANÇAISE du titre original
3. Exemple: "ECB cuts rates" → title_fr: "La BCE réduit ses taux"

{articles_text}

RÈGLE CHIFFRES : Chaque résumé DOIT contenir AU MOINS 1 chiffre concret (montant, %, ratio, date).
Si l'article n'en contient pas, contextualiser avec un chiffre sectoriel de cadrage.

TERMINAISON : La dernière phrase de chaque résumé doit répondre au "so what?" pour un DG de banque française.

Réponds en JSON avec un tableau d'analyses, une par article :
{{
    "analyses": [
        {{
            "article_id": "id de l'article",
            "title_fr": "TITRE TRADUIT EN FRANÇAIS (obligatoire)",
            "summary": "Résumé analytique en français (2-3 phrases, AVEC au moins 1 chiffre)",
            "relevance_score": 7.5,
            "category": "regulation",
            "key_facts": ["fait clé 1 en français", "fait clé 2 en français"],
            "entities": ["BCE", "BNP Paribas"],
            "sentiment": "neutral",
            "newsletter_priority": 2
        }}
    ]
}}"""

        # Utiliser plus de tokens pour les lots (3 articles = ~1500 tokens de réponse)
        response = self._call_claude(prompt, max_tokens=4096)

        # Parser le JSON avec nettoyage robuste
        clean_response = clean_json_response(response)

        try:
            data = json.loads(clean_response)
        except json.JSONDecodeError as e:
            # Log l'erreur et la réponse pour debug
            console.print(f"[red]Erreur JSON: {e}[/red]")
            console.print(f"[dim]Réponse (derniers 200 chars): ...{response[-200:]}[/dim]")
            raise

        # Mapper les résultats aux articles
        results = []
        analyses_map = {a["article_id"]: a for a in data.get("analyses", [])}

        for article in articles:
            analysis = analyses_map.get(article.id, {})
            results.append(AnalyzedArticle(
                article=article,
                ai_summary=analysis.get("summary", article.summary[:200]),
                relevance_score=float(analysis.get("relevance_score", 5)),
                assigned_category=analysis.get("category", article.category),
                key_facts=analysis.get("key_facts", []),
                entities=analysis.get("entities", []),
                sentiment=analysis.get("sentiment", "neutral"),
                newsletter_priority=int(analysis.get("newsletter_priority", 3)),
                title_fr=analysis.get("title_fr", article.title)
            ))

        return results


if __name__ == "__main__":
    # Test avec un article fictif
    test_article = Article(
        id="test123",
        title="La BCE maintient ses taux directeurs inchangés",
        url="https://example.com/test",
        source="Test Source",
        category="regulateur",
        published_date=None,
        content="La Banque centrale européenne a décidé de maintenir ses taux directeurs...",
        summary="La BCE maintient ses taux",
        priority=1
    )

    try:
        analyzer = Analyzer()
        result = analyzer.analyze_article(test_article)
        console.print(f"\n[bold]Résultat de l'analyse :[/bold]")
        console.print(f"  Résumé : {result.ai_summary}")
        console.print(f"  Score : {result.relevance_score}/10")
        console.print(f"  Catégorie : {result.assigned_category}")
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        console.print("[dim]Définir ANTHROPIC_API_KEY pour tester l'analyseur[/dim]")
