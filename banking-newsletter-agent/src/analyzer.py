"""
Module d'analyse des articles avec Claude API
Banking Newsletter Agent - Ares & Co

Ce module gère :
- L'analyse et le résumé des articles via Claude
- Le scoring de pertinence
- La catégorisation automatique
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import json
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from collector import Article

console = Console()


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
    """Analyseur d'articles utilisant Claude API"""

    SYSTEM_PROMPT = """Tu es un analyste expert du secteur bancaire européen travaillant pour Ares & Co, un cabinet de conseil en stratégie.

Ta mission est d'analyser des articles d'actualité bancaire et de produire une analyse structurée ENTIÈREMENT EN FRANÇAIS.

IMPORTANT : Même si l'article source est en anglais, TOUT ton output doit être en français :
- Le résumé doit être en français
- Les faits clés doivent être en français
- Si le titre original est en anglais, propose une traduction française dans le résumé

Pour chaque article, tu dois :
1. Rédiger un résumé concis (2-3 phrases) EN FRANÇAIS
2. Évaluer la pertinence pour une newsletter destinée aux dirigeants bancaires (score 0-10)
3. Identifier la catégorie principale
4. Extraire les faits clés EN FRANÇAIS (bullet points)
5. Identifier les entités mentionnées (banques, régulateurs, personnes)
6. Déterminer le sentiment général
7. Attribuer une priorité newsletter (1=critique, 5=informatif)

Catégories possibles :
- regulation : Évolutions réglementaires (Bâle, DORA, MiCA, etc.)
- monetary_policy : Politique monétaire BCE, taux d'intérêt
- french_banks : Actualités des banques françaises
- innovation : Fintech, digital banking, IA
- ma : Fusions, acquisitions, restructurations
- market : Tendances générales du marché

Réponds UNIQUEMENT en JSON valide, avec tout le contenu EN FRANÇAIS."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Clé API Anthropic requise. "
                "Définir ANTHROPIC_API_KEY ou passer api_key au constructeur."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_claude(self, prompt: str) -> str:
        """Appelle Claude API avec retry automatique"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def analyze_article(self, article: Article) -> AnalyzedArticle:
        """Analyse un article individuel avec Claude"""
        prompt = f"""Analyse cet article d'actualité bancaire :

**Titre** : {article.title}
**Source** : {article.source}
**Date** : {article.published_date.strftime('%Y-%m-%d') if article.published_date else 'Non spécifiée'}
**Contenu** : {article.content[:1500] if article.content else article.summary}

Réponds en JSON avec cette structure exacte :
{{
    "title_fr": "Titre en français (traduit si l'original est en anglais, sinon identique)",
    "summary": "Résumé en français (2-3 phrases)",
    "relevance_score": 7.5,
    "category": "regulation",
    "key_facts": ["fait clé 1 en français", "fait clé 2 en français"],
    "entities": ["BCE", "BNP Paribas"],
    "sentiment": "neutral",
    "newsletter_priority": 2
}}"""

        try:
            response = self._call_claude(prompt)

            # Parser le JSON
            # Nettoyer la réponse si elle contient des backticks
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            clean_response = clean_response.strip()

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
            return AnalyzedArticle(
                article=article,
                ai_summary=article.summary[:200],
                relevance_score=5.0,
                assigned_category=article.category,
                key_facts=[],
                entities=[],
                sentiment="neutral",
                newsletter_priority=3,
                title_fr=article.title
            )

        except Exception as e:
            console.print(f"[red]✗ Erreur analyse {article.title[:40]}: {str(e)[:50]}[/red]")
            raise

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
        batch_size: int = 5
    ) -> List[AnalyzedArticle]:
        """
        Analyse optimisée par lots pour réduire les appels API.
        Envoie plusieurs articles dans un seul prompt.
        """
        console.print(f"\n[bold blue]🔍 Analyse optimisée de {len(articles)} articles...[/bold blue]\n")

        analyzed = []

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

            for batch in batches:
                try:
                    batch_results = self._analyze_batch_single_call(batch)
                    analyzed.extend(batch_results)
                except Exception as e:
                    console.print(f"[yellow]⚠ Erreur lot, analyse individuelle...[/yellow]")
                    # Fallback : analyser individuellement
                    for article in batch:
                        try:
                            result = self.analyze_article(article)
                            analyzed.append(result)
                        except Exception:
                            pass

                progress.update(task, advance=1)

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
IMPORTANT : Tous les contenus (résumés, titres, faits clés) doivent être EN FRANÇAIS, même si l'article original est en anglais.

{articles_text}

Réponds en JSON avec un tableau d'analyses, une par article :
{{
    "analyses": [
        {{
            "article_id": "id de l'article",
            "title_fr": "Titre en français (traduit si anglais)",
            "summary": "Résumé en français",
            "relevance_score": 7.5,
            "category": "regulation",
            "key_facts": ["fait clé en français"],
            "entities": ["BCE"],
            "sentiment": "neutral",
            "newsletter_priority": 2
        }}
    ]
}}"""

        response = self._call_claude(prompt)

        # Parser le JSON
        clean_response = response.strip()
        if clean_response.startswith("```"):
            clean_response = clean_response.split("```")[1]
            if clean_response.startswith("json"):
                clean_response = clean_response[4:]
        clean_response = clean_response.strip()

        data = json.loads(clean_response)

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
