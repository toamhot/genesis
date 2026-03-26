#!/usr/bin/env python3
"""
Mode démo V3 avec données simulées
Banking Newsletter Agent - Ares & Co

Ce script démontre le fonctionnement de l'agent V3 avec des articles fictifs
(sans appels réseau ni API Claude). Génère la newsletter avec 4 blocs éditoriaux.
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


# Données simulées — réparties par bloc éditorial
MOCK_ARTICLES = [
    # --- Bloc 1 : L'essentiel (liés au thème éditorial) ---
    {
        "title": "La BCE maintient ses taux directeurs inchangés à 2,00%",
        "source": "BCE - Communiqués",
        "category": "monetary_policy",
        "summary": "Le Conseil des gouverneurs de la BCE a décidé de maintenir les trois taux directeurs inchangés.",
        "ai_summary": "Réunie le 6 mars, la BCE a confirmé le statu quo monétaire malgré une inflation sous-jacente toujours au-dessus de l'objectif. Le scénario d'une baisse avant l'été s'éloigne. Pour les banques françaises, cela prolonge la fenêtre de compression des marges sur les dépôts à vue — mais aussi la pression sur la production de crédit immobilier, qui reste anémique à 3,4% sur 20 ans.",
        "key_facts": ["Taux de dépôt maintenu à 2,00%", "Inflation sous-jacente au-dessus de l'objectif"],
        "entities": ["BCE", "Christine Lagarde"],
        "priority": 1,
        "relevance": 9.5
    },
    {
        "title": "L'EBA publie les nouvelles guidelines sur les risques ESG",
        "source": "EBA - Press Releases",
        "category": "regulation",
        "summary": "L'Autorité bancaire européenne a publié ses lignes directrices finales sur la gestion des risques ESG.",
        "ai_summary": "L'EBA impose l'intégration des risques ESG dans le processus ICAAP de toutes les banques européennes, avec un délai de 12 mois pour se conformer. Les établissements devront réaliser des stress tests climatiques annuels et documenter leurs expositions aux risques de transition. Pour les banques françaises de taille intermédiaire, le coût de mise en conformité est estimé entre 5 et 15 M€.",
        "key_facts": ["Intégration ESG dans ICAAP", "Stress tests climatiques requis", "Délai : 12 mois"],
        "entities": ["EBA", "ACPR"],
        "priority": 1,
        "relevance": 9.0
    },
    # --- Bloc 2 : Stratégies & marchés ---
    {
        "title": "BNP Paribas annonce un plan de transformation digitale de 500M€",
        "source": "Les Echos",
        "category": "french_banks",
        "summary": "BNP Paribas a dévoilé un plan d'investissement massif pour accélérer sa transformation digitale.",
        "ai_summary": "BNP Paribas engage 500 millions d'euros sur trois ans pour déployer l'IA générative dans la relation client et moderniser son core banking. L'objectif affiché — 30% de gains de productivité — traduit une ambition de réduire un cost-to-income encore supérieur à 65%. Pour les concurrents français, ce plan crée une pression compétitive directe sur les budgets IT et l'attractivité des talents tech.",
        "key_facts": ["500M€ sur 2026-2028", "IA générative pour les conseillers", "30% gains de productivité"],
        "entities": ["BNP Paribas", "Jean-Laurent Bonnafé"],
        "priority": 1,
        "relevance": 8.5
    },
    {
        "title": "Société Générale finalise la cession de ses activités en Russie",
        "source": "Les Echos",
        "category": "ma",
        "summary": "Société Générale a finalisé la vente de Rosbank et de ses filiales russes.",
        "ai_summary": "Société Générale clôt un chapitre de 20 ans en Russie avec la cession de Rosbank, libérant 20 points de base de CET1. L'opération permet au groupe de redéployer environ 3 Md€ de capital vers ses priorités stratégiques — la banque de détail en France et la BFI en Europe. Pour les autres banques françaises encore exposées aux marchés émergents, cette sortie confirme le recentrage européen du secteur.",
        "key_facts": ["Impact CET1 +20 bps", "Fin de 20 ans de présence", "Recentrage européen"],
        "entities": ["Société Générale", "Rosbank", "Slawomir Krupa"],
        "priority": 2,
        "relevance": 7.5
    },
    {
        "title": "HSBC France cède sa banque de détail à My Money Group pour 1,1 Md€",
        "source": "Les Echos",
        "category": "ma",
        "summary": "Retrait stratégique du marché retail français pour la banque britannique.",
        "ai_summary": "HSBC finalise la cession de ses 244 agences et 800 000 clients à My Money Group pour 1,1 Md€, soit 1,4x la valeur comptable. Le groupe britannique conserve uniquement la banque privée et la BFI en France. Cette opération illustre la difficulté pour un acteur international non-leader à atteindre une rentabilité suffisante sur le retail français — un signal pour les autres banques étrangères en position similaire.",
        "key_facts": ["1,1 Md€", "244 agences", "800K clients transférés"],
        "entities": ["HSBC", "My Money Group", "France"],
        "priority": 1,
        "relevance": 8.7
    },
    # --- Bloc 3 : Nouveaux modèles ---
    {
        "title": "Crédit Agricole lance une offre de Banking-as-a-Service",
        "source": "Mind Fintech",
        "category": "innovation",
        "summary": "Crédit Agricole annonce le lancement de CA BaaS pour les entreprises.",
        "ai_summary": "Le Crédit Agricole a ouvert en bêta fermée sa plateforme Banking-as-a-Service permettant à des enseignes retail d'intégrer des services financiers directement dans leur parcours client. L'offre cible d'abord la grande distribution et le e-commerce. Cette initiative positionne CA comme infrastructure financière pour des acteurs non-bancaires — un renversement de posture qui transforme un concurrent potentiel en client.",
        "key_facts": ["Plateforme API complète", "3 fintechs partenaires", "50 clients visés en 2026"],
        "entities": ["Crédit Agricole", "CACIB"],
        "priority": 2,
        "relevance": 7.2,
        "notre_lecture": "le BaaS bancaire en France en est encore à la phase de preuve de concept ; les banques qui n'auront pas de plateforme crédible d'ici 2027 se retrouveront reléguées au rang de fournisseurs de tuyaux."
    },
    {
        "title": "Open Banking : l'usage des APIs explose en Europe (+70%)",
        "source": "Fintech Futures",
        "category": "innovation",
        "summary": "Le nombre d'appels API en Open Banking a augmenté de 70% en Europe en 2025.",
        "ai_summary": "Le volume d'appels API Open Banking a bondi de 70% en Europe en 2025, porté par l'agrégation de comptes et l'initiation de paiements. La France se positionne comme 3ème marché européen derrière le Royaume-Uni et l'Allemagne. L'adoption du paiement par virement instantané progresse rapidement et pourrait capter 15% des transactions e-commerce d'ici 2028, réduisant la dépendance aux schémas cartes.",
        "key_facts": ["+70% appels API en 2025", "France 3ème marché", "15% e-commerce d'ici 2028"],
        "entities": ["Berlin Group", "STET", "DSP2"],
        "priority": 2,
        "relevance": 7.0
    },
    # --- Bloc 4 : Régulation & supervision ---
    {
        "title": "AMLA opérationnelle : transfert des compétences AML depuis l'EBA",
        "source": "EBA - Communiqué officiel",
        "category": "regulation",
        "summary": "L'Autorité européenne de lutte contre le blanchiment est désormais pleinement opérationnelle.",
        "ai_summary": "L'AMLA (Anti-Money Laundering Authority) est pleinement opérationnelle depuis le 1er janvier 2026 après le transfert de toutes les compétences LCB-FT de l'EBA. Basée à Francfort, elle exercera une supervision directe sur les 40 établissements européens à plus haut risque. Pour les banques françaises concernées, cela implique un double reporting — ACPR et AMLA — et une révision complète des dispositifs de conformité d'ici mi-2027.",
        "key_facts": ["Transfert effectif au 1er janvier 2026", "AMLA à Francfort", "40 établissements supervisés"],
        "entities": ["AMLA", "EBA", "ACPR"],
        "priority": 1,
        "relevance": 8.8
    },
    {
        "title": "Report d'un an pour le FRTB : application au 1er janvier 2027",
        "source": "Commission Européenne",
        "category": "regulation",
        "summary": "La Commission européenne reporte d'un an l'application du FRTB.",
        "ai_summary": "La Commission européenne accorde un an supplémentaire pour l'application du Fundamental Review of the Trading Book (FRTB), repoussant l'échéance au 1er janvier 2027. Ce report aligne le calendrier européen sur celui du Comité de Bâle. Pour les banques françaises actives en BFI, ce délai est l'occasion d'affiner les modèles internes — mais aussi le risque de reporter une charge en capital estimée entre 5 et 15% sur les desks de marché.",
        "key_facts": ["Report au 1er janvier 2027", "Alignement Bâle", "+5-15% charge capital estimée"],
        "entities": ["Commission Européenne", "EBA", "Comité de Bâle"],
        "priority": 1,
        "relevance": 8.2
    },
    {
        "title": "DORA : 85% des banques européennes conformes ou en voie de l'être",
        "source": "EBA - Communiqué officiel",
        "category": "regulation",
        "summary": "État des lieux de la mise en conformité DORA dans le secteur bancaire.",
        "ai_summary": "L'EBA publie un état des lieux de la conformité DORA : 85% des banques européennes déclarent être conformes ou en voie de l'être. Les 15% restants sont principalement des établissements de taille intermédiaire confrontés à la cartographie de leurs prestataires IT critiques. L'ACPR prévoit des contrôles ciblés dès le T2 2026 — un signal clair que les retardataires s'exposent à des recommandations voire des injonctions.",
        "key_facts": ["85% conformes", "Tests cyber obligatoires", "Contrôles ACPR au T2 2026"],
        "entities": ["EBA", "DORA", "ACPR"],
        "priority": 1,
        "relevance": 8.0
    }
]


def generate_mock_articles():
    """Génère des articles simulés"""
    articles = []
    for i, data in enumerate(MOCK_ARTICLES):
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
        mock_data = next(
            (m for m in MOCK_ARTICLES if m["title"] == article.title),
            None
        )
        if mock_data:
            analyzed.append(AnalyzedArticle(
                article=article,
                ai_summary=mock_data["ai_summary"],
                relevance_score=mock_data["relevance"],
                assigned_category=mock_data["category"],
                key_facts=mock_data["key_facts"],
                entities=mock_data["entities"],
                sentiment="neutral",
                newsletter_priority=mock_data["priority"],
                title_fr=mock_data["title"]
            ))
    return analyzed


def run_demo():
    """Exécute la démo V3 complète"""
    month = "Mars 2026"

    banner = f"""
[bold blue]╔══════════════════════════════════════════════════════════════╗
║                                                                ║
║   📰  BANKING NEWSLETTER AGENT V3 - MODE DÉMO                  ║
║       Ares & Co - Conseil en Stratégie                         ║
║                                                                ║
║   Structure : Édito → Essentiel → Stratégies →                 ║
║               Modèles → Régulation → Terrain → CTA             ║
║                                                                ║
║   Période : {month:^20}                            ║
║                                                                ║
╚══════════════════════════════════════════════════════════════╝[/bold blue]
"""
    console.print(banner)

    # ÉTAPE 1: Collecte simulée
    console.print(Panel("[bold]ÉTAPE 1/4 : COLLECTE (simulée)[/bold]", style="blue"))
    articles = generate_mock_articles()
    console.print(f"\n[green]✓ {len(articles)} articles simulés générés[/green]\n")

    # ÉTAPE 2: Analyse simulée
    console.print(Panel("[bold]ÉTAPE 2/4 : ANALYSE (simulée)[/bold]", style="blue"))
    analyzed = generate_mock_analyzed_articles(articles)
    console.print(f"\n[green]✓ {len(analyzed)} articles analysés[/green]\n")

    # ÉTAPE 3: Curation V3
    console.print(Panel("[bold]ÉTAPE 3/4 : CURATION V3 — 4 blocs éditoriaux[/bold]", style="blue"))
    curator = Curator(
        min_relevance_score=3.0,
        max_total_articles=12
    )
    selection = curator.curate(analyzed)

    # ÉTAPE 4: Génération V3
    console.print(Panel("[bold]ÉTAPE 4/4 : GÉNÉRATION V3[/bold]", style="blue"))

    # Éditorial simulé (sans API) — format V3 en 4 parties
    editorial = """Vos clients épargnent de plus en plus hors de chez vous — et ce n'est pas qu'une question de taux.

En 2025, 34% de la collecte nette en assurance-vie a été captée par des acteurs non-bancaires — contre 18% cinq ans plus tôt (Banque de France, janvier 2026). Les banques françaises perdent du terrain sur leur métier historique de collecte.

Trois dynamiques convergent. Premièrement, la montée en puissance des assureurs et gestionnaires d'actifs dans la distribution de produits d'épargne retraite rogne les parts de marché bancaires sur leur terrain historique. Deuxièmement, la digitalisation des parcours souscription — portée par des acteurs comme Yomoni ou Nalo — abaisse le coût d'entrée pour le client et réduit l'avantage de la relation en agence. Troisièmement, la directive CSRD et les nouvelles exigences ESG créent un besoin de conseil patrimonial complexe que les réseaux bancaires généralistes peinent à adresser faute de formation.

<strong>Notre conviction :</strong> d'ici 2028, les banques françaises qui n'auront pas construit une offre d'épargne retraite autonome — hors réseaux tiers — auront perdu entre 15 et 20% de leur PNB patrimonial sans possibilité de retour."""

    terrain = {
        "title": "Optimisation du réseau d'agences d'une banque régionale",
        "problem": "Une banque régionale avec 150 agences faisait face à une baisse de 30% de la fréquentation en 3 ans et une hausse des coûts fixes de 12%, menaçant la rentabilité du réseau.",
        "approach": "Diagnostic point de vente par point de vente, segmentation en 3 formats (flagship conseil, agence légère, automate+), redéploiement des effectifs vers les formats à forte valeur ajoutée.",
        "results": "Réduction de 25% des coûts de réseau en 18 mois, hausse de 15% du PNB par conseiller, NPS en progression de 12 points. Le modèle est en cours de réplication sur l'ensemble du réseau."
    }

    writer = NewsletterWriter()

    # Markdown V3
    md_content = writer.generate_markdown_v3(
        selection, month, editorial,
        partner_name="Olivier Dupin",
        terrain=terrain
    )
    md_path = writer.save_markdown(md_content, "output/newsletters", "demo-newsletter-v3.md")

    # HTML V3
    html_content = writer.generate_html_v3(
        selection=selection,
        month=month,
        editorial=editorial,
        terrain=terrain,
        partner_name="Olivier Dupin",
        logo_url=None
    )
    html_path = writer.save_html(html_content, "output/newsletters", "demo-newsletter-v3.html")

    # Résumé final
    blocs_detail = ""
    if hasattr(selection, 'blocs'):
        for bloc_id in ["essentiel", "strategies_marches", "nouveaux_modeles", "regulation"]:
            arts = selection.blocs.get(bloc_id, [])
            if arts:
                bloc_name = Curator.BLOC_NAMES.get(bloc_id, bloc_id)
                blocs_detail += f"\n- **{bloc_name}** : {len(arts)} articles"

    summary = f"""
## Démonstration V3 terminée

- **Articles simulés** : {len(articles)}
- **Articles analysés** : {len(analyzed)}
- **Articles sélectionnés** : {selection.total_selected}

### Distribution par bloc :{blocs_detail}

### Fichiers générés :
- `{md_path}`
- `{html_path}`
"""
    console.print(Panel(Markdown(summary), title="[bold green]✅ DÉMO V3 RÉUSSIE[/bold green]", style="green"))

    return md_path, html_path


if __name__ == "__main__":
    run_demo()
