"""
Module Audit Trail — Traçabilité de la production newsletter
Banking Newsletter Agent - Ares & Co

Génère un fichier Excel (.xlsx) documentant chaque étape du pipeline :
- Onglet 1 : Synthèse (KPIs, paramètres)
- Onglet 2 : Collecte (sources, statuts, erreurs)
- Onglet 3 : Articles analysés (scores, catégories, résumés)
- Onglet 4 : Curation (retenu/rejeté, raisons, blocs)
- Onglet 5 : Newsletter finale (articles publiés dans l'ordre)
- Onglet 6 : Qualité (métriques, diversité, couverture)
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import Counter, defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from rich.console import Console

console = Console()


# ──────────────────────────────────────────────────────────────
# Couleurs et styles Excel
# ──────────────────────────────────────────────────────────────
HEADER_FILL = PatternFill(start_color="1A2A3A", end_color="1A2A3A", fill_type="solid")
HEADER_FONT = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
SUBHEADER_FILL = PatternFill(start_color="EEF2F7", end_color="EEF2F7", fill_type="solid")
SUBHEADER_FONT = Font(name="Calibri", bold=True, size=10)
GOOD_FILL = PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid")
WARN_FILL = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
BAD_FILL = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="D1D5DB"),
    top=Side(style="thin", color="D1D5DB"),
    bottom=Side(style="thin", color="D1D5DB"),
)


@dataclass
class SourceLog:
    """Log d'une source de collecte."""
    name: str
    url: str
    status: str  # "OK", "error", "timeout"
    articles_count: int = 0
    error_message: str = ""


@dataclass
class ArticleLog:
    """Log d'un article à travers le pipeline."""
    article_id: str
    title_original: str
    title_fr: str = ""
    source: str = ""
    url: str = ""
    published_date: Optional[datetime] = None
    category_source: str = ""
    # Analyse
    relevance_score: float = 0.0
    category_ai: str = ""
    newsletter_priority: int = 0
    sentiment: str = ""
    summary: str = ""
    entities: str = ""
    key_facts: str = ""
    # Curation
    retained: bool = False
    bloc_assigned: str = ""
    final_score: float = 0.0
    rejection_reason: str = ""
    # Publication
    item_number: int = 0


@dataclass
class AuditTrail:
    """Collecteur de données d'audit pour l'ensemble du pipeline."""

    # Paramètres du run
    run_date: datetime = field(default_factory=datetime.now)
    month: str = ""
    theme_id: str = ""
    theme_name: str = ""
    partner_name: str = ""
    days_back: int = 30
    model_used: str = ""

    # Collecte
    source_logs: List[SourceLog] = field(default_factory=list)

    # Analyse
    article_logs: Dict[str, ArticleLog] = field(default_factory=dict)
    analysis_errors: List[Dict[str, str]] = field(default_factory=list)
    api_calls_count: int = 0
    total_tokens_estimate: int = 0

    # Curation
    filter_stats: Dict[str, int] = field(default_factory=dict)
    dedup_pairs: List[Dict[str, str]] = field(default_factory=list)

    # Génération
    editorial_word_count: int = 0
    editorial_thesis: str = ""
    chiffre_du_mois: str = ""
    hashtags: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)

    # ──────────────────────────────────────────────
    # Méthodes de logging
    # ──────────────────────────────────────────────

    def log_run_params(self, month: str, theme_id: str, theme_name: str,
                       partner_name: str, days_back: int, model: str):
        """Log les paramètres du run."""
        self.month = month
        self.theme_id = theme_id or ""
        self.theme_name = theme_name or ""
        self.partner_name = partner_name or "Olivier Dupin"
        self.days_back = days_back
        self.model_used = model

    def log_source(self, name: str, url: str, status: str,
                   articles_count: int = 0, error_message: str = ""):
        """Log le résultat d'une source de collecte."""
        self.source_logs.append(SourceLog(
            name=name, url=url, status=status,
            articles_count=articles_count, error_message=error_message
        ))

    def log_article_collected(self, article):
        """Log un article collecté (objet Article du collector)."""
        log = ArticleLog(
            article_id=article.id,
            title_original=article.title,
            source=article.source,
            url=article.url,
            published_date=article.published_date,
            category_source=article.category,
        )
        self.article_logs[article.id] = log

    def log_article_analyzed(self, analyzed_article):
        """Log les résultats d'analyse d'un article."""
        aid = analyzed_article.article.id
        if aid not in self.article_logs:
            self.log_article_collected(analyzed_article.article)

        log = self.article_logs[aid]
        log.title_fr = analyzed_article.title_fr or ""
        log.relevance_score = analyzed_article.relevance_score
        log.category_ai = analyzed_article.assigned_category
        log.newsletter_priority = analyzed_article.newsletter_priority
        log.sentiment = analyzed_article.sentiment
        log.summary = analyzed_article.ai_summary[:300] if analyzed_article.ai_summary else ""
        log.entities = ", ".join(analyzed_article.entities) if analyzed_article.entities else ""
        log.key_facts = " | ".join(analyzed_article.key_facts) if analyzed_article.key_facts else ""

    def log_analysis_error(self, article_title: str, error: str):
        """Log une erreur d'analyse."""
        self.analysis_errors.append({"title": article_title, "error": error})

    def log_api_call(self, tokens_estimate: int = 500):
        """Log un appel API Claude."""
        self.api_calls_count += 1
        self.total_tokens_estimate += tokens_estimate

    def log_curation_filter(self, filter_name: str, count: int):
        """Log un filtre de curation (nb articles retirés)."""
        self.filter_stats[filter_name] = count

    def log_article_retained(self, article_id: str, bloc: str, final_score: float, item_number: int):
        """Log un article retenu dans la newsletter."""
        if article_id in self.article_logs:
            log = self.article_logs[article_id]
            log.retained = True
            log.bloc_assigned = bloc
            log.final_score = final_score
            log.item_number = item_number

    def log_article_rejected(self, article_id: str, reason: str):
        """Log un article rejeté lors de la curation."""
        if article_id in self.article_logs:
            self.article_logs[article_id].rejection_reason = reason

    def log_generation(self, editorial: str, chiffre: Optional[Dict],
                       hashtags: List[str], output_files: List[str]):
        """Log les résultats de génération."""
        self.editorial_word_count = len(editorial.split()) if editorial else 0
        # Extraire la thèse (première phrase)
        if editorial:
            first_sentence = editorial.split(".")[0]
            self.editorial_thesis = first_sentence[:150]
        self.chiffre_du_mois = chiffre.get("value", "") if chiffre else ""
        self.hashtags = hashtags or []
        self.output_files = output_files or []

    # ──────────────────────────────────────────────
    # Métriques de qualité
    # ──────────────────────────────────────────────

    def compute_quality_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques de qualité de la newsletter."""
        retained = [a for a in self.article_logs.values() if a.retained]
        all_analyzed = list(self.article_logs.values())

        if not retained:
            return {"score_global": 0}

        # Diversité sources
        sources = [a.source for a in retained]
        source_diversity = len(set(sources)) / len(sources) if sources else 0

        # Diversité géographique (heuristique sur les sources)
        fr_sources = {"les echos", "l'agefi", "la tribune", "mind fintech",
                      "c'est pas mon idée", "amf", "acpr", "revue banque",
                      "option finance", "france fintech", "banque de france"}
        eu_sources = {"ecb", "bce", "eba", "finextra"}

        fr_count = sum(1 for a in retained if any(fs in a.source.lower() for fs in fr_sources))
        eu_count = sum(1 for a in retained if any(es in a.source.lower() for es in eu_sources))
        intl_count = len(retained) - fr_count - eu_count

        # % articles avec au moins 1 chiffre
        digit_pattern = re.compile(r'\d+[\.,]?\d*\s*(%|M€|Md€|Mds|M\$|Md\$|bps|pts|milliard|million)')
        articles_with_numbers = sum(
            1 for a in retained
            if digit_pattern.search(a.summary)
        )
        pct_with_numbers = articles_with_numbers / len(retained) * 100 if retained else 0

        # Couverture thématique
        if self.theme_id:
            on_theme = sum(1 for a in retained if a.bloc_assigned == "essentiel")
            pct_on_theme = on_theme / len(retained) * 100
        else:
            pct_on_theme = 100

        # Score moyen de pertinence
        avg_score = sum(a.relevance_score for a in retained) / len(retained)

        # Volume mots (résumés)
        total_words = sum(len(a.summary.split()) for a in retained)
        total_words += self.editorial_word_count

        # Score global composite (0-100)
        score = min(100, int(
            source_diversity * 20 +  # 0-20 pts
            min(pct_with_numbers, 100) * 0.2 +  # 0-20 pts
            min(avg_score / 10, 1) * 20 +  # 0-20 pts
            min(len(retained) / 15, 1) * 20 +  # 0-20 pts (volume)
            (1 if self.editorial_word_count >= 200 else 0.5) * 20  # 0-20 pts
        ))

        return {
            "score_global": score,
            "nb_articles_retenus": len(retained),
            "nb_articles_analyses": len(all_analyzed),
            "diversite_sources": f"{source_diversity:.0%}",
            "nb_sources_distinctes": len(set(sources)),
            "geo_france": fr_count,
            "geo_europe": eu_count,
            "geo_international": intl_count,
            "pct_avec_chiffres": f"{pct_with_numbers:.0f}%",
            "score_pertinence_moyen": f"{avg_score:.1f}/10",
            "volume_mots_total": total_words,
            "editorial_mots": self.editorial_word_count,
            "appels_api": self.api_calls_count,
            "tokens_estimes": self.total_tokens_estimate,
            "cout_estime_usd": f"${self.total_tokens_estimate * 0.000003:.2f}",
        }

    # ──────────────────────────────────────────────
    # Export Excel
    # ──────────────────────────────────────────────

    def _style_header_row(self, ws, row: int, max_col: int):
        """Applique le style header à une ligne."""
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = THIN_BORDER

    def _style_data_cell(self, ws, row: int, col: int, wrap: bool = False):
        """Applique le style standard à une cellule."""
        cell = ws.cell(row=row, column=col)
        cell.font = Font(name="Calibri", size=10)
        cell.alignment = Alignment(vertical="top", wrap_text=wrap)
        cell.border = THIN_BORDER

    def _auto_width(self, ws, min_width: int = 10, max_width: int = 50):
        """Ajuste la largeur des colonnes automatiquement."""
        for col_cells in ws.columns:
            col_letter = get_column_letter(col_cells[0].column)
            max_len = max(
                (len(str(cell.value or "")) for cell in col_cells),
                default=min_width
            )
            ws.column_dimensions[col_letter].width = min(max(max_len + 2, min_width), max_width)

    def _write_synthese(self, wb: Workbook):
        """Onglet 1 : Synthèse."""
        ws = wb.active
        ws.title = "Synthèse"

        # Titre
        ws.merge_cells("A1:D1")
        title_cell = ws["A1"]
        title_cell.value = f"AUDIT TRAIL — Newsletter {self.month}"
        title_cell.font = Font(name="Calibri", bold=True, size=16, color="1A2A3A")
        title_cell.alignment = Alignment(horizontal="left")

        ws.merge_cells("A2:D2")
        ws["A2"].value = f"Généré le {self.run_date.strftime('%d/%m/%Y à %H:%M')}"
        ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="6B7280")

        # Paramètres du run
        row = 4
        ws.cell(row=row, column=1, value="PARAMÈTRES DU RUN")
        ws.cell(row=row, column=1).font = SUBHEADER_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.merge_cells(f"A{row}:D{row}")

        params = [
            ("Mois", self.month),
            ("Thème", f"{self.theme_name} ({self.theme_id})" if self.theme_id else "Aucun"),
            ("Partner signataire", self.partner_name),
            ("Période de collecte", f"{self.days_back} jours"),
            ("Modèle Claude", self.model_used),
        ]
        for label, value in params:
            row += 1
            ws.cell(row=row, column=1, value=label).font = Font(name="Calibri", bold=True, size=10)
            ws.cell(row=row, column=2, value=value).font = Font(name="Calibri", size=10)

        # Métriques de qualité
        row += 2
        ws.cell(row=row, column=1, value="MÉTRIQUES DE QUALITÉ")
        ws.cell(row=row, column=1).font = SUBHEADER_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.merge_cells(f"A{row}:D{row}")

        metrics = self.compute_quality_metrics()
        for label, value in metrics.items():
            row += 1
            label_display = label.replace("_", " ").title()
            ws.cell(row=row, column=1, value=label_display).font = Font(name="Calibri", bold=True, size=10)
            cell = ws.cell(row=row, column=2, value=str(value))
            cell.font = Font(name="Calibri", size=10)

            # Colorer le score global
            if label == "score_global":
                if value >= 75:
                    cell.fill = GOOD_FILL
                elif value >= 50:
                    cell.fill = WARN_FILL
                else:
                    cell.fill = BAD_FILL

        # Pipeline résumé
        row += 2
        ws.cell(row=row, column=1, value="RÉSUMÉ PIPELINE")
        ws.cell(row=row, column=1).font = SUBHEADER_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.merge_cells(f"A{row}:D{row}")

        pipeline = [
            ("Sources interrogées", len(self.source_logs)),
            ("Sources OK", sum(1 for s in self.source_logs if s.status == "OK")),
            ("Sources en erreur", sum(1 for s in self.source_logs if s.status != "OK")),
            ("Articles collectés", sum(s.articles_count for s in self.source_logs)),
            ("Articles analysés", len(self.article_logs)),
            ("Articles retenus", sum(1 for a in self.article_logs.values() if a.retained)),
            ("Fichiers générés", len(self.output_files)),
        ]
        for label, value in pipeline:
            row += 1
            ws.cell(row=row, column=1, value=label).font = Font(name="Calibri", bold=True, size=10)
            ws.cell(row=row, column=2, value=value).font = Font(name="Calibri", size=10)

        # Filtres de curation
        if self.filter_stats:
            row += 2
            ws.cell(row=row, column=1, value="FILTRES DE CURATION")
            ws.cell(row=row, column=1).font = SUBHEADER_FONT
            ws.cell(row=row, column=1).fill = SUBHEADER_FILL
            ws.merge_cells(f"A{row}:D{row}")

            for filter_name, count in self.filter_stats.items():
                row += 1
                ws.cell(row=row, column=1, value=filter_name).font = Font(name="Calibri", size=10)
                ws.cell(row=row, column=2, value=f"{count} articles retirés").font = Font(name="Calibri", size=10)

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 40
        ws.column_dimensions["C"].width = 20
        ws.column_dimensions["D"].width = 20

    def _write_collecte(self, wb: Workbook):
        """Onglet 2 : Collecte."""
        ws = wb.create_sheet("Collecte")

        headers = ["Source", "URL", "Statut", "Articles collectés", "Erreur"]
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        self._style_header_row(ws, 1, len(headers))

        for row, src in enumerate(self.source_logs, 2):
            ws.cell(row=row, column=1, value=src.name)
            ws.cell(row=row, column=2, value=src.url)
            status_cell = ws.cell(row=row, column=3, value=src.status)
            ws.cell(row=row, column=4, value=src.articles_count)
            ws.cell(row=row, column=5, value=src.error_message)

            # Colorer le statut
            if src.status == "OK":
                status_cell.fill = GOOD_FILL
            else:
                status_cell.fill = BAD_FILL

            for col in range(1, len(headers) + 1):
                self._style_data_cell(ws, row, col)

        self._auto_width(ws)

    def _write_articles_analyses(self, wb: Workbook):
        """Onglet 3 : Articles analysés."""
        ws = wb.create_sheet("Articles analysés")

        headers = [
            "ID", "Titre original", "Titre FR", "Source", "Date",
            "Catégorie (source)", "Catégorie (IA)", "Score pertinence",
            "Priorité", "Sentiment", "Entités", "Résumé IA"
        ]
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        self._style_header_row(ws, 1, len(headers))

        # Trier par score décroissant
        sorted_articles = sorted(
            self.article_logs.values(),
            key=lambda a: a.relevance_score,
            reverse=True
        )

        for row, a in enumerate(sorted_articles, 2):
            ws.cell(row=row, column=1, value=a.article_id[:12])
            ws.cell(row=row, column=2, value=a.title_original[:80])
            ws.cell(row=row, column=3, value=a.title_fr[:80])
            ws.cell(row=row, column=4, value=a.source)
            ws.cell(row=row, column=5, value=a.published_date.strftime('%d/%m/%Y') if a.published_date else "")
            ws.cell(row=row, column=6, value=a.category_source)
            ws.cell(row=row, column=7, value=a.category_ai)

            score_cell = ws.cell(row=row, column=8, value=a.relevance_score)
            if a.relevance_score >= 7:
                score_cell.fill = GOOD_FILL
            elif a.relevance_score >= 5:
                score_cell.fill = WARN_FILL
            else:
                score_cell.fill = BAD_FILL

            ws.cell(row=row, column=9, value=a.newsletter_priority)
            ws.cell(row=row, column=10, value=a.sentiment)
            ws.cell(row=row, column=11, value=a.entities[:60])
            ws.cell(row=row, column=12, value=a.summary[:200])

            for col in range(1, len(headers) + 1):
                self._style_data_cell(ws, row, col, wrap=(col == 12))

        self._auto_width(ws)

    def _write_curation(self, wb: Workbook):
        """Onglet 4 : Curation (retenu/rejeté avec raisons)."""
        ws = wb.create_sheet("Curation")

        headers = [
            "Titre FR", "Source", "Score IA", "Score final",
            "Retenu", "Bloc assigné", "N°", "Raison exclusion"
        ]
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        self._style_header_row(ws, 1, len(headers))

        # Trier : retenus en premier (par numéro), puis rejetés (par score desc)
        retained = sorted(
            [a for a in self.article_logs.values() if a.retained],
            key=lambda a: a.item_number
        )
        rejected = sorted(
            [a for a in self.article_logs.values() if not a.retained],
            key=lambda a: a.relevance_score,
            reverse=True
        )

        row = 2
        for a in retained + rejected:
            ws.cell(row=row, column=1, value=(a.title_fr or a.title_original)[:80])
            ws.cell(row=row, column=2, value=a.source)
            ws.cell(row=row, column=3, value=a.relevance_score)
            ws.cell(row=row, column=4, value=round(a.final_score, 1))

            retained_cell = ws.cell(row=row, column=5, value="OUI" if a.retained else "NON")
            retained_cell.fill = GOOD_FILL if a.retained else BAD_FILL
            retained_cell.font = Font(name="Calibri", bold=True, size=10)

            ws.cell(row=row, column=6, value=a.bloc_assigned)
            ws.cell(row=row, column=7, value=a.item_number if a.retained else "")
            ws.cell(row=row, column=8, value=a.rejection_reason)

            for col in range(1, len(headers) + 1):
                self._style_data_cell(ws, row, col)
            row += 1

        self._auto_width(ws)

    def _write_newsletter_finale(self, wb: Workbook):
        """Onglet 5 : Newsletter finale (articles publiés dans l'ordre)."""
        ws = wb.create_sheet("Newsletter finale")

        headers = [
            "N°", "Bloc", "Titre", "Source", "Date", "Lien",
            "Résumé IA", "Score final"
        ]
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        self._style_header_row(ws, 1, len(headers))

        bloc_names = {
            "essentiel": "L'essentiel",
            "strategies_marches": "Stratégies & marchés",
            "nouveaux_modeles": "Nouveaux modèles",
            "regulation": "Régulation & supervision",
        }

        retained = sorted(
            [a for a in self.article_logs.values() if a.retained],
            key=lambda a: a.item_number
        )

        for row, a in enumerate(retained, 2):
            ws.cell(row=row, column=1, value=f"#{a.item_number}")
            ws.cell(row=row, column=2, value=bloc_names.get(a.bloc_assigned, a.bloc_assigned))
            ws.cell(row=row, column=3, value=a.title_fr or a.title_original)
            ws.cell(row=row, column=4, value=a.source)
            ws.cell(row=row, column=5, value=a.published_date.strftime('%d/%m/%Y') if a.published_date else "")
            ws.cell(row=row, column=6, value=a.url)
            ws.cell(row=row, column=7, value=a.summary[:300])
            ws.cell(row=row, column=8, value=round(a.final_score, 1))

            for col in range(1, len(headers) + 1):
                self._style_data_cell(ws, row, col, wrap=(col == 7))

        self._auto_width(ws)

    def _write_qualite(self, wb: Workbook):
        """Onglet 6 : Métriques de qualité."""
        ws = wb.create_sheet("Qualité")

        # Titre
        ws.merge_cells("A1:C1")
        ws["A1"].value = "MÉTRIQUES DE QUALITÉ"
        ws["A1"].font = Font(name="Calibri", bold=True, size=14, color="1A2A3A")

        metrics = self.compute_quality_metrics()

        row = 3
        headers = ["Métrique", "Valeur", "Seuil"]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        self._style_header_row(ws, row, len(headers))

        thresholds = {
            "score_global": ("≥ 75", lambda v: v >= 75),
            "nb_articles_retenus": ("≥ 12", lambda v: v >= 12),
            "diversite_sources": ("≥ 60%", lambda v: float(v.strip('%')) / 100 >= 0.6 if isinstance(v, str) else v >= 0.6),
            "pct_avec_chiffres": ("≥ 70%", lambda v: int(v.strip('%')) >= 70 if isinstance(v, str) else v >= 70),
            "editorial_mots": ("250-300", lambda v: 200 <= v <= 350),
        }

        for key, value in metrics.items():
            row += 1
            label = key.replace("_", " ").title()
            ws.cell(row=row, column=1, value=label).font = Font(name="Calibri", bold=True, size=10)
            value_cell = ws.cell(row=row, column=2, value=str(value))
            value_cell.font = Font(name="Calibri", size=10)

            if key in thresholds:
                threshold_label, check_fn = thresholds[key]
                ws.cell(row=row, column=3, value=threshold_label).font = Font(name="Calibri", size=10, color="6B7280")
                try:
                    if check_fn(value):
                        value_cell.fill = GOOD_FILL
                    else:
                        value_cell.fill = WARN_FILL
                except (ValueError, TypeError):
                    pass

            for col in range(1, len(headers) + 1):
                self._style_data_cell(ws, row, col)

        # Distribution par bloc
        row += 2
        ws.cell(row=row, column=1, value="DISTRIBUTION PAR BLOC")
        ws.cell(row=row, column=1).font = SUBHEADER_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.merge_cells(f"A{row}:C{row}")

        bloc_counts = Counter(
            a.bloc_assigned for a in self.article_logs.values() if a.retained
        )
        bloc_names = {
            "essentiel": "L'essentiel",
            "strategies_marches": "Stratégies & marchés",
            "nouveaux_modeles": "Nouveaux modèles",
            "regulation": "Régulation & supervision",
        }
        for bloc_id, name in bloc_names.items():
            row += 1
            ws.cell(row=row, column=1, value=name).font = Font(name="Calibri", size=10)
            ws.cell(row=row, column=2, value=bloc_counts.get(bloc_id, 0)).font = Font(name="Calibri", size=10)

        # Distribution par source
        row += 2
        ws.cell(row=row, column=1, value="DISTRIBUTION PAR SOURCE")
        ws.cell(row=row, column=1).font = SUBHEADER_FONT
        ws.cell(row=row, column=1).fill = SUBHEADER_FILL
        ws.merge_cells(f"A{row}:C{row}")

        source_counts = Counter(
            a.source for a in self.article_logs.values() if a.retained
        )
        for source, count in source_counts.most_common():
            row += 1
            ws.cell(row=row, column=1, value=source).font = Font(name="Calibri", size=10)
            ws.cell(row=row, column=2, value=count).font = Font(name="Calibri", size=10)

        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 15

    def save_excel(self, output_dir: str = "output/audit") -> str:
        """Génère et sauvegarde le fichier Excel d'audit trail."""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m")
        filename = f"audit-trail-{timestamp}.xlsx"
        filepath = os.path.join(output_dir, filename)

        console.print(f"\n[bold blue]📊 Génération de l'audit trail Excel...[/bold blue]")

        wb = Workbook()

        self._write_synthese(wb)
        self._write_collecte(wb)
        self._write_articles_analyses(wb)
        self._write_curation(wb)
        self._write_newsletter_finale(wb)
        self._write_qualite(wb)

        wb.save(filepath)
        console.print(f"[bold green]✅ Audit trail sauvegardé : {filepath}[/bold green]")

        return filepath
