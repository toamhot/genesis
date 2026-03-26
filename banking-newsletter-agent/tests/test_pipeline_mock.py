#!/usr/bin/env python3
"""
Test du pipeline Newsletter V3 avec données mockées
Permet de valider le workflow V3 (4 blocs éditoriaux) sans accès réseau
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
# DONNÉES MOCKÉES — Articles répartis pour les 4 blocs
# ═══════════════════════════════════════════════════════════════

MOCK_ARTICLES = [
    # Stratégies & marchés (french_banks, ma, market)
    {
        "title": "BNP Paribas lance une offensive omnicanale avec 500 agences repensées",
        "title_fr": "BNP Paribas lance une offensive omnicanale avec 500 agences repensées",
        "ai_summary": "BNP Paribas engage 200M€ pour transformer 500 agences en combinant espaces de conseil premium et outils digitaux. L'objectif — réduire les transactions simples de 40% tout en augmentant le temps de conseil de 60% — traduit un repositionnement du réseau vers la valeur ajoutée relationnelle.",
        "source": "Les Echos",
        "category": "french_banks",
        "relevance_score": 9.2,
        "entities": ["BNP Paribas", "France"],
        "key_facts": ["500 agences transformées", "200M€ investis"],
        "url": "https://example.com/bnp-omnicanal"
    },
    {
        "title": "HSBC France cède sa banque de détail à My Money Group pour 1,1 Md€",
        "title_fr": "HSBC France cède sa banque de détail à My Money Group pour 1,1 Md€",
        "ai_summary": "HSBC finalise la cession de ses 244 agences et 800 000 clients à My Money Group pour 1,1 Md€. Le groupe conserve uniquement banque privée et BFI en France. Cette opération illustre la difficulté pour un acteur international non-leader à atteindre une rentabilité suffisante sur le retail français.",
        "source": "Les Echos",
        "category": "ma",
        "relevance_score": 8.7,
        "entities": ["HSBC", "My Money Group", "France"],
        "key_facts": ["1,1 Md€", "244 agences", "800K clients"],
        "url": "https://example.com/hsbc-cession"
    },
    {
        "title": "Société Générale finalise la cession de Rosbank",
        "title_fr": "Société Générale finalise la cession de ses activités en Russie",
        "ai_summary": "Société Générale clôt 20 ans de présence en Russie avec la cession de Rosbank, libérant 20 bps de CET1. Le recentrage européen du groupe est confirmé, avec un redéploiement de 3 Md€ de capital vers la banque de détail France et la BFI Europe.",
        "source": "Les Echos",
        "category": "ma",
        "relevance_score": 7.5,
        "entities": ["Société Générale", "Rosbank"],
        "key_facts": ["CET1 +20 bps", "Fin de 20 ans de présence"],
        "url": "https://example.com/sg-rosbank"
    },
    # Nouveaux modèles (innovation, fintech)
    {
        "title": "Crédit Agricole lance une offre Banking-as-a-Service",
        "title_fr": "Crédit Agricole lance une offre de Banking-as-a-Service",
        "ai_summary": "Le Crédit Agricole ouvre en bêta fermée sa plateforme BaaS permettant à des enseignes retail d'intégrer des services financiers dans leur parcours client. L'offre cible la grande distribution et le e-commerce, positionnant CA comme infrastructure financière pour des acteurs non-bancaires.",
        "source": "Mind Fintech",
        "category": "innovation",
        "relevance_score": 7.2,
        "entities": ["Crédit Agricole"],
        "key_facts": ["Plateforme API complète", "50 clients visés"],
        "url": "https://example.com/ca-baas"
    },
    {
        "title": "Revolut obtient sa licence bancaire française",
        "title_fr": "Revolut obtient sa licence bancaire française et vise 5M de clients",
        "ai_summary": "Revolut obtient l'agrément ACPR et peut opérer comme banque de plein exercice en France. Objectif : passer de 2,5M à 5M de clients français d'ici 2027 avec lancement de crédits conso et offre pro renforcée. Un investissement de 100M€ dans l'Hexagone est annoncé.",
        "source": "Mind Fintech",
        "category": "fintech",
        "relevance_score": 9.0,
        "entities": ["Revolut", "ACPR", "France"],
        "key_facts": ["Licence bancaire obtenue", "5M clients visés"],
        "url": "https://example.com/revolut-licence"
    },
    # Régulation & supervision (regulation, monetary_policy, regulateur)
    {
        "title": "DORA : 85% des banques européennes conformes",
        "title_fr": "DORA : 85% des banques européennes conformes ou en voie de l'être",
        "ai_summary": "L'EBA publie un état des lieux de la conformité DORA : 85% des banques déclarent être conformes ou en voie de l'être. Les 15% restants sont principalement des établissements de taille intermédiaire. L'ACPR prévoit des contrôles ciblés dès le T2 2026.",
        "source": "EBA - Communiqué officiel",
        "category": "regulation",
        "relevance_score": 8.0,
        "entities": ["EBA", "DORA", "ACPR"],
        "key_facts": ["85% conformes", "Contrôles ACPR T2 2026"],
        "url": "https://example.com/dora-conformite"
    },
    {
        "title": "Report du FRTB au 1er janvier 2027",
        "title_fr": "Report d'un an pour le FRTB : application au 1er janvier 2027",
        "ai_summary": "La Commission européenne reporte d'un an le FRTB (Fundamental Review of the Trading Book), repoussant l'échéance au 1er janvier 2027. Ce report aligne le calendrier européen sur le Comité de Bâle. Pour les banques actives en BFI, ce délai permet d'affiner les modèles internes mais retarde une charge en capital de 5 à 15%.",
        "source": "Commission Européenne",
        "category": "regulation",
        "relevance_score": 8.2,
        "entities": ["Commission Européenne", "EBA", "Comité de Bâle"],
        "key_facts": ["Report au 1er janvier 2027", "+5-15% charge capital"],
        "url": "https://example.com/frtb-report"
    },
    {
        "title": "AMLA opérationnelle depuis le 1er janvier 2026",
        "title_fr": "AMLA opérationnelle : transfert des compétences AML depuis l'EBA",
        "ai_summary": "L'AMLA est pleinement opérationnelle après le transfert des compétences LCB-FT de l'EBA. Basée à Francfort, elle supervisera directement les 40 établissements européens à plus haut risque. Pour les banques françaises, cela implique un double reporting — ACPR et AMLA — et une révision des dispositifs de conformité d'ici mi-2027.",
        "source": "EBA - Communiqué officiel",
        "category": "regulation",
        "relevance_score": 8.8,
        "entities": ["AMLA", "EBA", "ACPR"],
        "key_facts": ["Transfert au 1er janvier 2026", "40 établissements supervisés"],
        "url": "https://example.com/amla-operationnel"
    }
]


def create_mock_analyzed_articles():
    """Crée des objets AnalyzedArticle mockés"""
    analyzed = []
    base_date = datetime.now() - timedelta(days=15)

    for i, data in enumerate(MOCK_ARTICLES):
        pub_date = base_date - timedelta(days=random.randint(0, 25))

        article = Article(
            id=f"mock_{i+1}",
            title=data["title"],
            url=data["url"],
            source=data["source"],
            published_date=pub_date,
            summary=data["ai_summary"][:200],
            content=data["ai_summary"],
            category=data["category"],
            priority=1 if data["relevance_score"] > 8.5 else 2
        )

        analyzed.append(AnalyzedArticle(
            article=article,
            ai_summary=data["ai_summary"],
            relevance_score=data["relevance_score"],
            assigned_category=data["category"],
            key_facts=data["key_facts"],
            entities=data["entities"],
            sentiment="neutral",
            newsletter_priority=1 if data["relevance_score"] > 8.5 else 2,
            title_fr=data["title_fr"]
        ))

    return analyzed


def test_full_pipeline():
    """Test complet du pipeline V3 avec données mockées"""
    print("=" * 60)
    print("TEST PIPELINE NEWSLETTER V3 - DONNÉES MOCKÉES")
    print("=" * 60)

    # 1. Créer les articles mockés
    print("\n[1/4] Création des articles mockés...")
    analyzed_articles = create_mock_analyzed_articles()
    print(f"  ✓ {len(analyzed_articles)} articles créés")

    # 2. Curation V3 — distribution en 4 blocs
    print("\n[2/4] Curation V3 — distribution en 4 blocs...")
    curator = Curator(
        min_relevance_score=3.0,
        max_total_articles=12,
        themes_config_path="config/themes.yaml"
    )

    selection = curator.curate(analyzed_articles, theme_id="growth_distribution")
    print(f"  ✓ {selection.total_selected} articles sélectionnés")

    # Vérifier la distribution par bloc
    for bloc_id in Curator.BLOC_ORDER:
        arts = selection.blocs.get(bloc_id, [])
        bloc_name = Curator.BLOC_NAMES.get(bloc_id, bloc_id)
        print(f"    - {bloc_name}: {len(arts)} articles")
        for a in arts:
            print(f"      • {a.title_fr or a.article.title}")

    # 3. Génération des contenus (sans API)
    print("\n[3/4] Génération des contenus V3...")
    writer = NewsletterWriter(api_key=None)

    # Éditorial simulé — format V3 en 4 parties
    editorial = """Vos clients épargnent de plus en plus hors de chez vous — et ce n'est pas qu'une question de taux.

En 2025, 34% de la collecte nette en assurance-vie a été captée par des acteurs non-bancaires — contre 18% cinq ans plus tôt (Banque de France, janvier 2026).

Trois dynamiques convergent. La montée en puissance des assureurs dans la distribution d'épargne retraite rogne les parts de marché bancaires. La digitalisation des parcours souscription abaisse le coût d'entrée pour le client. La directive CSRD crée un besoin de conseil patrimonial complexe que les réseaux généralistes peinent à adresser.

<strong>Notre conviction :</strong> d'ici 2028, les banques françaises qui n'auront pas construit une offre d'épargne retraite autonome auront perdu entre 15 et 20% de leur PNB patrimonial sans possibilité de retour."""

    terrain = {
        "title": "Optimisation du réseau d'agences d'une banque régionale",
        "problem": "Une banque régionale avec 150 agences faisait face à une baisse de 30% de la fréquentation.",
        "approach": "Diagnostic point de vente, segmentation en 3 formats, redéploiement des effectifs.",
        "results": "Réduction de 25% des coûts de réseau, hausse de 15% du PNB par conseiller."
    }

    print("  ✓ Éditorial V3 (4 parties)")
    print("  ✓ Terrain Ares & Co")

    # 4. Génération HTML V3
    print("\n[4/4] Génération du HTML V3...")
    html_content = writer.generate_html_v3(
        selection=selection,
        month="Mars 2026",
        editorial=editorial,
        terrain=terrain,
        partner_name="Olivier Dupin",
        logo_url=None
    )

    output_path = writer.save_html(html_content, "output/newsletters", "test-newsletter-v3.html")
    print(f"  ✓ HTML V3 généré: {output_path}")

    # Markdown V3
    md_content = writer.generate_markdown_v3(
        selection=selection,
        month="Mars 2026",
        editorial=editorial,
        partner_name="Olivier Dupin",
        terrain=terrain
    )
    md_path = writer.save_markdown(md_content, "output/newsletters", "test-newsletter-v3.md")
    print(f"  ✓ Markdown V3 généré: {md_path}")

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSULTAT DU TEST V3")
    print("=" * 60)
    print(f"  Articles mockés:       {len(analyzed_articles)}")
    print(f"  Articles sélectionnés: {selection.total_selected}")
    print(f"  Blocs:")
    for bloc_id in Curator.BLOC_ORDER:
        arts = selection.blocs.get(bloc_id, [])
        bloc_name = Curator.BLOC_NAMES.get(bloc_id, bloc_id)
        print(f"    {bloc_name}: {len(arts)}")
    print(f"  Fichiers générés:      {output_path}, {md_path}")
    print("\n✅ Test V3 réussi ! Ouvrez le fichier HTML pour vérifier le rendu.")

    return output_path


if __name__ == "__main__":
    test_full_pipeline()
