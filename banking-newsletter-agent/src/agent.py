#!/usr/bin/env python3
"""
Agent Principal - Newsletter Bancaire
Banking Newsletter Agent - Ares & Co

Point d'entrée principal qui orchestre :
1. Collecte des articles
2. Analyse avec Claude
3. Curation et sélection
4. Génération de la newsletter
"""

import argparse
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Charger les variables d'environnement depuis .env (chemin explicite)
from dotenv import load_dotenv
# Charger .env depuis le dossier parent de src/ (racine du projet)
env_path = Path(__file__).parent.parent / '.env'
loaded = load_dotenv(dotenv_path=env_path)

# Debug: afficher si le fichier .env a été trouvé
if not loaded:
    print(f"[DEBUG] Fichier .env non trouvé à: {env_path.absolute()}")
    print(f"[DEBUG] Créez ce fichier avec: ANTHROPIC_API_KEY=votre-clé")
elif not os.environ.get("ANTHROPIC_API_KEY"):
    print(f"[DEBUG] Fichier .env chargé depuis: {env_path.absolute()}")
    print(f"[DEBUG] Mais ANTHROPIC_API_KEY n'est pas définie dans le fichier")

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Ajouter le dossier src au path
sys.path.insert(0, str(Path(__file__).parent))

from collector import Collector, Article
from analyzer import Analyzer, AnalyzedArticle
from curator import Curator, CuratedSelection
from writer import NewsletterWriter

console = Console()


class BankingNewsletterAgent:
    """Agent principal orchestrant la génération de newsletter"""

    def __init__(
        self,
        config_path: str = "config/sources.yaml",
        api_key: Optional[str] = None,
        output_dir: str = "output/newsletters"
    ):
        self.config_path = config_path
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.output_dir = output_dir

        # Initialisation des modules
        self.collector = Collector(config_path)
        self.analyzer = None  # Initialisé si API key disponible
        self.curator = Curator(
            min_relevance_score=3.0,  # Seuil bas pour garder plus d'articles
            max_articles_per_category=5,  # Plus d'articles par catégorie
            max_total_articles=15  # Top 15 pour sélectionner les 10 meilleurs
        )
        self.writer = NewsletterWriter(api_key=self.api_key)

        if self.api_key:
            self.analyzer = Analyzer(api_key=self.api_key)

    def _display_banner(self, month: str):
        """Affiche la bannière de démarrage"""
        banner = f"""
[bold blue]╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   📰  BANKING NEWSLETTER AGENT                                 ║
║       Ares & Co - Conseil en Stratégie                         ║
║                                                                ║
║   Génération automatisée de la newsletter bancaire             ║
║   Période : {month:^20}                            ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝[/bold blue]
"""
        console.print(banner)

    def run(
        self,
        month: Optional[str] = None,
        days_back: int = 30,
        output_format: str = "markdown",
        max_articles: Optional[int] = None,
        skip_analysis: bool = False,
        logo_url: Optional[str] = None
    ) -> dict:
        """
        Exécute le pipeline complet de génération de newsletter.

        Args:
            month: Mois de la newsletter (ex: "Février 2026")
            days_back: Nombre de jours à remonter pour la collecte
            output_format: Format de sortie ("markdown", "html", "both")
            max_articles: Limite d'articles à analyser (pour tests)
            skip_analysis: Sauter l'analyse IA (pour tests sans API)
            logo_url: URL du logo pour le HTML

        Returns:
            dict: Résultats de l'exécution
        """
        # Déterminer le mois (mois précédent = mois des actualités collectées)
        if month is None:
            from dateutil.relativedelta import relativedelta
            # La newsletter couvre le mois précédent (mois des actualités)
            last_month = datetime.now() - relativedelta(months=1)
            month = last_month.strftime("%B %Y").capitalize()
            # Traduction française
            month_translations = {
                "January": "Janvier", "February": "Février", "March": "Mars",
                "April": "Avril", "May": "Mai", "June": "Juin",
                "July": "Juillet", "August": "Août", "September": "Septembre",
                "October": "Octobre", "November": "Novembre", "December": "Décembre"
            }
            for en, fr in month_translations.items():
                month = month.replace(en, fr)

        self._display_banner(month)

        results = {
            "month": month,
            "status": "success",
            "articles_collected": 0,
            "articles_analyzed": 0,
            "articles_selected": 0,
            "output_files": []
        }

        try:
            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 1 : COLLECTE
            # ═══════════════════════════════════════════════════════════
            console.print(Panel("[bold]ÉTAPE 1/4 : COLLECTE[/bold]", style="blue"))

            articles = self.collector.collect_all(days_back=days_back)
            results["articles_collected"] = len(articles)

            if not articles:
                console.print("[yellow]⚠ Aucun article collecté. Vérifiez les sources.[/yellow]")
                results["status"] = "no_articles"
                return results

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 2 : ANALYSE
            # ═══════════════════════════════════════════════════════════
            console.print(Panel("[bold]ÉTAPE 2/4 : ANALYSE[/bold]", style="blue"))

            if skip_analysis or not self.analyzer:
                if not self.analyzer:
                    console.print("[yellow]⚠ Pas de clé API Claude. Analyse basique.[/yellow]")

                # Analyse basique sans IA - scores plus généreux
                analyzed_articles = []
                for a in articles:
                    # Score basé sur la priorité de la source
                    if a.priority == 1:
                        score = 8.0
                    elif a.priority == 2:
                        score = 6.5
                    else:
                        score = 5.0

                    # Résumé basique
                    summary = a.summary[:300] if a.summary else (a.content[:300] if a.content else a.title)

                    analyzed_articles.append(AnalyzedArticle(
                        article=a,
                        ai_summary=summary,
                        relevance_score=score,
                        assigned_category=a.category,
                        key_facts=[],
                        entities=[],
                        sentiment="neutral",
                        newsletter_priority=a.priority,
                        title_fr=a.title  # Titre original (pas de traduction sans IA)
                    ))
            else:
                # Analyse avec Claude API
                articles_to_analyze = articles[:max_articles] if max_articles else articles
                analyzed_articles = self.analyzer.analyze_batch_optimized(
                    articles_to_analyze,
                    batch_size=5
                )

            results["articles_analyzed"] = len(analyzed_articles)

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 3 : CURATION
            # ═══════════════════════════════════════════════════════════
            console.print(Panel("[bold]ÉTAPE 3/4 : CURATION[/bold]", style="blue"))

            selection = self.curator.curate(analyzed_articles)
            results["articles_selected"] = selection.total_selected

            if selection.total_selected == 0:
                console.print("[yellow]⚠ Aucun article sélectionné après curation.[/yellow]")
                results["status"] = "no_selection"
                return results

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 4 : GÉNÉRATION
            # ═══════════════════════════════════════════════════════════
            console.print(Panel("[bold]ÉTAPE 4/4 : GÉNÉRATION[/bold]", style="blue"))

            # Générer l'éditorial une seule fois
            editorial = self.writer.generate_editorial(selection, month)

            # Markdown
            if output_format in ("markdown", "both"):
                md_content = self.writer.generate_markdown(selection, month, editorial)
                md_path = self.writer.save_markdown(md_content, self.output_dir)
                results["output_files"].append(md_path)

            # HTML
            if output_format in ("html", "both"):
                html_content = self.writer.generate_html(
                    selection, month, editorial, logo_url
                )
                html_path = self.writer.save_html(html_content, self.output_dir)
                results["output_files"].append(html_path)

            # ═══════════════════════════════════════════════════════════
            # RÉSUMÉ FINAL
            # ═══════════════════════════════════════════════════════════
            self._display_summary(results)

        except Exception as e:
            console.print(f"\n[bold red]❌ Erreur : {str(e)}[/bold red]")
            results["status"] = "error"
            results["error"] = str(e)
            raise

        return results

    def _display_summary(self, results: dict):
        """Affiche le résumé final"""
        summary = f"""
## Génération terminée

- **Articles collectés** : {results['articles_collected']}
- **Articles analysés** : {results['articles_analyzed']}
- **Articles sélectionnés** : {results['articles_selected']}

### Fichiers générés :
"""
        for f in results["output_files"]:
            summary += f"\n- `{f}`"

        console.print(Panel(Markdown(summary), title="[bold green]✅ SUCCÈS[/bold green]", style="green"))

    def run_interactive(self):
        """Mode interactif avec prompts utilisateur"""
        console.print("\n[bold]🎯 Mode interactif[/bold]\n")

        # Demander les paramètres
        month = console.input("[cyan]Mois de la newsletter[/cyan] (ex: Février 2026) : ") or None
        days = console.input("[cyan]Jours à remonter[/cyan] (défaut: 30) : ") or "30"
        format_choice = console.input("[cyan]Format[/cyan] (markdown/html/both, défaut: markdown) : ") or "markdown"

        return self.run(
            month=month,
            days_back=int(days),
            output_format=format_choice
        )


def main():
    """Point d'entrée CLI"""
    parser = argparse.ArgumentParser(
        description="Agent de génération de newsletter bancaire - Ares & Co",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  python agent.py                           # Génération standard
  python agent.py --month "Février 2026"    # Mois spécifique
  python agent.py --format both             # Markdown + HTML
  python agent.py --days 14                 # 2 dernières semaines
  python agent.py --interactive             # Mode interactif
  python agent.py --test                    # Test sans API
        """
    )

    parser.add_argument(
        "--month", "-m",
        help="Mois de la newsletter (ex: 'Février 2026')"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="Nombre de jours à remonter (défaut: 30)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "html", "both"],
        default="markdown",
        help="Format de sortie (défaut: markdown)"
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        help="Limite d'articles à analyser (pour tests)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output/newsletters",
        help="Dossier de sortie"
    )
    parser.add_argument(
        "--config", "-c",
        default="config/sources.yaml",
        help="Fichier de configuration des sources"
    )
    parser.add_argument(
        "--logo-url",
        help="URL du logo pour le HTML"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Mode interactif"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Mode test (sans analyse IA)"
    )

    args = parser.parse_args()

    # Changer vers le dossier du projet
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)

    # Créer et exécuter l'agent
    agent = BankingNewsletterAgent(
        config_path=args.config,
        output_dir=args.output
    )

    if args.interactive:
        results = agent.run_interactive()
    else:
        results = agent.run(
            month=args.month,
            days_back=args.days,
            output_format=args.format,
            max_articles=args.max_articles,
            skip_analysis=args.test,
            logo_url=args.logo_url
        )

    # Code de sortie
    sys.exit(0 if results["status"] == "success" else 1)


if __name__ == "__main__":
    main()
