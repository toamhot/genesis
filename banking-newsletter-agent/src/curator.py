"""
Module de curation des articles
Banking Newsletter Agent - Ares & Co

Ce module gère :
- Le scoring et ranking des articles
- La sélection des articles pour la newsletter
- Le groupement par thématique
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from rich.console import Console
from rich.table import Table

from analyzer import AnalyzedArticle

console = Console()


@dataclass
class CuratedSelection:
    """Sélection curée d'articles pour la newsletter"""
    top_articles: List[AnalyzedArticle]
    articles_by_category: Dict[str, List[AnalyzedArticle]]
    total_collected: int
    total_selected: int


class Curator:
    """Curateur d'articles pour la newsletter"""

    CATEGORY_NAMES = {
        "regulation": "Actualités Réglementaires",
        "monetary_policy": "Politique Monétaire",
        "french_banks": "Banques Françaises",
        "innovation": "Innovation & Digital",
        "ma": "M&A et Restructurations",
        "market": "Tendances Marché",
        "regulateur": "Régulateurs",
        "fintech": "Fintech",
    }

    def __init__(
        self,
        min_relevance_score: float = 5.0,
        max_articles_per_category: int = 3,
        max_total_articles: int = 10,
        target_month: Optional[datetime] = None,
        days_back: int = 30
    ):
        self.min_relevance_score = min_relevance_score
        self.max_articles_per_category = max_articles_per_category
        self.max_total_articles = max_total_articles

        # Configuration de la période cible
        if target_month is None:
            target_month = datetime.now() - relativedelta(months=1)
        self.target_month = target_month
        self.days_back = days_back
        self.cutoff_date = datetime.now() - timedelta(days=days_back)

    def calculate_final_score(self, article: AnalyzedArticle) -> float:
        """
        Calcule un score final combinant plusieurs facteurs.

        Facteurs pris en compte :
        - Score de pertinence IA (0-10)
        - Priorité de la source (1-3, inversé)
        - Priorité newsletter IA (1-5, inversé)
        - Récence de l'article
        """
        base_score = article.relevance_score

        # Bonus pour les sources prioritaires
        source_bonus = (4 - article.article.priority) * 0.5  # Max +1.5

        # Bonus pour la priorité newsletter
        priority_bonus = (6 - article.newsletter_priority) * 0.3  # Max +1.5

        # Bonus pour les articles récents (si date disponible)
        recency_bonus = 0
        if article.article.published_date:
            # Normaliser la date pour éviter les erreurs timezone
            pub_date = article.article.published_date
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)
            days_old = (datetime.now() - pub_date).days
            if days_old <= 7:
                recency_bonus = 1.0
            elif days_old <= 14:
                recency_bonus = 0.5

        final_score = base_score + source_bonus + priority_bonus + recency_bonus
        return min(final_score, 15.0)  # Cap à 15

    @staticmethod
    def normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Normalise une datetime en supprimant les informations de timezone.
        Permet de comparer des dates timezone-aware et timezone-naive.
        """
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt

    def filter_by_date(
        self,
        articles: List[AnalyzedArticle],
        strict: bool = False
    ) -> tuple[List[AnalyzedArticle], int]:
        """
        Filtre les articles par date.

        Args:
            articles: Liste des articles à filtrer
            strict: Si True, rejette les articles sans date

        Returns:
            Tuple (articles filtrés, nombre d'articles rejetés)
        """
        valid_articles = []
        rejected_count = 0
        no_date_count = 0
        now = datetime.now()

        for article in articles:
            pub_date = article.article.published_date

            # Pas de date
            if pub_date is None:
                no_date_count += 1
                if not strict:
                    valid_articles.append(article)
                else:
                    rejected_count += 1
                continue

            # Normaliser la date pour comparaison
            pub_date_normalized = self.normalize_datetime(pub_date)

            # Date dans le futur (erreur)
            if pub_date_normalized > now + timedelta(days=1):
                rejected_count += 1
                continue

            # Date trop ancienne
            if pub_date_normalized < self.cutoff_date:
                rejected_count += 1
                continue

            valid_articles.append(article)

        if no_date_count > 0:
            console.print(f"  [yellow]⚠ {no_date_count} articles sans date (acceptés par défaut)[/yellow]")

        return valid_articles, rejected_count

    def filter_and_rank(
        self,
        articles: List[AnalyzedArticle]
    ) -> List[AnalyzedArticle]:
        """Filtre et classe les articles par score"""
        # Filtrer par score minimum
        filtered = [
            a for a in articles
            if a.relevance_score >= self.min_relevance_score
        ]

        # Calculer le score final et trier
        scored = [(self.calculate_final_score(a), a) for a in filtered]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [a for _, a in scored]

    def group_by_category(
        self,
        articles: List[AnalyzedArticle]
    ) -> Dict[str, List[AnalyzedArticle]]:
        """Groupe les articles par catégorie"""
        grouped = defaultdict(list)

        for article in articles:
            category = article.assigned_category
            grouped[category].append(article)

        # Limiter le nombre d'articles par catégorie
        for category in grouped:
            grouped[category] = grouped[category][:self.max_articles_per_category]

        return dict(grouped)

    def deduplicate_similar(
        self,
        articles: List[AnalyzedArticle],
        similarity_threshold: float = 0.8
    ) -> List[AnalyzedArticle]:
        """
        Déduplique les articles similaires basé sur les entités et le titre.
        Garde l'article avec le meilleur score.
        """
        if not articles:
            return []

        unique = []
        seen_titles = set()

        for article in articles:
            # Normaliser le titre pour comparaison
            title_words = set(article.article.title.lower().split())

            # Vérifier la similarité avec les titres déjà vus
            is_duplicate = False
            for seen in seen_titles:
                seen_words = set(seen.split())
                # Calculer le coefficient de Jaccard
                intersection = len(title_words & seen_words)
                union = len(title_words | seen_words)
                similarity = intersection / union if union > 0 else 0

                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(article)
                seen_titles.add(article.article.title.lower())

        return unique

    def curate(self, articles: List[AnalyzedArticle], strict_date: bool = False) -> CuratedSelection:
        """
        Pipeline complet de curation :
        1. Validation des dates
        2. Filtre et ranking
        3. Déduplication
        4. Groupement par catégorie
        5. Sélection finale

        Args:
            articles: Liste des articles analysés
            strict_date: Si True, rejette les articles sans date
        """
        console.print(f"\n[bold blue]📋 Curation de {len(articles)} articles...[/bold blue]\n")
        console.print(f"  [dim]Période cible: depuis {self.cutoff_date.strftime('%d/%m/%Y')}[/dim]\n")

        # Étape 1: Valider les dates
        date_filtered, date_rejected = self.filter_by_date(articles, strict=strict_date)
        if date_rejected > 0:
            console.print(f"  [yellow]• {date_rejected} articles rejetés (hors période)[/yellow]")
        console.print(f"  [dim]• {len(date_filtered)} articles dans la période cible[/dim]")

        # Étape 2: Filtrer et classer
        ranked = self.filter_and_rank(date_filtered)
        console.print(f"  [dim]• {len(ranked)} articles après filtrage (score >= {self.min_relevance_score})[/dim]")

        # Étape 3: Dédupliquer
        deduplicated = self.deduplicate_similar(ranked)
        console.print(f"  [dim]• {len(deduplicated)} articles après déduplication[/dim]")

        # Étape 4: Sélectionner le top
        top_articles = deduplicated[:self.max_total_articles]
        console.print(f"  [dim]• {len(top_articles)} articles sélectionnés pour la newsletter[/dim]")

        # Étape 5: Grouper par catégorie
        by_category = self.group_by_category(top_articles)

        selection = CuratedSelection(
            top_articles=top_articles,
            articles_by_category=by_category,
            total_collected=len(articles),
            total_selected=len(top_articles)
        )

        self._display_summary(selection)

        return selection

    def _display_summary(self, selection: CuratedSelection):
        """Affiche un résumé de la sélection"""
        console.print(f"\n[bold green]✅ Curation terminée[/bold green]")
        console.print(f"   {selection.total_selected}/{selection.total_collected} articles retenus\n")

        # Tableau par catégorie
        table = Table(title="Répartition par catégorie")
        table.add_column("Catégorie", style="cyan")
        table.add_column("Articles", justify="right")

        for cat, articles in selection.articles_by_category.items():
            cat_name = self.CATEGORY_NAMES.get(cat, cat)
            table.add_row(cat_name, str(len(articles)))

        console.print(table)

        # Liste des top articles
        console.print("\n[bold]Top articles sélectionnés :[/bold]")
        for i, article in enumerate(selection.top_articles[:5], 1):
            score = self.calculate_final_score(article)
            console.print(
                f"  {i}. [cyan]{article.article.title[:60]}...[/cyan]\n"
                f"     [dim]Score: {score:.1f} | {article.assigned_category} | {article.article.source}[/dim]"
            )


if __name__ == "__main__":
    # Test avec des données fictives
    from collector import Article
    from analyzer import AnalyzedArticle

    test_articles = [
        AnalyzedArticle(
            article=Article(
                id="1", title="BCE maintient les taux", url="http://test.com/1",
                source="ECB", category="regulateur", published_date=None,
                content="", summary="", priority=1
            ),
            ai_summary="La BCE maintient ses taux directeurs.",
            relevance_score=8.5,
            assigned_category="monetary_policy",
            key_facts=["Taux inchangés"],
            entities=["BCE"],
            sentiment="neutral",
            newsletter_priority=1
        ),
        AnalyzedArticle(
            article=Article(
                id="2", title="BNP Paribas lance une nouvelle app", url="http://test.com/2",
                source="Finextra", category="innovation", published_date=None,
                content="", summary="", priority=2
            ),
            ai_summary="BNP Paribas innove avec une application mobile.",
            relevance_score=7.0,
            assigned_category="innovation",
            key_facts=["Nouvelle app"],
            entities=["BNP Paribas"],
            sentiment="positive",
            newsletter_priority=2
        ),
    ]

    curator = Curator()
    selection = curator.curate(test_articles)
