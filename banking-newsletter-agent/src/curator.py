"""
Module de curation des articles
Banking Newsletter Agent - Ares & Co

Ce module gère :
- Le scoring et ranking des articles
- La sélection des articles pour la newsletter
- Le filtrage par thème éditorial
- Le groupement par thématique
"""

import yaml
from pathlib import Path
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
    theme: Optional[str] = None  # Thème du mois
    theme_name: Optional[str] = None  # Nom du thème


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
        max_total_articles: int = 6,  # Réduit à 6 pour nouvelle structure
        min_articles_per_category: int = 1,
        target_month: Optional[datetime] = None,
        days_back: int = 30,
        themes_config_path: Optional[str] = None
    ):
        self.min_relevance_score = min_relevance_score
        self.max_articles_per_category = max_articles_per_category
        self.max_total_articles = max_total_articles
        self.min_articles_per_category = min_articles_per_category

        # Configuration de la période cible
        if target_month is None:
            target_month = datetime.now() - relativedelta(months=1)
        self.target_month = target_month
        self.days_back = days_back
        self.cutoff_date = datetime.now() - timedelta(days=days_back)

        # Charger la configuration des thèmes
        self.themes = {}
        if themes_config_path is None:
            themes_config_path = Path(__file__).parent.parent / "config" / "themes.yaml"
        self._load_themes(themes_config_path)

    def _load_themes(self, config_path: str):
        """Charge la configuration des thèmes éditoriaux"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.themes = config.get('themes', {})
        except FileNotFoundError:
            console.print(f"[yellow]⚠ Fichier thèmes non trouvé: {config_path}[/yellow]")
            self.themes = {}

    def get_available_themes(self) -> List[str]:
        """Retourne la liste des thèmes disponibles"""
        return list(self.themes.keys())

    def get_theme_info(self, theme_id: str) -> Optional[Dict]:
        """Retourne les informations d'un thème"""
        return self.themes.get(theme_id)

    def calculate_theme_relevance(
        self,
        article: AnalyzedArticle,
        theme_id: str
    ) -> float:
        """
        Calcule la pertinence d'un article pour un thème donné.

        Args:
            article: L'article analysé
            theme_id: L'identifiant du thème

        Returns:
            Score de pertinence thématique (0-5)
        """
        theme = self.themes.get(theme_id)
        if not theme:
            return 0

        keywords = theme.get('keywords', [])
        if not keywords:
            return 0

        # Texte à analyser (titre + résumé + faits clés)
        text_to_check = " ".join([
            article.article.title.lower(),
            (article.title_fr or "").lower(),
            article.ai_summary.lower(),
            " ".join(article.key_facts).lower() if article.key_facts else ""
        ])

        # Compter les mots-clés trouvés
        matches = 0
        for keyword in keywords:
            if keyword.lower() in text_to_check:
                matches += 1

        # Score proportionnel (max 5 points)
        score = min(5, matches * 0.5)
        return score

    def filter_by_theme(
        self,
        articles: List[AnalyzedArticle],
        theme_id: str,
        min_theme_score: float = 0.5
    ) -> List[AnalyzedArticle]:
        """
        Filtre et booste les articles selon leur pertinence pour le thème.

        Args:
            articles: Liste des articles à filtrer
            theme_id: Identifiant du thème
            min_theme_score: Score minimum pour inclure un article

        Returns:
            Articles filtrés et triés par pertinence thématique
        """
        theme = self.themes.get(theme_id)
        if not theme:
            console.print(f"[yellow]⚠ Thème inconnu: {theme_id}[/yellow]")
            return articles

        console.print(f"\n[bold cyan]🎯 Filtrage par thème: {theme.get('name', theme_id)}[/bold cyan]")

        scored_articles = []
        for article in articles:
            theme_score = self.calculate_theme_relevance(article, theme_id)
            if theme_score >= min_theme_score:
                scored_articles.append((theme_score, article))

        # Trier par score thématique décroissant
        scored_articles.sort(key=lambda x: x[0], reverse=True)

        filtered = [article for _, article in scored_articles]
        console.print(f"  [dim]• {len(filtered)}/{len(articles)} articles pertinents pour ce thème[/dim]")

        return filtered

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

    def ensure_minimum_per_category(
        self,
        articles: List[AnalyzedArticle],
        all_articles: List[AnalyzedArticle]
    ) -> List[AnalyzedArticle]:
        """
        S'assure qu'il y a au moins min_articles_per_category par catégorie.
        Remplit les catégories sous-représentées avec des articles supplémentaires.
        """
        # Grouper les articles sélectionnés par catégorie
        by_category = defaultdict(list)
        for article in articles:
            by_category[article.assigned_category].append(article)

        # Grouper TOUS les articles disponibles par catégorie
        all_by_category = defaultdict(list)
        for article in all_articles:
            all_by_category[article.assigned_category].append(article)

        # IDs déjà sélectionnés
        selected_ids = {a.article.id for a in articles}

        # Identifier les catégories qui ont des articles disponibles mais sous-représentées
        result = list(articles)

        for category, all_cat_articles in all_by_category.items():
            current_count = len(by_category.get(category, []))

            # Si cette catégorie a moins que le minimum requis
            if current_count < self.min_articles_per_category:
                # Chercher des articles supplémentaires dans cette catégorie
                for article in all_cat_articles:
                    if article.article.id not in selected_ids:
                        result.append(article)
                        selected_ids.add(article.article.id)
                        by_category[category].append(article)
                        current_count += 1

                        if current_count >= self.min_articles_per_category:
                            break

        return result

    def deduplicate_similar(
        self,
        articles: List[AnalyzedArticle],
        title_similarity_threshold: float = 0.4,
        entity_match_threshold: int = 2
    ) -> List[AnalyzedArticle]:
        """
        Déduplique les articles similaires basé sur :
        1. La similarité des titres (Jaccard)
        2. Les entités communes (banques, régulateurs mentionnés)

        Garde l'article avec le meilleur score pour chaque sujet.

        Args:
            articles: Liste triée par score (meilleurs en premier)
            title_similarity_threshold: Seuil Jaccard pour les titres (0.4 = 40%)
            entity_match_threshold: Nombre min d'entités communes pour considérer comme doublon
        """
        if not articles:
            return []

        unique = []
        seen_articles = []  # Liste de (title_words, title_fr_words, entities)
        duplicates_removed = 0

        # Mots à ignorer dans la comparaison de titres
        stopwords = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'en', 'pour',
                     'sur', 'dans', 'par', 'avec', 'the', 'a', 'an', 'of', 'to', 'for', 'in',
                     'on', 'at', 'by', 'its', 'son', 'sa', 'ses'}

        for article in articles:
            # Normaliser le titre original et français
            title_words = set(w for w in article.article.title.lower().split()
                            if w not in stopwords and len(w) > 2)
            title_fr_words = set(w for w in article.title_fr.lower().split()
                               if w not in stopwords and len(w) > 2) if article.title_fr else set()

            # Entités de l'article (normalisées)
            entities = set(e.lower() for e in article.entities) if article.entities else set()

            is_duplicate = False
            duplicate_of = None

            for i, (seen_title, seen_title_fr, seen_entities) in enumerate(seen_articles):
                # Test 1: Similarité des titres originaux
                if title_words and seen_title:
                    intersection = len(title_words & seen_title)
                    union = len(title_words | seen_title)
                    title_similarity = intersection / union if union > 0 else 0

                    if title_similarity >= title_similarity_threshold:
                        is_duplicate = True
                        duplicate_of = unique[i].article.title[:50]
                        break

                # Test 2: Similarité des titres français
                if title_fr_words and seen_title_fr:
                    intersection = len(title_fr_words & seen_title_fr)
                    union = len(title_fr_words | seen_title_fr)
                    title_fr_similarity = intersection / union if union > 0 else 0

                    if title_fr_similarity >= title_similarity_threshold:
                        is_duplicate = True
                        duplicate_of = unique[i].title_fr[:50] if unique[i].title_fr else unique[i].article.title[:50]
                        break

                # Test 3: Entités communes (au moins 2 entités identiques)
                if entities and seen_entities:
                    common_entities = entities & seen_entities
                    if len(common_entities) >= entity_match_threshold:
                        is_duplicate = True
                        duplicate_of = f"entités communes: {', '.join(list(common_entities)[:3])}"
                        break

            if not is_duplicate:
                unique.append(article)
                seen_articles.append((title_words, title_fr_words, entities))
            else:
                duplicates_removed += 1
                console.print(f"  [dim]↳ Doublon ignoré: {article.article.title[:40]}... (similaire à: {duplicate_of})[/dim]")

        if duplicates_removed > 0:
            console.print(f"  [yellow]• {duplicates_removed} doublons supprimés[/yellow]")

        return unique

    def curate(
        self,
        articles: List[AnalyzedArticle],
        strict_date: bool = False,
        theme_id: Optional[str] = None
    ) -> CuratedSelection:
        """
        Pipeline complet de curation :
        1. Validation des dates
        2. Filtrage par thème (si spécifié)
        3. Filtre et ranking
        4. Déduplication
        5. Sélection finale (6 articles pour le Radar)

        Args:
            articles: Liste des articles analysés
            strict_date: Si True, rejette les articles sans date
            theme_id: Identifiant du thème mensuel (optionnel)
        """
        theme_name = None
        if theme_id:
            theme_info = self.get_theme_info(theme_id)
            if theme_info:
                theme_name = theme_info.get('name', theme_id)

        console.print(f"\n[bold blue]📋 Curation de {len(articles)} articles...[/bold blue]\n")
        if theme_name:
            console.print(f"  [bold cyan]🎯 Thème du mois: {theme_name}[/bold cyan]\n")
        console.print(f"  [dim]Période cible: depuis {self.cutoff_date.strftime('%d/%m/%Y')}[/dim]\n")

        # Étape 1: Valider les dates
        date_filtered, date_rejected = self.filter_by_date(articles, strict=strict_date)
        if date_rejected > 0:
            console.print(f"  [yellow]• {date_rejected} articles rejetés (hors période)[/yellow]")
        console.print(f"  [dim]• {len(date_filtered)} articles dans la période cible[/dim]")

        # Étape 2: Filtrage par thème (si spécifié)
        if theme_id:
            themed = self.filter_by_theme(date_filtered, theme_id, min_theme_score=0.5)
            # Si pas assez d'articles sur le thème, garder tous les articles
            if len(themed) >= self.max_total_articles:
                date_filtered = themed
            else:
                console.print(f"  [yellow]⚠ Seulement {len(themed)} articles sur le thème, complément avec autres articles[/yellow]")
                # Garder les articles thématiques en premier, puis compléter
                other_articles = [a for a in date_filtered if a not in themed]
                date_filtered = themed + other_articles

        # Étape 3: Filtrer et classer
        ranked = self.filter_and_rank(date_filtered)
        console.print(f"  [dim]• {len(ranked)} articles après filtrage (score >= {self.min_relevance_score})[/dim]")

        # Étape 4: Dédupliquer
        deduplicated = self.deduplicate_similar(ranked)
        console.print(f"  [dim]• {len(deduplicated)} articles après déduplication[/dim]")

        # Étape 5: Sélectionner exactement 6 articles pour le Radar
        top_articles = deduplicated[:self.max_total_articles]
        console.print(f"  [dim]• {len(top_articles)} articles sélectionnés pour le Radar[/dim]")

        # Grouper par catégorie (pour compatibilité)
        by_category = self.group_by_category(top_articles)

        selection = CuratedSelection(
            top_articles=top_articles,
            articles_by_category=by_category,
            total_collected=len(articles),
            total_selected=len(top_articles),
            theme=theme_id,
            theme_name=theme_name
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
