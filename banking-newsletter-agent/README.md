# Banking Newsletter Agent

**Ares & Co** - Agent automatisé de génération de newsletter bancaire

## Description

Cet agent automatise la veille et la génération de newsletters mensuelles sur le secteur bancaire européen. Il collecte les actualités depuis diverses sources (régulateurs, presse spécialisée, fintech), les analyse avec Claude AI, et génère une newsletter professionnelle.

## Fonctionnalités

- **Collecte automatique** : Flux RSS (BCE, EBA, Finextra...) + scraping web
- **Analyse IA** : Résumé, scoring de pertinence, catégorisation via Claude API
- **Curation intelligente** : Sélection et déduplication des articles les plus pertinents
- **Génération automatisée** : Newsletter Markdown et HTML professionnelle

## Installation

```bash
# Cloner le projet
cd banking-newsletter-agent

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

### Clé API Claude

```bash
export ANTHROPIC_API_KEY="votre-clé-api"
```

### Sources de veille

Modifier `config/sources.yaml` pour ajouter/supprimer des sources :

```yaml
rss_feeds:
  - name: "BCE - Communiqués"
    url: "https://www.ecb.europa.eu/rss/press.html"
    category: "regulateur"
    priority: 1
```

## Utilisation

### Génération standard

```bash
python src/agent.py
```

### Options

```bash
# Mois spécifique
python src/agent.py --month "Février 2026"

# Format HTML (pour diffusion)
python src/agent.py --format html

# Les deux formats
python src/agent.py --format both

# Période personnalisée (14 derniers jours)
python src/agent.py --days 14

# Mode test (sans appels API Claude)
python src/agent.py --test

# Mode interactif
python src/agent.py --interactive

# Avec logo pour le HTML
python src/agent.py --format html --logo-url "https://example.com/logo.png"
```

### Exemples

```bash
# Newsletter de février, formats Markdown + HTML
python src/agent.py -m "Février 2026" -f both

# Test rapide sur 7 jours, 10 articles max
python src/agent.py -d 7 --max-articles 10 --test
```

## Architecture

```
banking-newsletter-agent/
├── config/
│   └── sources.yaml      # Configuration des sources
├── src/
│   ├── agent.py          # Agent principal (orchestration)
│   ├── collector.py      # Collecte RSS + web
│   ├── analyzer.py       # Analyse Claude API
│   ├── curator.py        # Curation et sélection
│   └── writer.py         # Génération newsletter
├── output/
│   └── newsletters/      # Fichiers générés
└── requirements.txt
```

## Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  COLLECTE   │────▶│  ANALYSE    │────▶│  CURATION   │────▶│  RÉDACTION  │
│             │     │             │     │             │     │             │
│ • RSS       │     │ • Résumé IA │     │ • Scoring   │     │ • Éditorial │
│ • Scraping  │     │ • Catégorie │     │ • Sélection │     │ • Markdown  │
│ • Filtrage  │     │ • Scoring   │     │ • Groupement│     │ • HTML      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## Sources configurées par défaut

| Source | Type | Catégorie |
|--------|------|-----------|
| BCE | RSS | Régulateur |
| EBA | RSS | Régulateur |
| Banque de France | RSS | Régulateur |
| France FinTech | RSS | Fintech |
| Finextra | RSS | Innovation |
| ACPR | Web | Régulateur |

## Coûts API

Estimation pour une newsletter mensuelle (~50 articles analysés) :
- **Claude Sonnet** : ~$0.50 - $1.00 par exécution
- Mode `--test` : $0 (pas d'appels API)

## Personnalisation

### Ajouter une source RSS

Dans `config/sources.yaml` :

```yaml
rss_feeds:
  - name: "Ma nouvelle source"
    url: "https://example.com/feed.xml"
    category: "innovation"  # ou: regulateur, fintech, etc.
    priority: 2  # 1=haute, 2=moyenne, 3=basse
```

### Modifier les critères de curation

Dans `src/agent.py`, ajuster les paramètres du `Curator` :

```python
self.curator = Curator(
    min_relevance_score=6.0,      # Score minimum (0-10)
    max_articles_per_category=4,   # Articles par catégorie
    max_total_articles=12          # Total dans la newsletter
)
```

## Support

Pour toute question sur l'utilisation de cet agent, contactez l'équipe Ares & Co.

---

*Développé pour Ares & Co - Cabinet de Conseil en Stratégie*
