# Guide Methodologique — Newsletter Banking Ares & Co

> **Document interne** | Version 1.0 — Mars 2026
> Ce guide decrit la methodologie de production de la newsletter mensuelle *Banking Insights* d'Ares & Co, de la collecte de donnees a la diffusion finale.

---

## Table des matieres

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture du pipeline](#2-architecture-du-pipeline)
3. [Etape 1 — Collecte des sources](#3-etape-1--collecte-des-sources)
4. [Etape 2 — Analyse IA](#4-etape-2--analyse-ia)
5. [Etape 3 — Curation et distribution](#5-etape-3--curation-et-distribution)
6. [Etape 4 — Redaction editoriale](#6-etape-4--redaction-editoriale)
7. [Etape 5 — Export et livrables](#7-etape-5--export-et-livrables)
8. [Ligne editoriale et persona](#8-ligne-editoriale-et-persona)
9. [Territoires editoriaux](#9-territoires-editoriaux)
10. [Tracabilite et audit](#10-tracabilite-et-audit)
11. [Resilience et reprise sur erreur](#11-resilience-et-reprise-sur-erreur)
12. [Execution pratique](#12-execution-pratique)

---

## 1. Vue d'ensemble

### Objectif

Produire chaque mois une newsletter de veille strategique bancaire a destination des Directeurs Generaux et membres de COMEX de banques francaises. La newsletter synthetise l'actualite du secteur sous un angle decisionnaire, porte par la voix d'un Senior Partner.

### Principes directeurs

| Principe | Description |
|----------|-------------|
| **Orientation decideur** | Chaque article repond a la question « *Qu'est-ce que ca change pour un DG de banque francaise ?* » |
| **Qualite MBB** | Niveau redactionnel McKinsey / BCG / Oliver Wyman |
| **Un theme, une conviction** | Chaque edition est centree sur un territoire editorial avec une prise de position tranchee |
| **Chiffres concrets** | Chaque resume contient au moins un chiffre source |
| **Tracabilite complete** | Un audit trail Excel documente chaque decision du pipeline |

### Stack technique

| Composant | Technologie |
|-----------|-------------|
| Collecte | `feedparser`, `BeautifulSoup4`, `requests`, NewsAPI |
| Analyse IA | API Claude (Anthropic) — modele `claude-sonnet-4-20250514` |
| Curation | Algorithmes de scoring, deduplication, distribution |
| Generation | `Jinja2` (HTML), `markdown` (Markdown) |
| Audit | `openpyxl` (Excel) |
| Interface | `rich` (console), CLI argparse |

---

## 2. Architecture du pipeline

Le systeme suit un pipeline sequentiel en 5 etapes, avec points de sauvegarde (checkpoints) entre chaque etape :

```
┌───────────────┐    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   COLLECTE    │───▶│   ANALYSE     │───▶│   CURATION    │───▶│   REDACTION   │───▶│    EXPORT     │
│               │    │               │    │               │    │               │    │               │
│ 15 flux RSS   │    │ Claude API    │    │ Scoring       │    │ Editorial     │    │ Markdown      │
│ 2 sites web   │    │ Categorisation│    │ Deduplication │    │ Chiffre mois  │    │ HTML email    │
│ NewsAPI (opt) │    │ Scoring 0-10  │    │ 4 blocs       │    │ Hashtags      │    │ Excel audit   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘    └───────┬───────┘    └───────────────┘
        │                    │                    │                    │
   checkpoint_           checkpoint_          checkpoint_         checkpoint_
   collecte.pkl          analyse.pkl          curation.pkl        redaction.pkl
```

**Flux de donnees typique** :
- ~120 articles bruts collectes
- ~60 articles echantillonnes pour analyse IA
- ~40 articles uniques apres deduplication
- **12-18 articles selectionnes** dans la newsletter finale

---

## 3. Etape 1 — Collecte des sources

### Sources configurees (fichier `config/sources.yaml`)

#### Regulateurs (priorite 1)
| Source | Type | Categorie |
|--------|------|-----------|
| BCE — Communiques de presse | RSS | regulateur |
| EBA — Press Releases | RSS | regulateur |
| AMF — Actualites | RSS | regulateur |
| ACPR — Actualites | Web scraping | regulateur |
| Banque de France — Publications | Web scraping | regulateur |

#### Presse specialisee
| Source | Type | Categorie |
|--------|------|-----------|
| Finextra | RSS | innovation |
| Mind Fintech | RSS | fintech |
| C'est pas mon idee | RSS | innovation |

#### Presse francaise (via Google News RSS)
| Source | Categorie |
|--------|-----------|
| Les Echos | french_banks |
| L'Agefi | french_banks |
| La Tribune | market |
| Option Finance | market |
| Revue Banque | french_banks |

#### Presse internationale (via Google News RSS)
| Source | Categorie |
|--------|-----------|
| Financial Times Banking | market |
| Wall Street Journal Finance | market |

#### NewsAPI (optionnel, necessite `NEWSAPI_KEY`)
Cible les domaines paywalled : FT.com, LesEchos.fr, WSJ.com, Reuters, Agefi.

### Traitement a la collecte

1. **Parsing RSS** via `feedparser` — extraction titre, URL, date, contenu (max 2000 caracteres)
2. **Web scraping** via `BeautifulSoup4` pour les sources sans flux RSS
3. **Nettoyage HTML** — suppression des balises, extraction du texte brut
4. **Validation des dates** — rejet des articles hors fenetre de 30 jours ou a date invalide
5. **Identification unique** — hash MD5 de l'URL (12 caracteres) comme identifiant

### Structure d'un article brut

```
Article {
    id           : str       # Hash MD5 de l'URL
    title        : str       # Titre original
    url          : str       # Lien source
    source       : str       # Nom du flux
    category     : str       # regulateur | fintech | innovation | french_banks | market
    published_date: datetime # Date de publication
    content      : str       # Contenu brut (max 2000 car.)
    summary      : str       # Resume brut (max 500 car.)
    priority     : int       # 1=haute, 2=moyenne, 3=basse
}
```

---

## 4. Etape 2 — Analyse IA

### Modele et parametrage

| Parametre | Valeur |
|-----------|--------|
| Modele | `claude-sonnet-4-20250514` |
| Timeout | 120s (total), 10s (connexion) |
| Taille batch | 3-5 articles par appel |
| Tokens max | 2048 par appel |
| Echantillonnage | Distribution temporelle uniforme sur le mois |

### Enrichissements par article

Pour chaque article, l'IA produit :

| Champ | Description |
|-------|-------------|
| `ai_summary` | Resume strategique de 2-3 phrases, incluant obligatoirement 1 chiffre concret |
| `relevance_score` | Score de pertinence 0-10 pour un decideur bancaire |
| `assigned_category` | Categorie IA (regulation, monetary_policy, innovation, fintech, french_banks, ma, market) |
| `key_facts` | 2-3 faits actionnables |
| `entities` | Entites mentionnees (banques, regulateurs, personnes) |
| `sentiment` | positive / negative / neutral |
| `newsletter_priority` | 1 (critique) a 5 (informationnel) |
| `title_fr` | Traduction francaise du titre (obligatoire si source anglophone) |

### Persona d'analyse

L'IA incarne un **Senior Partner de conseil en strategie bancaire** avec 25 ans d'experience. Le resume doit :
- Capturer l'essence strategique (pas un simple rappel des faits)
- Contenir au moins 1 chiffre concret (montant, %, ratio)
- Terminer par l'implication concrete pour un DG/CFO de banque francaise

---

## 5. Etape 3 — Curation et distribution

### Pipeline de filtrage

```
Articles analyses
    │
    ├─ 1. Filtre qualite ──────── Exclusion des resumes faibles (<50 car., formulations generiques)
    ├─ 2. Filtre date ─────────── Exclusion hors fenetre 30 jours
    ├─ 3. Filtre theme ────────── Correspondance mots-cles du theme du mois (score min 0.5)
    ├─ 4. Filtre pertinence ───── Score de pertinence >= 3.0
    ├─ 5. Deduplication ───────── Titres (40%), resumes (35%), entites (>=2 communes)
    └─ 6. Plafond par source ──── Max 3 articles par source
```

### Calcul du score final

```
score_final = score_base (0-10)
            + bonus_source      (0-1.5 selon priorite RSS)
            + bonus_priorite    (0-1.5 selon newsletter_priority)
            + bonus_recence     (0-1.0 si publie dans les 7 derniers jours)

Plafond : 15.0
```

### Distribution en 4 blocs editoriaux

| Bloc | Nom | Articles | Profondeur | Contenu |
|------|-----|----------|------------|---------|
| **1** | L'essentiel | 2-4 | Elevee (80-120 mots) | Faits saillants alimentant la these editoriale. Chaque item comporte un « A retenir » actionnable. |
| **2** | Strategies & marches | 3-6 | Moyenne (60-80 mots) | M&A, resultats structurants, mouvements concurrentiels. Max 1 item par acteur principal. |
| **3** | Nouveaux modeles | 3-5 | Moyenne (60-80 mots) | Fintech, innovations, disruptions. « Notre lecture » optionnelle (conviction Ares & Co). |
| **4** | Regulation & supervision | 3-5 | Concise (40-60 mots) | Publications BCE/EBA/AMF/ACPR, reglementation. Max 1 item par regulateur. |

### Contraintes de diversite

- **Bloc 2** : maximum 1 article par acteur principal (banque ou assureur)
- **Bloc 4** : maximum 1 article par regulateur (BCE, EBA, AMF, ACPR)
- **Global** : maximum 3 articles par source

---

## 6. Etape 4 — Redaction editoriale

### 6.1 L'editorial

Structure obligatoire en **4 parties**, 250-300 mots :

| Partie | Contenu | Volume |
|--------|---------|--------|
| **Accroche** | Point de tension formule comme une affirmation provocante. Doit creer une friction immediate. | 1-2 phrases, ~30 mots |
| **Constat ancre** | UN chiffre percutant, source, qui prouve la realite de la tension. | 2-3 phrases, ~60 mots |
| **Analyse** | 2-3 dynamiques structurantes avec connexions inattendues (FR/EU/US). Ton assertif. | 4-6 phrases, ~120 mots |
| **Conviction** | Prise de position tranchee du cabinet. Commence par « **Notre conviction :** ». Doit etre contestable. | 1-2 phrases, ~40 mots |

Signature : *— [Prenom Nom], Partner, Ares & Co*

### 6.2 Le chiffre du mois

Un KPI unique et impactant extrait des articles du mois.

Format : `VALEUR | LIBELLE | CONTEXTE`

Exemple : *2 Mds$ | Budget IA annuel de JPMorgan | soit 10% de la depense IT*

### 6.3 Les hashtags

5-6 hashtags tendance generes a partir des titres d'articles.

Format : `#NomBanque_Action` ou `#Sujet_MotCle`

Exemples : `#BCE_taux`, `#SocGen_Arkea`, `#IA_bancaire`

### 6.4 Notre lecture (Bloc 3 uniquement)

Conviction optionnelle du cabinet sur un article du Bloc « Nouveaux modeles ».
- 1 phrase, 20-30 mots max
- Prise de position (pas un commentaire neutre)
- Introduite par « *→ Notre lecture :* »

### 6.5 Terrain (cas client anonymise)

Section optionnelle en fin de newsletter. Cas client fictif mais ancre dans les thematiques du mois, illustrant une problematique bancaire concrete.

---

## 7. Etape 5 — Export et livrables

### Fichiers produits

| Livrable | Format | Contenu |
|----------|--------|---------|
| **Newsletter Markdown** | `.md` | Version texte complete : en-tete, hashtags, sommaire, editorial, chiffre, 4 blocs, terrain, footer |
| **Newsletter HTML** | `.html` | Email responsive (max 680px). Template Jinja2 V3. Compatible Outlook/Gmail/Apple Mail. |
| **Audit trail** | `.xlsx` | Classeur Excel 6 onglets (voir section 10) |

### Structure du livrable Markdown

```
En-tete (mois, theme, partner)
  └─ Hashtags
  └─ Sommaire (table des matieres avec ancres)
  └─ Editorial (4 parties + signature)
  └─ Chiffre du mois
  └─ Bloc 1 — L'essentiel (#1 a #4)
  └─ Bloc 2 — Strategies & marches (#5 a #10)
  └─ Bloc 3 — Nouveaux modeles (#11 a #15)
  └─ Bloc 4 — Regulation & supervision (#16 a #20)
  └─ Terrain (cas client)
  └─ Footer (mentions, contacts)
```

### Charte graphique HTML

Le template HTML respecte la charte Ares & Co :
- **Navy primaire** `#051E3B` pour les en-tetes
- **Bleu accent** `#57AEE0` pour les elements interactifs
- **Police** : Arial, hierarchie via taille et graisse
- **Largeur** : 700px max, breakpoint mobile a 600px
- Couleurs thematiques specifiques a chaque territoire editorial

---

## 8. Ligne editoriale et persona

### Persona : Senior Partner Banking

L'ensemble des contenus est redige du point de vue d'un Senior Partner de cabinet de conseil (25 ans d'experience bancaire). Ce positionnement garantit :

1. **Ton analytique et structure** — Faits avant interpretation, frameworks strategiques implicites
2. **Concision et impact** — Phrases courtes, un message par paragraphe
3. **Orientation decideur** — Toujours repondre au « so what? »
4. **Vision macro** — Connexions entre marches (FR/EU/US), effets de second ordre
5. **Engagement** — Assertif sans arrogance, point de vue affirme

### Regles de langue

- Francais integral (corps, titres, sources)
- Noms propres d'institutions en denomination officielle (BCE, EBA, DORA)
- **Interdits** : « paradigm shift », « best-in-class », « end-to-end », « synergies »
- Phrases courtes, verbes actifs, pas de conditionnel sauf citation

---

## 9. Territoires editoriaux

La newsletter suit un cycle de 6 themes sur 6 mois :

| Mois | Theme | Description | Couleur |
|------|-------|-------------|---------|
| Janvier | **Croissance & Distribution** | Omnicanal, bancassurance, partenariats, PNB | `#2563eb` Bleu |
| Fevrier | **Experience Client** | Parcours, NPS, fidelisation, onboarding | `#059669` Vert |
| Mars | **Performance Operationnelle** | Couts, productivite, automatisation, lean | `#dc2626` Rouge |
| Avril | **Transition Demographique** | Seniors, transmission, succession, patrimoine | `#7c3aed` Violet |
| Mai | **Epargne Retraite** | PER, assurance vie, gestion pilotee | `#ea580c` Orange |
| Juin | **Risk & Finance** | ALM, liquidite, ROE, stress tests | `#475569` Gris |

Chaque theme comporte :
- Des **mots-cles** pour le filtrage automatique des articles
- Des **questions COMEX** qui orientent l'angle editorial
- Une **couleur** utilisee dans le template HTML

---

## 10. Tracabilite et audit

Chaque execution produit un classeur Excel (`audit_YYYY-MM-DD_HH-MM-SS.xlsx`) a 6 onglets :

| Onglet | Contenu |
|--------|---------|
| **SYNTHESE** | Date, mois, theme, partner, KPI globaux (articles collectes/analyses/selectionnes), cout API estime |
| **SOURCES** | Source, URL, statut (OK/erreur/timeout), nombre d'articles, messages d'erreur |
| **ARTICLES ANALYSES** | Titre, titre FR, source, date, categorie IA, score, priorite, resume, entites, sentiment |
| **CURATION** | Article, retenu (O/N), bloc assigne, score final, raison de rejet si exclu |
| **NEWSLETTER FINALE** | Ordre de publication (#1-#N), titre, resume, bloc, source avec lien |
| **QUALITE** | Score global (0-100), diversite sources, presence de chiffres, repartition geographique, couverture thematique |

---

## 11. Resilience et reprise sur erreur

### Mecanismes de fiabilite

| Couche | Mecanisme | Detail |
|--------|-----------|--------|
| **Reseau** | Retry avec backoff exponentiel | 2^n secondes, max 30s, sur toutes les requetes HTTP |
| **API Claude** | Retry sur erreurs transitoires | 5 tentatives, backoff 2-60s. Rate limit : 30s-5min adaptatif |
| **Batch** | Fallback individuel | Si un batch echoue, bascule en analyse article par article |
| **Pipeline** | Checkpoints pickle | Sauvegarde apres chaque etape dans `.checkpoints/` |
| **Interruption** | Handlers SIGINT/SIGTERM | Sauvegarde checkpoint + message de reprise |
| **Reprise** | Flag `--resume` | Recharge le dernier checkpoint et reprend a l'etape suivante |
| **Donnees** | Analyse fallback | Si des articles echouent, le reste continue avec scoring basique |

### Flux de reprise

```
Execution interrompue (Ctrl+C, erreur reseau, etc.)
    │
    ├─ Sauvegarde automatique du checkpoint courant
    │
    └─ L'utilisateur relance avec : python src/agent.py --resume
        │
        └─ Chargement du dernier checkpoint → reprise a l'etape suivante
```

---

## 12. Execution pratique

### Prerequis

- Python 3.9+
- Cle API Anthropic (`ANTHROPIC_API_KEY` dans `.env`)
- (Optionnel) Cle NewsAPI (`NEWSAPI_KEY` dans `.env`)

### Commandes

```bash
# Installation des dependances
pip install -r requirements.txt

# Execution standard (mois courant, sans theme)
python src/agent.py

# Execution avec theme specifique
python src/agent.py --month "Mars 2026" --theme operational_performance

# Mode interactif (choix guide des parametres)
python src/agent.py --interactive

# Periode personnalisee
python src/agent.py --days 14 --max-articles 10

# Format de sortie
python src/agent.py --format html       # HTML seul
python src/agent.py --format markdown   # Markdown seul
python src/agent.py --format both       # Les deux (defaut)

# Reprise apres interruption
python src/agent.py --resume

# Mode test (sans appels API)
python src/agent.py --test
```

### Arborescence des livrables

```
banking-newsletter-agent/
├── output/
│   ├── newsletters/
│   │   ├── newsletter-banque-2026-03.md
│   │   └── newsletter-banque-2026-03.html
│   └── audit/
│       └── audit_2026-03-26_16-30-45.xlsx
└── .checkpoints/                          # Supprime apres execution reussie
```

### Cout et performance indicatifs

| Metrique | Valeur typique |
|----------|----------------|
| Duree d'execution | 5-15 minutes |
| Articles collectes | 80-120 |
| Articles selectionnes | 12-18 |
| Tokens API consommes | 30 000 - 40 000 |
| Cout API par execution | ~0.50 - 1.00 USD |
| Taille newsletter (mots) | 2 500 - 3 500 |

---

*Document genere le 26 mars 2026 — Ares & Co, Cabinet de conseil de Direction Generale*
