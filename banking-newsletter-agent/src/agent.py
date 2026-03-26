#!/usr/bin/env python3
"""
Agent Principal - Newsletter Bancaire V3
Banking Newsletter Agent - Ares & Co

Point d'entrée principal qui orchestre :
1. Collecte des articles
2. Analyse avec Claude
3. Curation et distribution dans 4 blocs éditoriaux
4. Génération de la newsletter (format V3)

V3 — Structure 5 blocs :
- Bloc 0 : Notre éditorial (250-300 mots, 4 parties obligatoires)
- Bloc 1 : L'essentiel (1-3 items liés à l'éditorial)
- Bloc 2 : Stratégies & marchés (2-3 items)
- Bloc 3 : Nouveaux modèles (2-3 items, avec "Notre lecture" optionnel)
- Bloc 4 : Régulation & supervision (2-3 items)
+ Terrain Ares & Co (optionnel)
+ CTA

Numérotation continue #1 à #20 max.
Volume cible : 2 500 à 3 500 mots (éditorial inclus).
"""

import argparse
import os
import sys
import json
import pickle
import signal
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Charger les variables d'environnement depuis .env (chemin explicite)
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'

# Gérer les problèmes d'encodage Windows (UTF-16 BOM)
try:
    loaded = load_dotenv(dotenv_path=env_path)
except UnicodeDecodeError:
    try:
        with open(env_path, 'r', encoding='utf-16') as f:
            content = f.read()
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        loaded = load_dotenv(dotenv_path=env_path)
    except Exception as e:
        print(f"[ERREUR] Impossible de lire .env: {e}")
        print("Créez un fichier .env en UTF-8 avec: ANTHROPIC_API_KEY=votre-clé")
        loaded = False

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
from newsapi_collector import collect_newsapi
from analyzer import Analyzer, AnalyzedArticle
from curator import Curator, CuratedSelection
from writer import NewsletterWriter
from audit_trail import AuditTrail

console = Console()


class BankingNewsletterAgent:
    """Agent principal orchestrant la génération de newsletter V3"""

    # Thèmes disponibles
    AVAILABLE_THEMES = [
        "growth_distribution",
        "customer_experience",
        "operational_performance",
        "demographic_transition",
        "retirement_savings",
        "risk_finance"
    ]

    def __init__(
        self,
        config_path: str = "config/sources.yaml",
        themes_config_path: str = "config/themes.yaml",
        api_key: Optional[str] = None,
        output_dir: str = "output/newsletters"
    ):
        self.config_path = config_path
        self.themes_config_path = themes_config_path
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.output_dir = output_dir

        # Charger la configuration des thèmes
        self.themes_config = self._load_themes_config()

        # Initialisation des modules
        self.collector = Collector(config_path)
        self.analyzer = None
        self.curator = Curator(
            min_relevance_score=3.0,
            max_total_articles=20,   # V4 : jusqu'à 20 items (gradient de profondeur)
            themes_config_path=themes_config_path
        )
        self.writer = NewsletterWriter(api_key=self.api_key)

        if self.api_key:
            self.analyzer = Analyzer(api_key=self.api_key)

        # Dossier pour les checkpoints de reprise
        self.checkpoint_dir = os.path.join(self.output_dir, "..", ".checkpoints")

        # Gestion gracieuse des interruptions (SIGINT/SIGTERM)
        self._current_stage = None
        self._current_stage_data = None
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Sauvegarde le checkpoint courant avant arrêt propre"""
        sig_name = "SIGINT (Ctrl+C)" if signum == signal.SIGINT else "SIGTERM"
        console.print(f"\n[bold yellow]⚠ Signal {sig_name} reçu — arrêt propre en cours...[/bold yellow]")
        if self._current_stage and self._current_stage_data is not None:
            self._save_checkpoint(self._current_stage, self._current_stage_data)
            console.print(f"[green]💾 Checkpoint '{self._current_stage}' sauvegardé. Relancez avec --resume pour reprendre.[/green]")
        else:
            console.print("[yellow]💡 Aucun checkpoint intermédiaire à sauvegarder. Relancez avec --resume si des checkpoints existaient.[/yellow]")
        sys.exit(130 if signum == signal.SIGINT else 143)

    def _check_api_connection(self) -> bool:
        """Vérifie la connexion à l'API Claude avant de lancer le pipeline"""
        if not self.api_key:
            return False
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            # Appel minimal pour tester la connexion
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            console.print("[green]  ✓ Connexion API Claude OK[/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]✗ Connexion API Claude échouée: {type(e).__name__}: {str(e)[:100]}[/bold red]")
            console.print("[yellow]  Vérifiez votre clé API et votre connexion réseau.[/yellow]")
            return False

    def _checkpoint_path(self, stage: str) -> str:
        """Chemin du fichier checkpoint pour une étape donnée"""
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        return os.path.join(self.checkpoint_dir, f"checkpoint_{stage}.pkl")

    def _save_checkpoint(self, stage: str, data: Any):
        """Sauvegarde un checkpoint après une étape du pipeline"""
        path = self._checkpoint_path(stage)
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            console.print(f"[dim]  💾 Checkpoint sauvegardé: {stage}[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠ Impossible de sauvegarder le checkpoint {stage}: {e}[/yellow]")

    def _load_checkpoint(self, stage: str) -> Optional[Any]:
        """Charge un checkpoint si disponible"""
        path = self._checkpoint_path(stage)
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                console.print(f"[green]  ♻ Checkpoint chargé: {stage}[/green]")
                return data
            except Exception as e:
                console.print(f"[yellow]⚠ Checkpoint {stage} corrompu, recalcul...[/yellow]")
        return None

    def _clear_checkpoints(self):
        """Supprime tous les checkpoints après une exécution réussie"""
        if os.path.exists(self.checkpoint_dir):
            for f in os.listdir(self.checkpoint_dir):
                if f.startswith("checkpoint_"):
                    os.remove(os.path.join(self.checkpoint_dir, f))
            console.print("[dim]  🧹 Checkpoints nettoyés[/dim]")

    def _load_themes_config(self) -> Dict[str, Any]:
        """Charge la configuration des thèmes éditoriaux"""
        try:
            with open(self.themes_config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[yellow]⚠ Config thèmes non trouvée: {self.themes_config_path}[/yellow]")
            return {}

    def _get_suggested_theme(self, month: str) -> Optional[str]:
        """Retourne le thème suggéré pour un mois donné"""
        month_mapping = {
            "janvier": "janvier", "février": "fevrier", "mars": "mars",
            "avril": "avril", "mai": "mai", "juin": "juin",
            "juillet": "juillet", "août": "aout", "septembre": "septembre",
            "octobre": "octobre", "novembre": "novembre", "décembre": "decembre"
        }

        month_name = month.split()[0].lower()
        month_key = month_mapping.get(month_name)

        if month_key and 'planning_suggere' in self.themes_config:
            return self.themes_config['planning_suggere'].get(month_key)

        return None

    def _get_theme_info(self, theme_id: str) -> Dict[str, Any]:
        """Retourne les informations d'un thème"""
        if 'themes' in self.themes_config and theme_id in self.themes_config['themes']:
            return self.themes_config['themes'][theme_id]
        return {}

    def _display_banner(self, month: str, theme_id: Optional[str] = None):
        """Affiche la bannière de démarrage"""
        theme_info = self._get_theme_info(theme_id) if theme_id else {}
        theme_name = theme_info.get('name_short', 'Tous thèmes')

        banner = f"""
[bold blue]╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   📰  BANKING NEWSLETTER AGENT V3                              ║
║       Ares & Co - Conseil en Stratégie                         ║
║                                                                ║
║   Structure : Édito → Essentiel → Stratégies →                 ║
║               Modèles → Régulation → Terrain → CTA             ║
║                                                                ║
║   Période : {month:^20}                            ║
║   Thème   : {theme_name:^20}                            ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝[/bold blue]
"""
        console.print(banner)

    def run(
        self,
        month: Optional[str] = None,
        theme_id: Optional[str] = None,
        tension_point: Optional[str] = None,
        partner_name: Optional[str] = None,
        days_back: int = 30,
        output_format: str = "html",
        max_articles: Optional[int] = None,
        skip_analysis: bool = False,
        logo_url: Optional[str] = None,
        terrain: Optional[Dict[str, str]] = None,
        skip_terrain: bool = False
    ) -> dict:
        """
        Exécute le pipeline complet de génération de newsletter V3.

        Args:
            month: Mois de la newsletter (ex: "Mars 2026")
            theme_id: Identifiant du thème éditorial
            tension_point: Point de tension pour l'éditorial (optionnel)
            partner_name: Nom du Partner signataire
            days_back: Nombre de jours à remonter
            output_format: Format de sortie ("markdown", "html", "both")
            max_articles: Limite d'articles à analyser
            skip_analysis: Sauter l'analyse IA
            logo_url: URL du logo
            terrain: Mini-cas Ares & Co (dict)
            skip_terrain: Ne pas générer le terrain
        """
        # Déterminer le mois
        if month is None:
            from dateutil.relativedelta import relativedelta
            last_month = datetime.now() - relativedelta(months=1)
            month = last_month.strftime("%B %Y").capitalize()
            month_translations = {
                "January": "Janvier", "February": "Février", "March": "Mars",
                "April": "Avril", "May": "Mai", "June": "Juin",
                "July": "Juillet", "August": "Août", "September": "Septembre",
                "October": "Octobre", "November": "Novembre", "December": "Décembre"
            }
            for en, fr in month_translations.items():
                month = month.replace(en, fr)

        # Déterminer le thème
        if theme_id is None:
            theme_id = self._get_suggested_theme(month)
            if theme_id:
                console.print(f"[cyan]📋 Thème suggéré pour {month}: {theme_id}[/cyan]")

        if theme_id and theme_id not in self.AVAILABLE_THEMES:
            console.print(f"[yellow]⚠ Thème inconnu '{theme_id}'. Disponibles: {', '.join(self.AVAILABLE_THEMES)}[/yellow]")
            theme_id = None

        self._display_banner(month, theme_id)

        # Vérifier la connexion API avant de lancer le pipeline
        if self.api_key and not skip_analysis:
            if not self._check_api_connection():
                console.print("[bold red]❌ Impossible de continuer sans connexion API.[/bold red]")
                return {"status": "connection_error", "month": month, "error": "API connection failed"}

        theme_info = self._get_theme_info(theme_id) if theme_id else {}

        results = {
            "month": month,
            "theme": theme_id,
            "theme_name": theme_info.get('name', None),
            "status": "success",
            "articles_collected": 0,
            "articles_analyzed": 0,
            "articles_selected": 0,
            "blocs": {},
            "output_files": []
        }

        # Initialiser l'audit trail
        audit = AuditTrail()
        audit.log_run_params(
            month=month,
            theme_id=theme_id,
            theme_name=theme_info.get('name', ''),
            partner_name=partner_name or "Olivier Dupin",
            days_back=days_back,
            model=self.analyzer.model if self.analyzer else "N/A"
        )

        try:
            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 1 : COLLECTE (avec reprise sur checkpoint)
            # ═══════════════════════════════════════════════════════════
            self._current_stage = "collecte"
            cached_articles = self._load_checkpoint("collecte")
            if cached_articles is not None:
                console.print(Panel("[bold]ÉTAPE 1/5 : COLLECTE ♻ (reprise depuis checkpoint)[/bold]", style="green"))
                articles = cached_articles
            else:
                console.print(Panel("[bold]ÉTAPE 1/5 : COLLECTE[/bold]", style="blue"))
                articles = self.collector.collect_all(days_back=days_back)
                self._save_checkpoint("collecte", articles)
            self._current_stage_data = articles

            # Collecte complémentaire via NewsAPI (si NEWSAPI_KEY est définie)
            if os.environ.get("NEWSAPI_KEY"):
                newsapi_articles = collect_newsapi(days_back=days_back)
                if newsapi_articles:
                    # Dédupliquer par URL (basé sur l'id = hash de l'URL)
                    existing_ids = {a.id for a in articles}
                    new_count = 0
                    for na in newsapi_articles:
                        if na.id not in existing_ids:
                            articles.append(na)
                            existing_ids.add(na.id)
                            new_count += 1
                    console.print(f"[green]✓ {new_count} articles NewsAPI ajoutés (après déduplication)[/green]")
            results["articles_collected"] = len(articles)

            # Audit : logger les sources
            for feed in self.collector.config.get('rss_feeds', []):
                status = "OK"
                count = sum(1 for a in articles if a.source == feed['name'])
                audit.log_source(feed['name'], feed['url'], status, count)
            for web in self.collector.config.get('web_sources', []):
                count = sum(1 for a in articles if a.source == web['name'])
                status = "OK" if count > 0 else "empty"
                audit.log_source(web['name'], web['url'], status, count)

            # Audit : logger tous les articles collectés
            for a in articles:
                audit.log_article_collected(a)

            if not articles:
                console.print("[yellow]⚠ Aucun article collecté. Vérifiez les sources.[/yellow]")
                results["status"] = "no_articles"
                audit.save_excel(os.path.join(self.output_dir, "..", "audit"))
                return results

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 2 : ANALYSE (avec reprise sur checkpoint)
            # ═══════════════════════════════════════════════════════════
            self._current_stage = "analyse"
            cached_analysis = self._load_checkpoint("analyse")
            if cached_analysis is not None:
                console.print(Panel("[bold]ÉTAPE 2/5 : ANALYSE ♻ (reprise depuis checkpoint)[/bold]", style="green"))
                analyzed_articles = cached_analysis
            else:
                console.print(Panel("[bold]ÉTAPE 2/5 : ANALYSE[/bold]", style="blue"))

                if skip_analysis or not self.analyzer:
                    if not self.analyzer:
                        console.print("[yellow]⚠ Pas de clé API Claude. Analyse basique.[/yellow]")

                    analyzed_articles = []
                    for a in articles:
                        if a.priority == 1:
                            score = 8.0
                        elif a.priority == 2:
                            score = 6.5
                        else:
                            score = 5.0

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
                            title_fr=a.title
                        ))
                else:
                    articles_to_analyze = articles[:max_articles] if max_articles else articles
                    analyzed_articles = self.analyzer.analyze_batch_optimized(
                        articles_to_analyze,
                        batch_size=5
                    )

                self._save_checkpoint("analyse", analyzed_articles)
            self._current_stage_data = analyzed_articles

            # Audit : logger les analyses
            for aa in analyzed_articles:
                audit.log_article_analyzed(aa)
                audit.log_api_call(tokens_estimate=600)

            results["articles_analyzed"] = len(analyzed_articles)

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 3 : CURATION V3 (distribution en 4 blocs, avec reprise)
            # ═══════════════════════════════════════════════════════════
            self._current_stage = "curation"
            cached_curation = self._load_checkpoint("curation")
            if cached_curation is not None:
                console.print(Panel("[bold]ÉTAPE 3/5 : CURATION V3 ♻ (reprise depuis checkpoint)[/bold]", style="green"))
                selection = cached_curation
            else:
                console.print(Panel("[bold]ÉTAPE 3/5 : CURATION V3 — 4 blocs éditoriaux[/bold]", style="blue"))

                if theme_id:
                    console.print(f"[cyan]🎯 Filtrage par thème: {theme_info.get('name', theme_id)}[/cyan]")

                selection = self.curator.curate(analyzed_articles, theme_id=theme_id)
                self._save_checkpoint("curation", selection)
            self._current_stage_data = selection
            results["articles_selected"] = selection.total_selected

            # Résumé des blocs
            if hasattr(selection, 'blocs'):
                for bloc_id, arts in selection.blocs.items():
                    results["blocs"][bloc_id] = len(arts)

            # Audit : logger les articles retenus et rejetés
            retained_ids = set()
            item_num = 1
            for bloc_id in self.curator.BLOC_ORDER:
                bloc_articles = selection.blocs.get(bloc_id, [])
                for aa in bloc_articles:
                    final_score = self.curator.calculate_final_score(aa)
                    audit.log_article_retained(aa.article.id, bloc_id, final_score, item_num)
                    retained_ids.add(aa.article.id)
                    item_num += 1

            # Logger les articles rejetés
            for aa in analyzed_articles:
                if aa.article.id not in retained_ids:
                    reason = "Score insuffisant"
                    if aa.relevance_score < self.curator.min_relevance_score:
                        reason = f"Score trop bas ({aa.relevance_score:.1f} < {self.curator.min_relevance_score})"
                    audit.log_article_rejected(aa.article.id, reason)

            if selection.total_selected == 0:
                console.print("[yellow]⚠ Aucun article sélectionné après curation.[/yellow]")
                results["status"] = "no_selection"
                audit.save_excel(os.path.join(self.output_dir, "..", "audit"))
                return results

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 4 : RÉDACTION (appels Claude — avec checkpoint)
            # ═══════════════════════════════════════════════════════════
            self._current_stage = "redaction"
            cached_redaction = self._load_checkpoint("redaction")
            if cached_redaction is not None:
                console.print(Panel("[bold]ÉTAPE 4/5 : RÉDACTION ♻ (reprise depuis checkpoint)[/bold]", style="green"))
                editorial = cached_redaction["editorial"]
                chiffre_du_mois = cached_redaction["chiffre_du_mois"]
                hashtags = cached_redaction["hashtags"]
                sommaire = cached_redaction["sommaire"]
                terrain = cached_redaction.get("terrain", terrain)
            else:
                console.print(Panel("[bold]ÉTAPE 4/5 : RÉDACTION (appels Claude)[/bold]", style="blue"))

                # Générer les hashtags d'accroche
                console.print("[dim]  → Génération des hashtags d'accroche...[/dim]")
                hashtags = self.writer.generate_hashtags(selection)

                # Générer le sommaire
                sommaire = self.writer.generate_sommaire(selection)

                # Générer l'éditorial V3 (250-300 mots, 4 parties)
                console.print("[dim]  → Génération de l'éditorial V3 (4 parties, 250-300 mots)...[/dim]")
                editorial = self.writer.generate_editorial(
                    selection, month,
                    tension_point=tension_point,
                    partner_name=partner_name
                )

                # Générer "Notre lecture" pour Bloc 3 (Nouveaux modèles)
                console.print("[dim]  → Génération de 'Notre lecture' (Bloc 3)...[/dim]")
                self.writer.generate_notre_lecture(selection)

                # Générer le Chiffre du mois (bandeau post-éditorial)
                console.print("[dim]  → Génération du Chiffre du mois...[/dim]")
                chiffre_du_mois = self.writer.generate_chiffre_du_mois(
                    selection, month, editorial
                )

                # Générer le Terrain (optionnel)
                if not skip_terrain and terrain is None:
                    console.print("[dim]  → Génération du Terrain Ares & Co...[/dim]")
                    terrain = self.writer.generate_terrain(selection, month)

                # Sauvegarder le checkpoint rédaction
                self._save_checkpoint("redaction", {
                    "editorial": editorial,
                    "chiffre_du_mois": chiffre_du_mois,
                    "hashtags": hashtags,
                    "sommaire": sommaire,
                    "terrain": terrain,
                })
            self._current_stage_data = {
                "editorial": editorial, "chiffre_du_mois": chiffre_du_mois,
                "hashtags": hashtags, "sommaire": sommaire, "terrain": terrain,
            }

            # ═══════════════════════════════════════════════════════════
            # ÉTAPE 5 : EXPORT (Markdown / HTML)
            # ═══════════════════════════════════════════════════════════
            self._current_stage = "export"
            console.print(Panel("[bold]ÉTAPE 5/5 : EXPORT[/bold]", style="blue"))

            # Markdown
            if output_format in ("markdown", "both"):
                console.print("[dim]  → Génération du Markdown V3...[/dim]")
                md_content = self.writer.generate_markdown_v3(
                    selection, month, editorial,
                    partner_name=partner_name,
                    terrain=terrain,
                    chiffre_du_mois=chiffre_du_mois,
                    hashtags=hashtags,
                    sommaire=sommaire
                )
                md_path = self.writer.save_markdown(md_content, self.output_dir)
                results["output_files"].append(md_path)

            # HTML V3
            if output_format in ("html", "both"):
                console.print("[dim]  → Génération du HTML V3...[/dim]")
                html_content = self.writer.generate_html_v3(
                    selection=selection,
                    month=month,
                    editorial=editorial,
                    terrain=terrain,
                    partner_name=partner_name,
                    logo_url=logo_url,
                    chiffre_du_mois=chiffre_du_mois,
                    hashtags=hashtags,
                    sommaire=sommaire
                )
                html_path = self.writer.save_html(html_content, self.output_dir)
                results["output_files"].append(html_path)

            # ═══════════════════════════════════════════════════════════
            # AUDIT TRAIL — Logger la génération
            # ═══════════════════════════════════════════════════════════
            audit.log_generation(
                editorial=editorial,
                chiffre=chiffre_du_mois,
                hashtags=hashtags,
                output_files=results["output_files"]
            )

            # Sauvegarder l'audit trail Excel
            audit_dir = os.path.join(self.output_dir, "..", "audit")
            audit_path = audit.save_excel(audit_dir)
            results["output_files"].append(audit_path)

            # ═══════════════════════════════════════════════════════════
            # RÉSUMÉ FINAL
            # ═══════════════════════════════════════════════════════════
            self._display_summary(results)

            # Nettoyer les checkpoints après succès
            self._clear_checkpoints()

        except Exception as e:
            console.print(f"\n[bold red]❌ Erreur : {str(e)}[/bold red]")
            console.print(f"[yellow]💡 Les checkpoints sont sauvegardés. Relancez avec --resume pour reprendre.[/yellow]")
            results["status"] = "error"
            results["error"] = str(e)
            # Sauvegarder l'audit trail même en cas d'erreur
            try:
                audit_dir = os.path.join(self.output_dir, "..", "audit")
                audit.save_excel(audit_dir)
            except Exception:
                pass
            raise

        return results

    def _display_summary(self, results: dict):
        """Affiche le résumé final"""
        theme_line = ""
        if results.get('theme_name'):
            theme_line = f"\n- **Thème** : {results['theme_name']}"

        blocs_line = ""
        if results.get('blocs'):
            bloc_names = {
                "essentiel": "L'essentiel",
                "strategies_marches": "Stratégies & marchés",
                "nouveaux_modeles": "Nouveaux modèles",
                "regulation": "Régulation & supervision",
            }
            blocs_detail = ", ".join([
                f"{bloc_names.get(k, k)}: {v}"
                for k, v in results['blocs'].items() if v > 0
            ])
            blocs_line = f"\n- **Blocs** : {blocs_detail}"

        summary = f"""
## Génération V3 terminée

- **Mois** : {results['month']}{theme_line}
- **Articles collectés** : {results['articles_collected']}
- **Articles analysés** : {results['articles_analyzed']}
- **Articles sélectionnés** : {results['articles_selected']}{blocs_line}

### Fichiers générés :
"""
        for f in results["output_files"]:
            summary += f"\n- `{f}`"

        console.print(Panel(Markdown(summary), title="[bold green]✅ SUCCÈS[/bold green]", style="green"))

    def run_interactive(self):
        """Mode interactif avec prompts utilisateur"""
        console.print("\n[bold]🎯 Mode interactif V3[/bold]\n")

        # Afficher les thèmes disponibles
        console.print("[cyan]Thèmes disponibles :[/cyan]")
        for i, theme_id in enumerate(self.AVAILABLE_THEMES, 1):
            theme_info = self._get_theme_info(theme_id)
            console.print(f"  {i}. [bold]{theme_id}[/bold] - {theme_info.get('name', '')}")

        # Demander les paramètres
        month = console.input("\n[cyan]Mois de la newsletter[/cyan] (ex: Mars 2026, vide=auto) : ") or None
        theme_input = console.input("[cyan]Thème[/cyan] (numéro ou ID, vide=suggéré) : ") or None

        theme_id = None
        if theme_input:
            if theme_input.isdigit():
                idx = int(theme_input) - 1
                if 0 <= idx < len(self.AVAILABLE_THEMES):
                    theme_id = self.AVAILABLE_THEMES[idx]
            else:
                theme_id = theme_input

        tension = console.input("[cyan]Point de tension de l'éditorial[/cyan] (vide=auto) : ") or None
        partner = console.input("[cyan]Partner signataire[/cyan] (défaut: Olivier Dupin) : ") or None
        days = console.input("[cyan]Jours à remonter[/cyan] (défaut: 30) : ") or "30"
        format_choice = console.input("[cyan]Format[/cyan] (html/markdown/both, défaut: both) : ") or "both"

        return self.run(
            month=month,
            theme_id=theme_id,
            tension_point=tension,
            partner_name=partner,
            days_back=int(days),
            output_format=format_choice
        )


def main():
    """Point d'entrée CLI"""
    theme_choices = [
        "growth_distribution",
        "customer_experience",
        "operational_performance",
        "demographic_transition",
        "retirement_savings",
        "risk_finance"
    ]

    parser = argparse.ArgumentParser(
        description="Agent de génération de newsletter bancaire V3 - Ares & Co",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Thèmes disponibles :
  1. growth_distribution      - Modèles de croissance & distribution
  2. customer_experience      - Expérience client & propositions de valeur
  3. operational_performance  - Performance opérationnelle
  4. demographic_transition   - Transition démographique
  5. retirement_savings       - Épargne retraite
  6. risk_finance            - Risk & Finance

Structure V3 :
  Bloc 0 : Notre éditorial (250-300 mots, 4 parties)
  Bloc 1 : L'essentiel (1-3 items, liés à l'éditorial)
  Bloc 2 : Stratégies & marchés (2-3 items)
  Bloc 3 : Nouveaux modèles (2-3 items, "Notre lecture" optionnel)
  Bloc 4 : Régulation & supervision (2-3 items)

Exemples d'utilisation :
  python agent.py                                        # Génération avec thème suggéré
  python agent.py --theme growth_distribution            # Thème spécifique
  python agent.py --month "Mars 2026" --theme 1          # Mois + thème
  python agent.py --tension "La fin du modèle généraliste"  # Point de tension imposé
  python agent.py --partner "Jean Dupont"                # Partner signataire
  python agent.py --format both                          # HTML + Markdown
  python agent.py --interactive                          # Mode interactif
  python agent.py --test                                 # Test sans API
  python agent.py --resume                               # Reprendre après perte de connexion
        """
    )

    parser.add_argument("--month", "-m", help="Mois de la newsletter (ex: 'Mars 2026')")
    parser.add_argument("--theme", "-T", help="Thème éditorial (ID ou numéro 1-6)")
    parser.add_argument("--tension", help="Point de tension pour l'éditorial")
    parser.add_argument("--partner", help="Nom du Partner signataire (défaut: Olivier Dupin)")
    parser.add_argument("--list-themes", action="store_true", help="Afficher les thèmes et quitter")
    parser.add_argument("--days", "-d", type=int, default=30, help="Jours à remonter (défaut: 30)")
    parser.add_argument("--format", "-f", choices=["markdown", "html", "both"], default="html", help="Format de sortie")
    parser.add_argument("--max-articles", type=int, help="Limite d'articles à analyser")
    parser.add_argument("--output", "-o", default="output/newsletters", help="Dossier de sortie")
    parser.add_argument("--config", "-c", default="config/sources.yaml", help="Config des sources")
    parser.add_argument("--themes-config", default="config/themes.yaml", help="Config des thèmes")
    parser.add_argument("--logo-url", help="URL du logo")
    parser.add_argument("--skip-terrain", action="store_true", help="Ne pas générer le Terrain")
    parser.add_argument("--interactive", "-i", action="store_true", help="Mode interactif")
    parser.add_argument("--test", "-t", action="store_true", help="Mode test (sans analyse IA)")
    parser.add_argument("--resume", "-r", action="store_true", help="Reprendre depuis les checkpoints après une perte de connexion")

    args = parser.parse_args()

    # Changer vers le dossier du projet
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)

    # Option --list-themes
    if args.list_themes:
        console.print("\n[bold]📋 Thèmes éditoriaux disponibles :[/bold]\n")
        for i, theme_id in enumerate(theme_choices, 1):
            console.print(f"  [cyan]{i}[/cyan]. [bold]{theme_id}[/bold]")
        console.print("\n[dim]Utilisez --theme <ID> ou --theme <numéro> pour sélectionner.[/dim]")
        sys.exit(0)

    # Résoudre le thème
    theme_id = None
    if args.theme:
        if args.theme.isdigit():
            idx = int(args.theme) - 1
            if 0 <= idx < len(theme_choices):
                theme_id = theme_choices[idx]
            else:
                console.print(f"[red]❌ Numéro invalide: {args.theme}. Utilisez 1-6.[/red]")
                sys.exit(1)
        else:
            theme_id = args.theme

    # Créer et exécuter l'agent
    agent = BankingNewsletterAgent(
        config_path=args.config,
        themes_config_path=args.themes_config,
        output_dir=args.output
    )

    # Vérifier la présence de checkpoints et proposer la reprise
    if not args.resume and os.path.exists(agent.checkpoint_dir):
        checkpoint_files = [f for f in os.listdir(agent.checkpoint_dir) if f.startswith("checkpoint_")]
        if checkpoint_files:
            stages = [f.replace("checkpoint_", "").replace(".pkl", "") for f in checkpoint_files]
            console.print(f"\n[yellow]💡 Checkpoints détectés ({', '.join(stages)}). Utilisez --resume pour reprendre.[/yellow]")

    if not args.resume:
        # Sans --resume, on efface les anciens checkpoints pour repartir de zéro
        agent._clear_checkpoints()

    if args.interactive:
        results = agent.run_interactive()
    else:
        results = agent.run(
            month=args.month,
            theme_id=theme_id,
            tension_point=args.tension,
            partner_name=args.partner,
            days_back=args.days,
            output_format=args.format,
            max_articles=args.max_articles,
            skip_analysis=args.test,
            logo_url=args.logo_url,
            skip_terrain=args.skip_terrain
        )

    sys.exit(0 if results["status"] == "success" else 1)


if __name__ == "__main__":
    main()
