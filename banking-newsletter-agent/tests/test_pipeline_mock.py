#!/usr/bin/env python3
"""
Test du pipeline Newsletter V2 avec données mockées
Permet de valider le workflow sans accès réseau
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collector import Article
from analyzer import AnalyzedArticle
from curator import Curator, CuratedSelection
from writer import NewsletterWriter

# ═══════════════════════════════════════════════════════════════
# DONNÉES MOCKÉES - Articles fictifs sur le thème "Croissance & Distribution"
# ═══════════════════════════════════════════════════════════════

MOCK_ARTICLES = [
    {
        "title": "BNP Paribas lance une offensive omnicanale avec 500 agences repensées",
        "title_fr": "BNP Paribas lance une offensive omnicanale avec 500 agences repensées",
        "summary": "Le groupe bancaire français annonce un plan de transformation de son réseau d'agences, misant sur l'hybridation digital-physique.",
        "ai_summary": "BNP Paribas déploie un ambitieux programme de modernisation de 500 agences, combinant espaces de conseil premium et outils digitaux. L'objectif : réduire les transactions simples en agence de 40% tout en augmentant le temps de conseil de 60%. Un investissement de 200M€ sur 3 ans.",
        "source": "Les Echos",
        "category": "retail_banking",
        "relevance_score": 9.2,
        "entities": ["BNP Paribas", "France"],
        "key_facts": ["500 agences transformées", "200M€ investis", "Réduction 40% transactions simples"],
        "url": "https://lesechos.fr/bnp-omnicanal"
    },
    {
        "title": "Crédit Agricole et Worldline s'allient dans les paiements merchants",
        "title_fr": "Crédit Agricole et Worldline s'allient dans les paiements merchants",
        "summary": "Partenariat stratégique pour conquérir le marché des TPE/PME avec une offre intégrée banque + paiement.",
        "ai_summary": "Crédit Agricole et Worldline créent une joint-venture dédiée aux solutions de paiement pour commerçants. L'alliance cible 500 000 nouveaux clients TPE/PME d'ici 2028, avec une offre bundlée compte pro + terminal + encaissement. Potentiel de revenus additionnels estimé à 150M€/an.",
        "source": "L'Agefi",
        "category": "payments",
        "relevance_score": 8.8,
        "entities": ["Crédit Agricole", "Worldline", "France"],
        "key_facts": ["Joint-venture créée", "500K clients ciblés", "150M€ revenus potentiels"],
        "url": "https://agefi.fr/ca-worldline"
    },
    {
        "title": "ING Direct ferme ses agences physiques en France - 100% digital",
        "title_fr": "ING Direct ferme ses agences physiques en France - 100% digital",
        "summary": "La banque néerlandaise achève sa transformation vers un modèle 100% en ligne.",
        "ai_summary": "ING Direct finalise la fermeture de ses 3 derniers points de présence physique en France, confirmant son positionnement 100% digital. La banque revendique 1,2 million de clients et mise sur l'IA conversationnelle pour le service client. Coût de servicing réduit de 65% vs modèle traditionnel.",
        "source": "Finextra",
        "category": "digital_banking",
        "relevance_score": 8.5,
        "entities": ["ING", "France"],
        "key_facts": ["100% digital", "1.2M clients", "-65% coût servicing"],
        "url": "https://finextra.com/ing-digital"
    },
    {
        "title": "Société Générale déploie la bancassurance auto avec Allianz",
        "title_fr": "Société Générale déploie la bancassurance auto avec Allianz",
        "summary": "Nouveau partenariat pour distribuer l'assurance auto via le réseau bancaire.",
        "ai_summary": "Société Générale et Allianz signent un accord de distribution exclusive d'assurance auto. Les conseillers bancaires pourront proposer des contrats directement en agence, avec un objectif de 200 000 contrats la première année. Le taux de pénétration cible est de 15% de la base clients véhiculés.",
        "source": "L'Argus de l'Assurance",
        "category": "bancassurance",
        "relevance_score": 8.3,
        "entities": ["Société Générale", "Allianz", "France"],
        "key_facts": ["Partenariat exclusif", "200K contrats visés", "15% pénétration cible"],
        "url": "https://argusdelassurance.com/sg-allianz"
    },
    {
        "title": "Revolut obtient sa licence bancaire française et vise 5M de clients",
        "title_fr": "Revolut obtient sa licence bancaire française et vise 5M de clients",
        "summary": "La néobanque britannique accélère son expansion en France post-Brexit.",
        "ai_summary": "Revolut obtient l'agrément de l'ACPR et peut désormais opérer comme banque de plein exercice en France. Objectif : passer de 2,5M à 5M de clients français d'ici 2027. Lancement prévu de crédits conso et d'une offre pro renforcée. Investissement de 100M€ dans l'Hexagone.",
        "source": "Mind Fintech",
        "category": "fintech",
        "relevance_score": 9.0,
        "entities": ["Revolut", "ACPR", "France"],
        "key_facts": ["Licence bancaire obtenue", "5M clients visés", "100M€ investis"],
        "url": "https://mindfintech.fr/revolut-licence"
    },
    {
        "title": "La Banque Postale mise sur les territoires ruraux avec 2000 points de contact",
        "title_fr": "La Banque Postale mise sur les territoires ruraux avec 2000 points de contact",
        "summary": "Stratégie de maillage territorial pour capter la clientèle des zones moins denses.",
        "ai_summary": "La Banque Postale annonce le maintien de 2000 points de contact en zones rurales, à contre-courant de la tendance de fermeture d'agences. Partenariat renforcé avec les mairies pour des permanences bancaires. Objectif : +300 000 clients en zones rurales sur 3 ans.",
        "source": "La Tribune",
        "category": "retail_banking",
        "relevance_score": 8.1,
        "entities": ["La Banque Postale", "France"],
        "key_facts": ["2000 points maintenus", "+300K clients ruraux visés", "Partenariat mairies"],
        "url": "https://latribune.fr/lbp-rural"
    },
    {
        "title": "HSBC France cède sa banque de détail à My Money Group",
        "title_fr": "HSBC France cède sa banque de détail à My Money Group",
        "summary": "Retrait stratégique du marché retail français pour la banque britannique.",
        "ai_summary": "HSBC finalise la cession de ses activités de banque de détail en France (244 agences, 800 000 clients) à My Money Group pour 1,1Md€. Le groupe britannique conserve uniquement la banque privée et la BFI. Illustration de la consolidation du marché français.",
        "source": "Les Echos",
        "category": "ma_banking",
        "relevance_score": 8.7,
        "entities": ["HSBC", "My Money Group", "France"],
        "key_facts": ["Cession 1.1Md€", "244 agences", "800K clients transférés"],
        "url": "https://lesechos.fr/hsbc-cession"
    },
    {
        "title": "Orange Bank abandonne le B2C mais se renforce en B2B2C",
        "title_fr": "Orange Bank abandonne le B2C mais se renforce en B2B2C",
        "summary": "Pivot stratégique vers la distribution via partenaires après l'échec du modèle direct.",
        "ai_summary": "Orange Bank annonce l'arrêt de son offre bancaire grand public directe pour se repositionner en fournisseur de services bancaires en marque blanche. Partenariats signés avec 3 retailers majeurs. Le modèle B2B2C vise la rentabilité d'ici 2026.",
        "source": "C'est pas mon idée",
        "category": "digital_banking",
        "relevance_score": 8.4,
        "entities": ["Orange Bank", "France"],
        "key_facts": ["Arrêt B2C", "Pivot B2B2C", "3 partenaires retailers"],
        "url": "https://cestpasmonidee.fr/orange-bank"
    }
]


def create_mock_articles():
    """Crée des objets Article mockés"""
    articles = []
    base_date = datetime.now() - timedelta(days=15)

    for i, data in enumerate(MOCK_ARTICLES):
        pub_date = base_date - timedelta(days=random.randint(0, 25))

        article = Article(
            id=f"mock_{i+1}",
            title=data["title"],
            url=data["url"],
            source=data["source"],
            published_date=pub_date,
            summary=data["summary"],
            content=data["ai_summary"],
            category=data["category"],
            priority=1 if data["relevance_score"] > 8.5 else 2
        )
        articles.append(article)

    return articles


def create_mock_analyzed_articles():
    """Crée des objets AnalyzedArticle mockés"""
    articles = create_mock_articles()
    analyzed = []

    for i, (article, data) in enumerate(zip(articles, MOCK_ARTICLES)):
        analyzed_article = AnalyzedArticle(
            article=article,
            ai_summary=data["ai_summary"],
            relevance_score=data["relevance_score"],
            assigned_category=data["category"],
            key_facts=data["key_facts"],
            entities=data["entities"],
            sentiment="positive" if "lance" in data["title"].lower() or "obtient" in data["title"].lower() else "neutral",
            newsletter_priority=1 if data["relevance_score"] > 8.5 else 2,
            title_fr=data["title_fr"]
        )
        analyzed.append(analyzed_article)

    return analyzed


def test_full_pipeline():
    """Test complet du pipeline avec données mockées"""
    print("=" * 60)
    print("TEST PIPELINE NEWSLETTER V2 - DONNÉES MOCKÉES")
    print("=" * 60)

    # 1. Créer les articles mockés
    print("\n[1/4] Création des articles mockés...")
    analyzed_articles = create_mock_analyzed_articles()
    print(f"  ✓ {len(analyzed_articles)} articles créés")

    # 2. Curation avec thème
    print("\n[2/4] Curation avec thème 'growth_distribution'...")
    curator = Curator(
        min_relevance_score=3.0,
        max_articles_per_category=3,
        max_total_articles=6,
        themes_config_path="config/themes.yaml"
    )

    selection = curator.curate(analyzed_articles, theme_id="growth_distribution")
    print(f"  ✓ {selection.total_selected} articles sélectionnés")

    for cat, arts in selection.articles_by_category.items():
        if arts:
            print(f"    - {cat}: {len(arts)} articles")

    # 3. Génération éditoriale (sans API - mode simplifié)
    print("\n[3/4] Génération des contenus...")
    writer = NewsletterWriter(api_key=None)  # Sans API pour le test

    # Éditorial style McKinsey (exemple sans API)
    editorial = """Le mois de janvier 2026 acte la fin d'une illusion : celle de la banque 100% digitale comme modèle universel. Trois mouvements convergents — le pivot B2B2C d'Orange Bank, l'offensive omnicanale de BNP Paribas, et l'accélération des partenariats bancassurance — dessinent une nouvelle réalité où le "phygital" n'est plus une option mais une nécessité stratégique.

L'annonce de BNP Paribas de transformer 500 agences avec un investissement de 200M€ n'est pas un simple programme immobilier. C'est l'aveu que la relation bancaire complexe — crédit immobilier, gestion de patrimoine, accompagnement des professionnels — requiert une présence physique réinventée. Dans le même temps, Orange Bank tire les leçons de sept années d'expérimentation directe : le coût d'acquisition client en B2C digital dépasse désormais 300€, rendant le modèle structurellement déficitaire sur le segment mass market. Le pivot vers le B2B2C, avec trois partenariats retailers annoncés, traduit une recherche de distribution à coût marginal proche de zéro.

Cette recomposition n'est pas neutre pour les acteurs établis. L'alliance Crédit Agricole-Worldline sur les paiements merchants, ciblant 500 000 TPE/PME, illustre une stratégie de bundling défensif face à la montée des néobanques sur le segment professionnel. Quant à la cession par HSBC de ses 244 agences à My Money Group pour 1,1Md€, elle confirme que le retail banking français n'offre plus de perspectives de rentabilité suffisantes pour un acteur international non-leader.

Pour les dirigeants bancaires, ces signaux posent une question stratégique immédiate : comment optimiser le ratio coût/valeur de chaque canal tout en préservant la capacité à capter les moments de vie à forte valeur ? Les banques qui sauront articuler digital transactionnel et physique relationnel creuseront l'écart avec celles qui resteront dans un "ni-ni" mal assumé.

**Notre conviction : d'ici 2028, le marché français ne comptera plus que deux modèles viables — les réseaux "phygitaux" intégrés des bancassureurs et les pure players spécialisés sur des niches à forte valeur. Le milieu de gamme digital généraliste aura disparu.**"""

    # Point de vue Ares simplifié
    ares_view = {
        "title": "La fin du mythe de la banque 100% digitale ?",
        "content": """Les derniers mouvements du marché révèlent une réalité que nous anticipions : le modèle
100% digital atteint ses limites pour une clientèle mass market. ING ferme ses agences, Orange Bank
pivote vers le B2B2C, tandis que BNP et La Banque Postale réinvestissent le physique.

Notre conviction : la banque de demain sera **phygitale par nécessité**, pas par choix. Les pure players
qui survivront seront ceux qui auront trouvé des relais de distribution physique via des partenariats.""",
        "author": "Équipe Banking - Ares & Co"
    }

    # Terrain (mini-cas)
    terrain = {
        "title": "Optimisation du réseau d'agences d'une banque régionale",
        "problem": "Une banque régionale avec 150 agences faisait face à une baisse de 30% de la fréquentation et une hausse des coûts fixes.",
        "approach": "Diagnostic de chaque point de vente, segmentation en 3 formats (flagship, conseil, automate+), redéploiement des effectifs.",
        "results": "Réduction de 25% des coûts de réseau, hausse de 15% du PNB par conseiller, NPS en progression de 12 points."
    }

    print("  ✓ Éditorial généré")
    print("  ✓ Point de vue Ares généré")
    print("  ✓ Terrain Ares généré")

    # 4. Génération HTML V2
    print("\n[4/4] Génération du HTML V2...")
    html_content = writer.generate_html_v2(
        selection=selection,
        month="Janvier 2026",
        editorial=editorial,
        ares_view=ares_view,
        terrain=terrain,
        logo_url=None
    )

    # Sauvegarder
    output_path = writer.save_html(html_content, "output/newsletters")
    print(f"  ✓ HTML généré: {output_path}")

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSULTAT DU TEST")
    print("=" * 60)
    print(f"  Articles mockés:     {len(analyzed_articles)}")
    print(f"  Articles sélectionnés: {selection.total_selected}")
    print(f"  Thème:               {selection.theme_name or 'N/A'}")
    print(f"  Fichier généré:      {output_path}")
    print("\n✅ Test réussi ! Ouvrez le fichier HTML pour vérifier le rendu.")

    return output_path


if __name__ == "__main__":
    test_full_pipeline()
