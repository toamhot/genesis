"""
Module de rédaction de la newsletter - V3
Banking Newsletter Agent - Ares & Co

Ce module gère :
- La génération de l'éditorial (250-300 mots, 4 parties)
- Le formatage des items par bloc
- La génération Markdown et HTML V3
- L'export des fichiers

V3 : 5 blocs éditoriaux (Éditorial, Essentiel, Stratégies, Modèles, Régulation)
"""

import os
import re
from datetime import datetime
from typing import Optional, Dict, List
import anthropic
from jinja2 import Template
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console

from curator import CuratedSelection
from analyzer import AnalyzedArticle
from persona import (
    get_editorial_system_prompt,
    get_bloc_prompt,
    SENIOR_PARTNER_PERSONA,
)

console = Console()


class NewsletterWriter:
    """Rédacteur de newsletter V3 — 5 blocs éditoriaux"""

    BLOC_NAMES = {
        "essentiel": "L'essentiel",
        "strategies_marches": "Stratégies & marchés",
        "nouveaux_modeles": "Nouveaux modèles",
        "regulation": "Régulation & supervision",
    }

    BLOC_ORDER = ["essentiel", "strategies_marches", "nouveaux_modeles", "regulation"]

    # Gouvernance éditoriale
    DEFAULT_PARTNER = "Olivier Dupin"

    # Prompt éditorial V3
    EDITORIAL_SYSTEM_PROMPT = get_editorial_system_prompt()

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_claude(self, system: str, prompt: str, max_tokens: int = 1024) -> str:
        """Appelle Claude API"""
        if not self.client:
            console.print("[yellow]⚠ Pas de client Claude API[/yellow]")
            return "[Contenu à rédiger manuellement - Clé API manquante]"

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            console.print(f"[red]✗ Erreur API Claude: {str(e)[:100]}[/red]")
            return f"[Erreur génération: {str(e)[:50]}]"

    def generate_editorial(
        self,
        selection: CuratedSelection,
        month: str,
        tension_point: Optional[str] = None,
        partner_name: Optional[str] = None
    ) -> str:
        """
        Génère l'éditorial V3 — 4 parties obligatoires, 250-300 mots.

        Args:
            selection: La sélection curée d'articles
            month: Le mois de la newsletter
            tension_point: Point de tension du mois (optionnel, déduit des articles si absent)
            partner_name: Nom du Partner signataire
        """
        console.print("\n[bold blue]✍️  Génération de l'éditorial V3...[/bold blue]")

        partner = partner_name or self.DEFAULT_PARTNER

        # Préparer le contexte — tous les articles sélectionnés avec leurs titres
        articles_summary = "\n".join([
            f"- {a.title_fr if a.title_fr else a.article.title}: {a.ai_summary}"
            for a in selection.top_articles
        ])

        # Contexte par bloc
        blocs_context = ""
        if hasattr(selection, 'blocs') and selection.blocs:
            for bloc_id in self.BLOC_ORDER:
                articles = selection.blocs.get(bloc_id, [])
                if articles:
                    bloc_name = self.BLOC_NAMES.get(bloc_id, bloc_id)
                    titles = "\n".join([f"  - {a.title_fr or a.article.title}" for a in articles])
                    blocs_context += f"\n{bloc_name}:\n{titles}\n"

        tension_instruction = ""
        if tension_point:
            tension_instruction = f"\nPOINT DE TENSION DU MOIS (imposé) : {tension_point}\n"

        prompt = f"""Tu es un Senior Partner d'un cabinet de conseil en stratégie spécialisé services financiers
(profil McKinsey/BCG/Oliver Wyman, 25 ans d'expérience, marchés FR/EU/US).
Tu rédiges l'éditorial d'une newsletter mensuelle adressée aux DG et COMEX de banques françaises.
{tension_instruction}
Articles sélectionnés pour cette édition :
{articles_summary}

Distribution par bloc :
{blocs_context}

Structure OBLIGATOIRE :
1. Accroche (1-2 phrases) : formule la tension comme une affirmation provocante
2. Constat ancré (2-3 phrases) : 1 chiffre qui fait mal, ancré FR/EU
3. Analyse (4-6 phrases) : 2-3 dynamiques structurantes, connexions inattendues
4. Conviction (1-2 phrases) : thèse tranchée, commencer par "**Notre conviction :**"

Règles absolues :
- 250-300 mots maximum
- Pas de "paradigm shift", "best practices", "synergies"
- Pas de conditionnel sauf citation
- 1 seul chiffre dans le constat, sourcé
- Première personne du pluriel ("notre conviction", "nous observons")
- Terminer par la signature : — {partner}, Partner, Ares & Co
- JAMAIS de liste à puces — tout en prose fluide
- Pas de titre ni de préambule — commence directement par l'accroche

Rédige directement l'éditorial."""

        editorial = self._call_claude(self.EDITORIAL_SYSTEM_PROMPT, prompt)

        # Convertir le markdown en HTML (gras)
        editorial = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', editorial)

        console.print("[green]✓ Éditorial V3 généré[/green]")
        return editorial

    def generate_terrain(
        self,
        selection: CuratedSelection,
        month: str
    ) -> dict:
        """Génère la section "Terrain Ares & Co" — mini-cas anonymisé."""
        console.print("\n[bold blue]💼 Génération du Terrain Ares & Co...[/bold blue]")

        if not self.client:
            return {
                "title": "Retour d'expérience terrain",
                "problem": "[À compléter]",
                "approach": "[À compléter]",
                "results": "[À compléter]"
            }

        theme_name = getattr(selection, 'theme_name', None) or "transformation bancaire"

        articles_context = "\n".join([
            f"- {a.title_fr if a.title_fr else a.article.title}"
            for a in selection.top_articles[:6]
        ])

        prompt = f"""Génère un mini-cas "TERRAIN ARES & CO" pour la newsletter bancaire de {month}.

THÈME DU MOIS : {theme_name}

ARTICLES DE L'ÉDITION (pour contexte) :
{articles_context}

MISSION :
Imagine un cas de mission Ares & Co ANONYMISÉ et RÉALISTE qui illustre le thème du mois.

STRUCTURE STRICTE :
TITRE: [Titre court du cas]
---
PROBLÈME: [2-3 phrases — contexte, enjeux, chiffres]
---
APPROCHE: [2-3 phrases — méthodologie, phases, outils]
---
RÉSULTATS: [2-3 phrases — résultats quantifiés, KPIs]

RÈGLES :
- Client ANONYMISÉ ("une banque régionale", "un acteur majeur de la bancassurance")
- Chiffres CRÉDIBLES et PRÉCIS (%, M€, jours)
- Maximum 150 mots au total
- Lien ÉVIDENT avec le thème du mois"""

        response = self._call_claude(self.EDITORIAL_SYSTEM_PROMPT, prompt)

        terrain = {
            "title": "Retour d'expérience terrain",
            "problem": "",
            "approach": "",
            "results": ""
        }

        if "TITRE:" in response:
            parts = response.split("---")
            for part in parts:
                part = part.strip()
                if part.startswith("TITRE:"):
                    terrain["title"] = part.replace("TITRE:", "").strip()
                elif part.startswith("PROBLÈME:") or part.startswith("PROBLEME:"):
                    terrain["problem"] = part.replace("PROBLÈME:", "").replace("PROBLEME:", "").strip()
                elif part.startswith("APPROCHE:"):
                    terrain["approach"] = part.replace("APPROCHE:", "").strip()
                elif part.startswith("RÉSULTATS:") or part.startswith("RESULTATS:"):
                    terrain["results"] = part.replace("RÉSULTATS:", "").replace("RESULTATS:", "").strip()

        console.print(f"[green]✓ Terrain généré: {terrain['title'][:50]}...[/green]")
        return terrain

    def _compute_item_numbers(self, blocs: Dict[str, List]) -> Dict[str, List[int]]:
        """Calcule la numérotation continue des items à travers les blocs."""
        item_numbers = {}
        current_num = 1
        for bloc_id in self.BLOC_ORDER:
            articles = blocs.get(bloc_id, [])
            nums = list(range(current_num, current_num + len(articles)))
            item_numbers[bloc_id] = nums
            current_num += len(articles)
        return item_numbers

    def generate_markdown_v3(
        self,
        selection: CuratedSelection,
        month: str,
        editorial: Optional[str] = None,
        partner_name: Optional[str] = None,
        terrain: Optional[dict] = None
    ) -> str:
        """Génère la newsletter V3 au format Markdown."""
        console.print("\n[bold blue]📝 Génération du Markdown V3...[/bold blue]")

        partner = partner_name or self.DEFAULT_PARTNER

        if editorial is None:
            editorial = self.generate_editorial(selection, month, partner_name=partner)

        # Reconvertir HTML bold en markdown
        editorial_md = re.sub(r'<strong>(.+?)</strong>', r'**\1**', editorial)

        blocs = getattr(selection, 'blocs', {})
        item_numbers = self._compute_item_numbers(blocs)

        lines = []

        # Séparateur
        sep = "────────────────────────────────────────────────────────"

        # Header
        lines.append(f"# Newsletter Banque — {month}")
        lines.append("")
        lines.append("**Ares & Co** | Cabinet de conseil de Direction Générale")
        lines.append("")
        lines.append(sep)
        lines.append("")

        # Bloc 0 — Éditorial
        lines.append("## NOTRE ÉDITORIAL")
        lines.append("")
        lines.append(editorial_md)
        lines.append("")
        lines.append(f"— {partner}, Partner, Ares & Co")
        lines.append("")
        lines.append(sep)
        lines.append("")

        # Blocs 1-4
        bloc_titles = {
            "essentiel": "L'ESSENTIEL",
            "strategies_marches": "STRATÉGIES & MARCHÉS",
            "nouveaux_modeles": "NOUVEAUX MODÈLES",
            "regulation": "RÉGULATION & SUPERVISION",
        }

        for bloc_id in self.BLOC_ORDER:
            articles = blocs.get(bloc_id, [])
            if not articles:
                continue

            lines.append(f"## {bloc_titles.get(bloc_id, bloc_id.upper())}")
            lines.append("")

            nums = item_numbers.get(bloc_id, [])
            for i, article in enumerate(articles):
                num = nums[i] if i < len(nums) else i + 1
                title = article.title_fr if article.title_fr else article.article.title

                lines.append(f"**#{num}. {title}**")
                lines.append("")
                lines.append(article.ai_summary)
                lines.append("")

                # Source
                source_line = f"📰 {article.article.source}"
                if article.article.published_date:
                    source_line += f" | {article.article.published_date.strftime('%d/%m/%Y')}"
                lines.append(source_line)
                lines.append("")

            lines.append(sep)
            lines.append("")

        # Terrain (optionnel)
        if terrain and terrain.get("problem"):
            lines.append("## TERRAIN ARES & CO")
            lines.append("")
            lines.append(f"**{terrain.get('title', 'Retour terrain')}**")
            lines.append("")
            lines.append(f"**Problématique** → {terrain['problem']}")
            lines.append("")
            lines.append(f"**Approche** → {terrain['approach']}")
            lines.append("")
            lines.append(f"**Résultats** → {terrain['results']}")
            lines.append("")
            lines.append(sep)
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append("**Ares & Co** — Cabinet de conseil de Direction Générale")
        lines.append("")
        lines.append("contact@aresandco.com | +33 1 40 20 44 49")
        lines.append("")
        lines.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*")

        content = "\n".join(lines)
        console.print("[green]✓ Newsletter Markdown V3 générée[/green]")
        return content

    def generate_html_v3(
        self,
        selection: CuratedSelection,
        month: str,
        editorial: Optional[str] = None,
        terrain: Optional[dict] = None,
        partner_name: Optional[str] = None,
        logo_url: Optional[str] = None
    ) -> str:
        """
        Génère la newsletter V3 avec la structure 5 blocs :
        0. Notre éditorial (250-300 mots, 4 parties)
        1. L'essentiel (1-3 items)
        2. Stratégies & marchés (2-3 items)
        3. Nouveaux modèles (2-3 items)
        4. Régulation & supervision (2-3 items)
        + Terrain (optionnel)
        + CTA
        """
        from pathlib import Path

        console.print("\n[bold blue]🎨 Génération du HTML V3...[/bold blue]")

        partner = partner_name or self.DEFAULT_PARTNER

        if editorial is None:
            editorial = self.generate_editorial(selection, month, partner_name=partner)

        # Charger le template V3
        template_path = Path(__file__).parent / "templates" / "newsletter_v3.html"
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        template = Template(template_content)

        # Préparer les blocs
        blocs = getattr(selection, 'blocs', {})
        item_numbers = self._compute_item_numbers(blocs)

        theme_color = '#57AEE0'

        html = template.render(
            month=month,
            theme_color=theme_color,
            editorial=editorial,
            partner_name=partner,
            blocs=blocs,
            item_numbers=item_numbers,
            terrain=terrain,
            generation_date=datetime.now().strftime('%d/%m/%Y'),
            logo_url=logo_url or ""
        )

        total_items = sum(len(arts) for arts in blocs.values())
        console.print(f"[green]✓ Newsletter HTML V3 générée ({total_items} items dans 4 blocs)[/green]")
        return html

    # ──────────────────────────────────────────────────────────
    # Backward compatibility — V2 methods kept for transition
    # ──────────────────────────────────────────────────────────

    def generate_html_v2(
        self,
        selection,
        month: str,
        editorial: Optional[str] = None,
        ares_view: Optional[dict] = None,
        terrain: Optional[dict] = None,
        logo_url: Optional[str] = None
    ) -> str:
        """V2 compatibility wrapper — delegates to V3."""
        return self.generate_html_v3(
            selection=selection,
            month=month,
            editorial=editorial,
            terrain=terrain,
            logo_url=logo_url
        )

    def generate_ares_view(
        self,
        selection: CuratedSelection,
        month: str,
        partner_name: str = "Olivier Dupin"
    ) -> dict:
        """Deprecated — replaced by 'Notre lecture' in Bloc 3. Returns empty dict."""
        console.print("[dim]  → generate_ares_view() deprecated in V3 — 'Notre lecture' is in Bloc 3[/dim]")
        return {"topic": "", "content": "", "partner": partner_name}

    def generate_markdown(
        self,
        selection: CuratedSelection,
        month: str,
        editorial: Optional[str] = None
    ) -> str:
        """V2 compatibility wrapper — delegates to V3."""
        return self.generate_markdown_v3(
            selection=selection,
            month=month,
            editorial=editorial
        )

    def save_markdown(
        self,
        content: str,
        output_dir: str = "output/newsletters",
        filename: Optional[str] = None
    ) -> str:
        """Sauvegarde la newsletter en fichier Markdown"""
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m")
            filename = f"newsletter-banque-{timestamp}.md"

        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"\n[bold green]💾 Newsletter sauvegardée : {filepath}[/bold green]")
        return filepath

    def save_html(
        self,
        content: str,
        output_dir: str = "output/newsletters",
        filename: Optional[str] = None
    ) -> str:
        """Sauvegarde la newsletter en fichier HTML"""
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m")
            filename = f"newsletter-banque-{timestamp}.html"

        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"\n[bold green]💾 Newsletter HTML sauvegardée : {filepath}[/bold green]")
        return filepath


if __name__ == "__main__":
    from collector import Article
    from analyzer import AnalyzedArticle
    from curator import CuratedSelection

    test_selection = CuratedSelection(
        blocs={
            "essentiel": [
                AnalyzedArticle(
                    article=Article(
                        id="1", title="BCE : maintien des taux directeurs",
                        url="http://example.com", source="BCE",
                        category="regulateur", published_date=datetime.now(),
                        content="", summary="", priority=1
                    ),
                    ai_summary="La BCE a décidé de maintenir ses taux directeurs inchangés pour le troisième trimestre consécutif. Pour les banques françaises, cela prolonge la compression des marges sur les dépôts à vue.",
                    relevance_score=9.0,
                    assigned_category="monetary_policy",
                    key_facts=["Taux de dépôt : 2.00%"],
                    entities=["BCE"],
                    sentiment="neutral",
                    newsletter_priority=1
                )
            ],
            "strategies_marches": [],
            "nouveaux_modeles": [],
            "regulation": [],
        },
        top_articles=[],
        articles_by_category={},
        total_collected=10,
        total_selected=1
    )

    writer = NewsletterWriter()
    md = writer.generate_markdown_v3(test_selection, "Mars 2026")
    print(md)
