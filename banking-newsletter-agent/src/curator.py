"""
Module de curation des articles - V3
Banking Newsletter Agent - Ares & Co

Ce module gère :
- Le scoring et ranking des articles
- La distribution dans les 4 blocs éditoriaux
- Le filtrage par thème éditorial
- La déduplication

V3 : Distribution dans 4 blocs (Essentiel, Stratégies & marchés, Nouveaux modèles, Régulation)
     au lieu d'un Radar plat.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from rich.console import Console
from rich.table import Table

from analyzer import AnalyzedArticle

console = Console()


@dataclass
class CuratedSelection:
    """Sélection curée d'articles pour la newsletter V3"""
    # Articles distribués par bloc éditorial
    blocs: Dict[str, List[AnalyzedArticle]] = field(default_factory=dict)
    # Tous les articles sélectionnés (liste plate, ordonnée)
    top_articles: List[AnalyzedArticle] = field(default_factory=list)
    # Compatibilité V2
    articles_by_category: Dict[str, List[AnalyzedArticle]] = field(default_factory=dict)
    total_collected: int = 0
    total_selected: int = 0
    theme: Optional[str] = None
    theme_name: Optional[str] = None


class Curator:
    """Curateur d'articles pour la newsletter V3 — 4 blocs éditoriaux"""

    # Mapping catégories IA → blocs newsletter
    CATEGORY_TO_BLOC = {
        "regulation": "regulation",
        "monetary_policy": "regulation",
        "regulateur": "regulation",
        "french_banks": "strategies_marches",
        "ma": "strategies_marches",
        "market": "strategies_marches",
        "innovation": "nouveaux_modeles",
        "fintech": "nouveaux_modeles",
    }

    BLOC_NAMES = {
        "essentiel": "L'essentiel",
        "strategies_marches": "Stratégies & marchés",
        "nouveaux_modeles": "Nouveaux modèles",
        "regulation": "Régulation & supervision",
    }

    BLOC_LIMITS = {
        "essentiel": (2, 4),          # 2 à 4 items (thème du mois, profondeur élevée)
        "strategies_marches": (3, 6),  # 3 à 6 items
        "nouveaux_modeles": (3, 5),    # 3 à 5 items
        "regulation": (3, 5),          # 3 à 5 items
    }

    BLOC_ORDER = ["essentiel", "strategies_marches", "nouveaux_modeles", "regulation"]

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

    # Sources françaises connues
    FRENCH_SOURCES = {
        'les echos', 'l\'agefi', 'la tribune', 'bfm', 'challenges',
        'le figaro', 'le monde', 'option finance', 'revue banque',
        'mind fintech', 'c\'est pas mon idée', 'france fintech',
        'banque de france', 'acpr', 'amf', 'bnp', 'société générale',
        'crédit agricole', 'bpce', 'la banque postale', 'lcl',
        'boursorama', 'fortuneo', 'orange bank', 'argus de l\'assurance'
    }

    # Entités françaises
    FRENCH_ENTITIES = {
        'france', 'français', 'française', 'paris', 'hexagone',
        'bnp paribas', 'société générale', 'crédit agricole', 'bpce',
        'la banque postale', 'lcl', 'crédit mutuel', 'caisse d\'épargne',
        'banque populaire', 'cic', 'hsbc france', 'boursorama', 'fortuneo',
        'orange bank', 'nickel', 'revolut france', 'n26 france',
        'amf', 'acpr', 'banque de france', 'bercy', 'trésor'
    }

    def __init__(
        self,
        min_relevance_score: float = 5.0,
        max_total_articles: int = 12,
        target_month: Optional[datetime] = None,
        days_back: int = 30,
        themes_config_path: Optional[str] = None
    ):
        self.min_relevance_score = min_relevance_score
        self.max_total_articles = max_total_articles

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

    def is_french_article(self, article: AnalyzedArticle) -> bool:
        """Détermine si un article concerne principalement la France."""
        source_lower = article.article.source.lower()
        if any(fr_source in source_lower for fr_source in self.FRENCH_SOURCES):
            return True

        if article.entities:
            entities_lower = [e.lower() for e in article.entities]
            if any(fr_entity in ' '.join(entities_lower) for fr_entity in self.FRENCH_ENTITIES):
                return True

        content_lower = f"{article.article.title} {article.title_fr or ''} {article.ai_summary}".lower()
        french_indicators = ['france', 'français', 'française', 'hexagone', 'paris', 'acpr', 'amf']
        if any(indicator in content_lower for indicator in french_indicators):
            return True

        return False

    def calculate_theme_relevance(
        self,
        article: AnalyzedArticle,
        theme_id: str
    ) -> float:
        """Calcule la pertinence d'un article pour un thème donné (0-5)."""
        theme = self.themes.get(theme_id)
        if not theme:
            return 0

        keywords = theme.get('keywords', [])
        if not keywords:
            return 0

        text_to_check = " ".join([
            article.article.title.lower(),
            (article.title_fr or "").lower(),
            article.ai_summary.lower(),
            " ".join(article.key_facts).lower() if article.key_facts else ""
        ])

        matches = sum(1 for keyword in keywords if keyword.lower() in text_to_check)
        return min(5, matches * 0.5)

    # Phrases qui signalent un résumé de mauvaise qualité (IA n'a pas assez d'info)
    WEAK_SUMMARY_INDICATORS = [
        "absence de détails",
        "limite l'analyse",
        "informations limitées",
        "pas suffisamment d'informations",
        "détails non disponibles",
        "impossible d'analyser",
        "contenu non accessible",
        "à compléter",
        "sans plus de détails",
        "manque de précision",
    ]

    def filter_weak_summaries(
        self,
        articles: List[AnalyzedArticle]
    ) -> List[AnalyzedArticle]:
        """
        Rejette les articles dont le résumé IA est trop faible pour être publié.
        Un résumé faible contient des aveux d'impuissance de l'IA.
        """
        strong = []
        weak_count = 0

        for article in articles:
            summary_lower = article.ai_summary.lower()
            is_weak = any(
                indicator in summary_lower
                for indicator in self.WEAK_SUMMARY_INDICATORS
            )

            # Aussi rejeter les résumés trop courts (< 50 chars)
            if is_weak or len(article.ai_summary.strip()) < 50:
                weak_count += 1
                console.print(
                    f"  [dim]  ✗ Rejeté (résumé faible): {(article.title_fr or article.article.title)[:50]}...[/dim]"
                )
            else:
                strong.append(article)

        if weak_count > 0:
            console.print(f"  [yellow]• {weak_count} articles rejetés (résumés trop faibles)[/yellow]")

        return strong

    def calculate_final_score(self, article: AnalyzedArticle) -> float:
        """Calcule un score final combinant pertinence IA, source et récence."""
        base_score = article.relevance_score

        # Bonus sources prioritaires
        source_bonus = (4 - article.article.priority) * 0.5  # Max +1.5

        # Bonus priorité newsletter
        priority_bonus = (6 - article.newsletter_priority) * 0.3  # Max +1.5

        # Bonus récence
        recency_bonus = 0
        if article.article.published_date:
            pub_date = article.article.published_date
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)
            days_old = (datetime.now() - pub_date).days
            if days_old <= 7:
                recency_bonus = 1.0
            elif days_old <= 14:
                recency_bonus = 0.5

        return min(base_score + source_bonus + priority_bonus + recency_bonus, 15.0)

    @staticmethod
    def normalize_datetime(dt: Optional[datetime]) -> Optional[datetime]:
        """Normalise une datetime en supprimant les informations de timezone."""
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
        """Filtre les articles par date."""
        valid_articles = []
        rejected_count = 0
        no_date_count = 0
        now = datetime.now()

        for article in articles:
            pub_date = article.article.published_date

            if pub_date is None:
                no_date_count += 1
                if not strict:
                    valid_articles.append(article)
                else:
                    rejected_count += 1
                continue

            pub_date_normalized = self.normalize_datetime(pub_date)

            if pub_date_normalized > now + timedelta(days=1):
                rejected_count += 1
                continue

            if pub_date_normalized < self.cutoff_date:
                rejected_count += 1
                continue

            valid_articles.append(article)

        if no_date_count > 0:
            console.print(f"  [yellow]⚠ {no_date_count} articles sans date (acceptés par défaut)[/yellow]")

        return valid_articles, rejected_count

    def filter_by_theme(
        self,
        articles: List[AnalyzedArticle],
        theme_id: str,
        min_theme_score: float = 0.5,
        target_count: int = 12
    ) -> List[AnalyzedArticle]:
        """Filtre et booste les articles selon leur pertinence pour le thème."""
        theme = self.themes.get(theme_id)
        if not theme:
            console.print(f"[yellow]⚠ Thème inconnu: {theme_id}[/yellow]")
            return articles

        console.print(f"\n[bold cyan]🎯 Filtrage par thème: {theme.get('name', theme_id)}[/bold cyan]")

        french_articles = []
        international_articles = []

        for article in articles:
            theme_score = self.calculate_theme_relevance(article, theme_id)
            is_french = self.is_french_article(article)

            if theme_score >= min_theme_score:
                final_score = theme_score + (2.0 if is_french else 0)
                if is_french:
                    french_articles.append((final_score, theme_score, article))
                else:
                    international_articles.append((final_score, theme_score, article))

        french_articles.sort(key=lambda x: x[0], reverse=True)
        international_articles.sort(key=lambda x: x[0], reverse=True)

        console.print(f"  [dim]• {len(french_articles)} articles France sur le thème[/dim]")
        console.print(f"  [dim]• {len(international_articles)} articles internationaux sur le thème[/dim]")

        result = []
        for score, theme_score, article in french_articles:
            if len(result) < target_count:
                result.append(article)

        if len(result) < target_count:
            remaining = target_count - len(result)
            for score, theme_score, article in international_articles[:remaining]:
                result.append(article)

        console.print(f"  [bold]→ {len(result)} articles sélectionnés[/bold]")
        return result

    def filter_and_rank(
        self,
        articles: List[AnalyzedArticle]
    ) -> List[AnalyzedArticle]:
        """Filtre et classe les articles par score"""
        filtered = [
            a for a in articles
            if a.relevance_score >= self.min_relevance_score
        ]
        scored = [(self.calculate_final_score(a), a) for a in filtered]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in scored]

    def _extract_content_words(self, text: str, stopwords: set) -> set:
        """Extrait les mots significatifs d'un texte."""
        return set(w for w in text.lower().split() if w not in stopwords and len(w) > 2)

    def deduplicate_similar(
        self,
        articles: List[AnalyzedArticle],
        title_similarity_threshold: float = 0.4,
        summary_similarity_threshold: float = 0.35,
        entity_match_threshold: int = 2
    ) -> List[AnalyzedArticle]:
        """
        Déduplique les articles similaires.
        V3 : ajoute la comparaison sémantique sur les résumés IA (pas juste les titres).
        """
        if not articles:
            return []

        unique = []
        seen_articles = []
        duplicates_removed = 0

        stopwords = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'en', 'pour',
                     'sur', 'dans', 'par', 'avec', 'the', 'a', 'an', 'of', 'to', 'for', 'in',
                     'on', 'at', 'by', 'its', 'son', 'sa', 'ses', 'cette', 'ces', 'qui', 'que',
                     'est', 'sont', 'ont', 'aux', 'plus', 'pas', 'une', 'also', 'has', 'was'}

        for article in articles:
            title_words = self._extract_content_words(article.article.title, stopwords)
            title_fr_words = self._extract_content_words(article.title_fr, stopwords) if article.title_fr else set()
            summary_words = self._extract_content_words(article.ai_summary, stopwords) if article.ai_summary else set()
            entities = set(e.lower() for e in article.entities) if article.entities else set()

            is_duplicate = False

            for seen_title, seen_title_fr, seen_summary, seen_entities in seen_articles:
                # Check title similarity (original)
                if title_words and seen_title:
                    intersection = len(title_words & seen_title)
                    union = len(title_words | seen_title)
                    if union > 0 and intersection / union >= title_similarity_threshold:
                        is_duplicate = True
                        break

                # Check translated title similarity
                if title_fr_words and seen_title_fr:
                    intersection = len(title_fr_words & seen_title_fr)
                    union = len(title_fr_words | seen_title_fr)
                    if union > 0 and intersection / union >= title_similarity_threshold:
                        is_duplicate = True
                        break

                # NEW: Check summary semantic similarity (catches same-topic articles with different titles)
                if summary_words and seen_summary:
                    intersection = len(summary_words & seen_summary)
                    union = len(summary_words | seen_summary)
                    if union > 0 and intersection / union >= summary_similarity_threshold:
                        is_duplicate = True
                        break

                # Check entity overlap
                if entities and seen_entities and len(entities & seen_entities) >= entity_match_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(article)
                seen_articles.append((title_words, title_fr_words, summary_words, entities))
            else:
                duplicates_removed += 1

        if duplicates_removed > 0:
            console.print(f"  [yellow]• {duplicates_removed} doublons supprimés (titres + résumés + entités)[/yellow]")

        return unique

    def cap_per_source(
        self,
        articles: List[AnalyzedArticle],
        max_per_source: int = 2
    ) -> List[AnalyzedArticle]:
        """
        Plafonne le nombre d'articles par source pour garantir la diversité.
        Garde les articles les mieux scorés pour chaque source.
        """
        source_counts = defaultdict(int)
        capped = []
        removed = 0

        for article in articles:
            source = article.article.source.lower().strip()
            if source_counts[source] < max_per_source:
                capped.append(article)
                source_counts[source] += 1
            else:
                removed += 1

        if removed > 0:
            console.print(f"  [yellow]• {removed} articles retirés (plafond {max_per_source}/source)[/yellow]")

        return capped

    def enforce_bloc_diversity(
        self,
        blocs: Dict[str, List['AnalyzedArticle']]
    ) -> Dict[str, List['AnalyzedArticle']]:
        """
        Applique les contraintes de diversité du CDC par bloc :
        - Bloc 2 (Stratégies) : pas 2 items sur le même acteur
        - Bloc 4 (Régulation) : pas 2 items sur le même régulateur sauf sujets très distincts
        """
        # Bloc 2 — max 1 article par acteur principal
        if "strategies_marches" in blocs:
            seen_actors = set()
            diversified = []
            removed_actors = 0
            for article in blocs["strategies_marches"]:
                # L'acteur principal est la première entité identifiée
                main_actor = None
                if article.entities:
                    main_actor = article.entities[0].lower().strip()

                if main_actor and main_actor in seen_actors:
                    removed_actors += 1
                    continue
                if main_actor:
                    seen_actors.add(main_actor)
                diversified.append(article)

            if removed_actors > 0:
                console.print(f"  [yellow]• Bloc Stratégies: {removed_actors} items retirés (même acteur)[/yellow]")
            blocs["strategies_marches"] = diversified

        # Bloc 4 — max 1 article par régulateur
        if "regulation" in blocs:
            regulators = {"bce", "ecb", "eba", "amf", "acpr", "banque de france",
                          "commission européenne", "european commission"}
            seen_regulators = set()
            diversified = []
            removed_regs = 0
            for article in blocs["regulation"]:
                source_lower = article.article.source.lower()
                entities_lower = [e.lower() for e in article.entities] if article.entities else []

                # Identifier le régulateur principal
                main_reg = None
                for reg in regulators:
                    if reg in source_lower or any(reg in e for e in entities_lower):
                        main_reg = reg
                        break

                if main_reg and main_reg in seen_regulators:
                    removed_regs += 1
                    continue
                if main_reg:
                    seen_regulators.add(main_reg)
                diversified.append(article)

            if removed_regs > 0:
                console.print(f"  [yellow]• Bloc Régulation: {removed_regs} items retirés (même régulateur)[/yellow]")
            blocs["regulation"] = diversified

        return blocs

    def distribute_to_blocs(
        self,
        articles: List[AnalyzedArticle],
        theme_id: Optional[str] = None
    ) -> Dict[str, List[AnalyzedArticle]]:
        """
        Distribue les articles dans les 4 blocs éditoriaux.

        V3 amélioré :
        - Bloc 1 "L'essentiel" : articles les plus pertinents pour le THÈME du mois
          (doivent documenter la thèse de l'éditorial, pas être un fourre-tout)
        - Bloc 2 "Stratégies & marchés" : M&A, banques françaises, tendances marché
        - Bloc 3 "Nouveaux modèles" : innovation, fintech
        - Bloc 4 "Régulation & supervision" : regulation, politique monétaire, régulateurs
        """
        blocs = {bloc: [] for bloc in self.BLOC_ORDER}

        # D'abord, distribuer dans les blocs 2-4 par catégorie
        candidates_by_bloc = defaultdict(list)
        for article in articles:
            bloc = self.CATEGORY_TO_BLOC.get(article.assigned_category, "strategies_marches")
            candidates_by_bloc[bloc].append(article)

        # Remplir les blocs 2-4 avec les limites
        for bloc_id in ["strategies_marches", "nouveaux_modeles", "regulation"]:
            _, max_items = self.BLOC_LIMITS[bloc_id]
            blocs[bloc_id] = candidates_by_bloc[bloc_id][:max_items]

        # ──────────────────────────────────────────────────
        # Bloc 1 "L'essentiel" — DOIT être lié au thème
        # ──────────────────────────────────────────────────
        assigned_ids = set()
        for bloc_id in ["strategies_marches", "nouveaux_modeles", "regulation"]:
            for a in blocs[bloc_id]:
                assigned_ids.add(a.article.id)

        # Stratégie : si un thème est défini, L'essentiel pioche PARMI TOUS les articles
        # (y compris ceux déjà dans d'autres blocs) les plus pertinents thématiquement.
        # L'article est alors retiré de son bloc d'origine.
        essentiel_candidates = []
        min_theme_score_essentiel = 1.0  # Seuil minimum de pertinence thématique

        for article in articles:
            score = self.calculate_final_score(article)
            theme_score = 0

            if theme_id:
                theme_score = self.calculate_theme_relevance(article, theme_id)
                # L'essentiel EXIGE une pertinence thématique forte
                if theme_score < min_theme_score_essentiel:
                    continue
                score += theme_score * 3  # Triple bonus thème pour L'essentiel

            essentiel_candidates.append((score, theme_score, article))

        essentiel_candidates.sort(key=lambda x: x[0], reverse=True)
        _, max_essentiel = self.BLOC_LIMITS["essentiel"]

        for score, theme_score, article in essentiel_candidates[:max_essentiel]:
            blocs["essentiel"].append(article)
            # Retirer du bloc d'origine si nécessaire
            for bloc_id in ["strategies_marches", "nouveaux_modeles", "regulation"]:
                if article in blocs[bloc_id]:
                    blocs[bloc_id].remove(article)
                    break

        # Si pas assez de candidats thématiques, prendre les top articles globaux
        # mais uniquement ceux avec un score élevé (pas de remplissage faible)
        if not blocs["essentiel"] and articles:
            non_assigned = [a for a in articles if a.article.id not in assigned_ids]
            non_assigned.sort(key=lambda a: self.calculate_final_score(a), reverse=True)
            # Seulement si le meilleur candidat a un score > 10
            if non_assigned and self.calculate_final_score(non_assigned[0]) > 10:
                blocs["essentiel"] = [non_assigned[0]]
            else:
                # Prendre le meilleur tous blocs confondus
                best = articles[0]
                for bloc_id in ["strategies_marches", "nouveaux_modeles", "regulation"]:
                    if best in blocs[bloc_id]:
                        blocs[bloc_id].remove(best)
                        break
                blocs["essentiel"] = [best]

        return blocs

    def curate(
        self,
        articles: List[AnalyzedArticle],
        strict_date: bool = False,
        theme_id: Optional[str] = None
    ) -> CuratedSelection:
        """
        Pipeline complet de curation V3 :
        1. Validation des dates
        2. Filtrage par thème (si spécifié)
        3. Filtre et ranking
        4. Déduplication
        5. Distribution dans les 4 blocs éditoriaux
        """
        theme_name = None
        if theme_id:
            theme_info = self.get_theme_info(theme_id)
            if theme_info:
                theme_name = theme_info.get('name', theme_id)

        console.print(f"\n[bold blue]📋 Curation V3 de {len(articles)} articles...[/bold blue]\n")
        if theme_name:
            console.print(f"  [bold cyan]🎯 Thème du mois: {theme_name}[/bold cyan]\n")
        console.print(f"  [dim]Période cible: depuis {self.cutoff_date.strftime('%d/%m/%Y')}[/dim]\n")

        # Étape 0: Filtrer les résumés faibles
        quality_filtered = self.filter_weak_summaries(articles)

        # Étape 1: Valider les dates
        date_filtered, date_rejected = self.filter_by_date(quality_filtered, strict=strict_date)
        if date_rejected > 0:
            console.print(f"  [yellow]• {date_rejected} articles rejetés (hors période)[/yellow]")
        console.print(f"  [dim]• {len(date_filtered)} articles dans la période cible[/dim]")

        # Étape 2: Filtrage par thème (si spécifié)
        if theme_id:
            themed = self.filter_by_theme(date_filtered, theme_id, min_theme_score=0.5)
            if len(themed) >= self.max_total_articles:
                date_filtered = themed
            else:
                console.print(f"  [yellow]⚠ Seulement {len(themed)} articles sur le thème, complément avec autres articles[/yellow]")
                other_articles = [a for a in date_filtered if a not in themed]
                date_filtered = themed + other_articles

        # Étape 3: Filtrer et classer
        ranked = self.filter_and_rank(date_filtered)
        console.print(f"  [dim]• {len(ranked)} articles après filtrage (score >= {self.min_relevance_score})[/dim]")

        # Étape 4: Dédupliquer (titres + résumés + entités)
        deduplicated = self.deduplicate_similar(ranked)
        console.print(f"  [dim]• {len(deduplicated)} articles après déduplication[/dim]")

        # Étape 4b: Plafonner par source (max 3 articles/source)
        diversified = self.cap_per_source(deduplicated, max_per_source=3)
        console.print(f"  [dim]• {len(diversified)} articles après diversification sources[/dim]")

        # Étape 5: Distribuer dans les 4 blocs
        blocs = self.distribute_to_blocs(diversified, theme_id=theme_id)

        # Étape 6: Contraintes de diversité par bloc (CDC anti-patterns)
        blocs = self.enforce_bloc_diversity(blocs)

        # Construire la liste plate (ordonnée par bloc)
        top_articles = []
        for bloc_id in self.BLOC_ORDER:
            top_articles.extend(blocs[bloc_id])

        # Grouper par catégorie (compatibilité V2)
        by_category = defaultdict(list)
        for article in top_articles:
            by_category[article.assigned_category].append(article)

        total_selected = sum(len(articles) for articles in blocs.values())

        selection = CuratedSelection(
            blocs=blocs,
            top_articles=top_articles,
            articles_by_category=dict(by_category),
            total_collected=len(articles),
            total_selected=total_selected,
            theme=theme_id,
            theme_name=theme_name
        )

        self._display_summary(selection)

        return selection

    def _display_summary(self, selection: CuratedSelection):
        """Affiche un résumé de la sélection V3"""
        console.print(f"\n[bold green]✅ Curation V3 terminée[/bold green]")
        console.print(f"   {selection.total_selected}/{selection.total_collected} articles retenus\n")

        # Tableau par bloc
        table = Table(title="Répartition par bloc éditorial")
        table.add_column("Bloc", style="cyan")
        table.add_column("Nom", style="white")
        table.add_column("Articles", justify="right")

        item_num = 1
        for bloc_id in self.BLOC_ORDER:
            articles = selection.blocs.get(bloc_id, [])
            bloc_name = self.BLOC_NAMES.get(bloc_id, bloc_id)
            count = len(articles)
            if count > 0:
                nums = f"#{item_num}-#{item_num + count - 1}"
                item_num += count
            else:
                nums = "-"
            table.add_row(f"Bloc {self.BLOC_ORDER.index(bloc_id) + 1}", bloc_name, f"{count} ({nums})")

        console.print(table)

        # Détail des articles
        console.print("\n[bold]Articles sélectionnés par bloc :[/bold]")
        item_num = 1
        for bloc_id in self.BLOC_ORDER:
            articles = selection.blocs.get(bloc_id, [])
            if articles:
                bloc_name = self.BLOC_NAMES.get(bloc_id, bloc_id)
                console.print(f"\n  [bold cyan]{bloc_name}[/bold cyan]")
                for article in articles:
                    score = self.calculate_final_score(article)
                    title = article.title_fr if article.title_fr else article.article.title
                    console.print(
                        f"    #{item_num}. [dim]{title[:55]}...[/dim]\n"
                        f"         [dim]Score: {score:.1f} | {article.article.source}[/dim]"
                    )
                    item_num += 1


if __name__ == "__main__":
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
