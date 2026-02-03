#!/usr/bin/env python3
"""
Mode démo avec données simulées
Banking Newsletter Agent - Ares & Co

Ce script démontre le fonctionnement de l'agent avec des articles fictifs
(sans appels réseau ni API Claude)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from collector import Article
from analyzer import AnalyzedArticle
from curator import Curator, CuratedSelection
from writer import NewsletterWriter

console = Console()


# Données simulées basées sur l'actualité bancaire réelle
MOCK_ARTICLES = [
    {
        "title": "La BCE maintient ses taux directeurs inchangés à 2,00%",
        "source": "BCE - Communiqués",
        "category": "monetary_policy",
        "summary": "Le Conseil des gouverneurs de la BCE a décidé de maintenir les trois taux directeurs inchangés. Le taux de la facilité de dépôt reste à 2,00%, le taux des opérations principales de refinancement à 2,15% et le taux de la facilité de prêt marginal à 2,40%.",
        "key_facts": [
            "Taux de dépôt maintenu à 2,00%",
            "Inflation sous-jacente toujours au-dessus de l'objectif",
            "Prochaine réunion le 6 mars 2026"
        ],
        "entities": ["BCE", "Christine Lagarde"],
        "priority": 1,
        "relevance": 9.5
    },
    {
        "title": "L'EBA publie les nouvelles guidelines sur les risques ESG",
        "source": "EBA - Press Releases",
        "category": "regulation",
        "summary": "L'Autorité bancaire européenne a publié ses lignes directrices finales sur la gestion des risques environnementaux, sociaux et de gouvernance (ESG). Ces guidelines entrent en application immédiate et concernent toutes les banques européennes.",
        "key_facts": [
            "Intégration ESG obligatoire dans le processus ICAAP",
            "Nouveaux stress tests climatiques requis",
            "Délai de mise en conformité : 12 mois"
        ],
        "entities": ["EBA", "ACPR"],
        "priority": 1,
        "relevance": 9.0
    },
    {
        "title": "BNP Paribas annonce un plan de transformation digitale de 500M€",
        "source": "Finextra",
        "category": "french_banks",
        "summary": "BNP Paribas a dévoilé un plan d'investissement massif de 500 millions d'euros sur trois ans pour accélérer sa transformation digitale. Le plan prévoit notamment le déploiement de l'IA générative dans la relation client.",
        "key_facts": [
            "Investissement de 500M€ sur 2026-2028",
            "Déploiement IA générative pour les conseillers",
            "Objectif : 30% de gains de productivité"
        ],
        "entities": ["BNP Paribas", "Jean-Laurent Bonnafé"],
        "priority": 1,
        "relevance": 8.5
    },
    {
        "title": "AMLA opérationnelle : transfert des compétences AML depuis l'EBA",
        "source": "EBA - Press Releases",
        "category": "regulation",
        "summary": "L'Autorité européenne de lutte contre le blanchiment (AMLA) est désormais pleinement opérationnelle après le transfert de toutes les compétences AML/CFT depuis l'EBA. Un protocole de coopération a été signé entre les deux autorités.",
        "key_facts": [
            "Transfert effectif au 1er janvier 2026",
            "AMLA basée à Francfort",
            "Supervision directe des établissements à haut risque"
        ],
        "entities": ["AMLA", "EBA", "Commission Européenne"],
        "priority": 1,
        "relevance": 8.8
    },
    {
        "title": "Société Générale finalise la cession de ses activités en Russie",
        "source": "Les Echos",
        "category": "french_banks",
        "summary": "Société Générale a finalisé la vente de Rosbank et de ses filiales russes, mettant fin à sa présence historique en Russie. L'opération génère une perte comptable mais libère des fonds propres significatifs.",
        "key_facts": [
            "Cession de Rosbank finalisée",
            "Impact CET1 positif de +20 points de base",
            "Fin de 20 ans de présence en Russie"
        ],
        "entities": ["Société Générale", "Rosbank", "Slawomir Krupa"],
        "priority": 2,
        "relevance": 7.5
    },
    {
        "title": "France FinTech : record de levées de fonds pour les néobanques en 2025",
        "source": "France FinTech",
        "category": "innovation",
        "summary": "L'écosystème fintech français a enregistré un record de levées de fonds en 2025, porté notamment par les néobanques et les solutions de paiement B2B. Le total atteint 2,3 milliards d'euros.",
        "key_facts": [
            "2,3 milliards d'euros levés en 2025",
            "Croissance de 40% vs 2024",
            "Paiement B2B : segment le plus dynamique"
        ],
        "entities": ["France FinTech", "Qonto", "Pennylane"],
        "priority": 2,
        "relevance": 7.8
    },
    {
        "title": "Report d'un an pour le FRTB : la Commission européenne accorde un délai",
        "source": "Commission Européenne",
        "category": "regulation",
        "summary": "La Commission européenne a adopté un acte délégué reportant d'un an supplémentaire l'application du Fundamental Review of the Trading Book (FRTB). Les exigences de risque de marché s'appliqueront au 1er janvier 2027.",
        "key_facts": [
            "Report au 1er janvier 2027",
            "Alignement avec les calendriers internationaux",
            "Banques saluent cette décision"
        ],
        "entities": ["Commission Européenne", "EBA", "Comité de Bâle"],
        "priority": 1,
        "relevance": 8.2
    },
    {
        "title": "Crédit Agricole lance une offre de Banking-as-a-Service",
        "source": "Finextra",
        "category": "innovation",
        "summary": "Crédit Agricole a annoncé le lancement de CA BaaS, une plateforme permettant aux entreprises d'intégrer des services bancaires via API. L'offre cible les marketplaces et les fintechs.",
        "key_facts": [
            "Plateforme API complète (comptes, paiements, KYC)",
            "Partenariat avec 3 fintechs au lancement",
            "Objectif : 50 clients entreprises en 2026"
        ],
        "entities": ["Crédit Agricole", "CACIB"],
        "priority": 2,
        "relevance": 7.2
    },
    {
        "title": "DORA : les banques européennes finalisent leur mise en conformité",
        "source": "EBA - Press Releases",
        "category": "regulation",
        "summary": "À l'approche de l'échéance de janvier 2026, les banques européennes accélèrent leur mise en conformité avec le règlement DORA sur la résilience opérationnelle numérique. L'EBA publie un état des lieux.",
        "key_facts": [
            "85% des banques conformes ou en voie de l'être",
            "Tests de résilience cyber obligatoires",
            "Cartographie des prestataires IT critiques"
        ],
        "entities": ["EBA", "DORA", "ACPR"],
        "priority": 1,
        "relevance": 8.0
    },
    {
        "title": "Open Banking : l'usage des APIs explose en Europe",
        "source": "Fintech Futures",
        "category": "innovation",
        "summary": "Le nombre d'appels API en Open Banking a augmenté de 70% en Europe en 2025, porté par l'agrégation de comptes et l'initiation de paiements. Le Royaume-Uni reste leader mais la France progresse.",
        "key_facts": [
            "+70% d'appels API en 2025",
            "France : 3ème marché européen",
            "Paiement par virement : adoption croissante"
        ],
        "entities": ["Berlin Group", "STET", "DSP2"],
        "priority": 2,
        "relevance": 7.0
    }
]


def generate_mock_articles():
    """Génère des articles simulés"""
    articles = []

    for i, data in enumerate(MOCK_ARTICLES):
        # Date aléatoire dans les 30 derniers jours
        days_ago = random.randint(1, 28)
        pub_date = datetime.now() - timedelta(days=days_ago)

        article = Article(
            id=f"mock_{i:03d}",
            title=data["title"],
            url=f"https://example.com/article/{i}",
            source=data["source"],
            category=data["category"],
            published_date=pub_date,
            content=data["summary"],
            summary=data["summary"],
            priority=data["priority"]
        )
        articles.append(article)

    return articles


def generate_mock_analyzed_articles(articles):
    """Génère des articles analysés simulés"""
    analyzed = []

    for article in articles:
        # Trouver les données mock correspondantes
        mock_data = next(
            (m for m in MOCK_ARTICLES if m["title"] == article.title),
            None
        )

        if mock_data:
            analyzed.append(AnalyzedArticle(
                article=article,
                ai_summary=mock_data["summary"],
                relevance_score=mock_data["relevance"],
                assigned_category=mock_data["category"],
                key_facts=mock_data["key_facts"],
                entities=mock_data["entities"],
                sentiment="neutral",
                newsletter_priority=mock_data["priority"]
            ))

    return analyzed


def run_demo():
    """Exécute la démo complète"""
    month = "Janvier 2026"

    banner = f"""
[bold blue]╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   📰  BANKING NEWSLETTER AGENT - MODE DÉMO                     ║
║       Ares & Co - Conseil en Stratégie                         ║
║                                                                ║
║   Démonstration avec données simulées                          ║
║   Période : {month:^20}                            ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝[/bold blue]
"""
    console.print(banner)

    # ÉTAPE 1: Collecte simulée
    console.print(Panel("[bold]ÉTAPE 1/4 : COLLECTE (simulée)[/bold]", style="blue"))
    articles = generate_mock_articles()
    console.print(f"\n[green]✓ {len(articles)} articles simulés générés[/green]\n")

    for a in articles[:3]:
        console.print(f"  • [cyan]{a.source}[/cyan]: {a.title[:50]}...")
    console.print("  ...")

    # ÉTAPE 2: Analyse simulée
    console.print(Panel("[bold]ÉTAPE 2/4 : ANALYSE (simulée)[/bold]", style="blue"))
    analyzed = generate_mock_analyzed_articles(articles)
    console.print(f"\n[green]✓ {len(analyzed)} articles analysés[/green]\n")

    # ÉTAPE 3: Curation
    console.print(Panel("[bold]ÉTAPE 3/4 : CURATION[/bold]", style="blue"))
    curator = Curator(
        min_relevance_score=7.0,
        max_articles_per_category=3,
        max_total_articles=10
    )
    selection = curator.curate(analyzed)

    # ÉTAPE 4: Génération
    console.print(Panel("[bold]ÉTAPE 4/4 : GÉNÉRATION[/bold]", style="blue"))

    # Editorial simulé (sans API)
    editorial = """Le mois de février 2026 a été marqué par une actualité réglementaire dense, avec notamment l'entrée en vigueur effective de l'AMLA et les derniers ajustements du calendrier Bâle III. La BCE, de son côté, maintient le cap de sa politique monétaire restrictive, dans un contexte d'inflation sous-jacente encore élevée.

Du côté des banques françaises, les initiatives de transformation digitale se multiplient. BNP Paribas a dévoilé un plan ambitieux d'investissement dans l'IA, tandis que Crédit Agricole accélère sur le Banking-as-a-Service. Ces mouvements témoignent d'une industrie en pleine mutation, sous la pression conjuguée des fintechs et des nouvelles attentes clients.

L'écosystème fintech français continue par ailleurs de démontrer son dynamisme, avec des levées de fonds record en 2025. Le paiement B2B et les solutions d'embedded finance émergent comme les segments les plus porteurs pour 2026."""

    writer = NewsletterWriter()

    # Générer Markdown
    md_content = writer.generate_markdown(selection, month, editorial)
    md_path = writer.save_markdown(md_content, "output/newsletters", "demo-newsletter.md")

    # Générer HTML
    html_content = writer.generate_html(selection, month, editorial)
    html_path = writer.save_html(html_content, "output/newsletters", "demo-newsletter.html")

    # Résumé final
    summary = f"""
## Démonstration terminée

- **Articles simulés** : {len(articles)}
- **Articles analysés** : {len(analyzed)}
- **Articles sélectionnés** : {selection.total_selected}

### Fichiers générés :
- `{md_path}`
- `{html_path}`

### Aperçu de la newsletter :

{md_content[:1500]}...
"""
    console.print(Panel(Markdown(summary), title="[bold green]✅ DÉMO RÉUSSIE[/bold green]", style="green"))

    return md_path, html_path


if __name__ == "__main__":
    run_demo()
