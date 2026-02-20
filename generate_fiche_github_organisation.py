"""Fiche de recommandation - Mise en place d'un GitHub Organisation pour Ares & Co"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

# Genesis colors
NAVY_PRIMARY = RGBColor(0x05, 0x1E, 0x3B)
NAVY_SECONDARY = RGBColor(0x05, 0x1E, 0x5B)
ACCENT_BLUE = RGBColor(0x57, 0xAE, 0xE0)
TEXT_COLOR = RGBColor(0x2D, 0x37, 0x48)
GRAY = RGBColor(0x66, 0x66, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x05, 0x96, 0x69)
ORANGE = RGBColor(0xEA, 0x58, 0x0C)

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)

style = doc.styles['Normal']
style.font.name = 'Arial'
style.font.size = Pt(10)
style.font.color.rgb = TEXT_COLOR

h1 = doc.styles['Heading 1']
h1.font.name = 'Arial'
h1.font.size = Pt(14)
h1.font.color.rgb = NAVY_PRIMARY
h1.font.bold = True
h1.paragraph_format.space_before = Pt(18)
h1.paragraph_format.space_after = Pt(8)

h2 = doc.styles['Heading 2']
h2.font.name = 'Arial'
h2.font.size = Pt(12)
h2.font.color.rgb = NAVY_SECONDARY
h2.font.bold = True
h2.paragraph_format.space_before = Pt(14)
h2.paragraph_format.space_after = Pt(6)

def set_cell_shading(cell, hex_color):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def set_cell_text(cell, text, bold=False, color=TEXT_COLOR, size=Pt(9)):
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = size
    run.font.bold = bold
    run.font.color.rgb = color

def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1+len(rows), cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        set_cell_shading(table.rows[0].cells[i], "051E3B")
        set_cell_text(table.rows[0].cells[i], h, bold=True, color=WHITE)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            if r % 2 == 1:
                set_cell_shading(table.rows[r+1].cells[c], "F0F4F8")
            set_cell_text(table.rows[r+1].cells[c], val)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph()

def add_code(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        run = p.add_run(line)
        run.font.name = 'Consolas'
        run.font.size = Pt(9)
        run.font.color.rgb = NAVY_SECONDARY

def add_tip(doc, text, icon="💡"):
    table = doc.add_table(rows=1, cols=1)
    table.style = 'Table Grid'
    cell = table.rows[0].cells[0]
    set_cell_shading(cell, "E8F5E9")
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(f"{icon} {text}")
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.color.rgb = GREEN
    doc.add_paragraph()

def add_warning(doc, text):
    table = doc.add_table(rows=1, cols=1)
    table.style = 'Table Grid'
    cell = table.rows[0].cells[0]
    set_cell_shading(cell, "FFF3E0")
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(f"⚠️ {text}")
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.color.rgb = ORANGE
    doc.add_paragraph()

def add_success(doc, text):
    table = doc.add_table(rows=1, cols=1)
    table.style = 'Table Grid'
    cell = table.rows[0].cells[0]
    set_cell_shading(cell, "E3F2FD")
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run("✓ ")
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.color.rgb = TEXT_COLOR
    doc.add_paragraph()

def add_body(doc, text):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(6)

def add_bullet(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Cm(1)
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.font.bold = True
        run = p.add_run(text)
    else:
        p.add_run(text)

def add_numbered(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style='List Number')
    p.paragraph_format.left_indent = Cm(1)
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.font.bold = True
        run = p.add_run(text)
    else:
        p.add_run(text)

def add_flow_diagram(doc, steps, title=None):
    if title:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"📊 {title}")
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = NAVY_SECONDARY

    num_cols = len(steps) * 2 - 1
    table = doc.add_table(rows=1, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, step in enumerate(steps):
        cell_idx = i * 2
        cell = table.rows[0].cells[cell_idx]
        if i == 0 or i == len(steps) - 1:
            set_cell_shading(cell, "051E3B")
        else:
            set_cell_shading(cell, "57AEE0")
        set_cell_text(cell, step, bold=True, color=WHITE, size=Pt(8))
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cell.width = Cm(2.5)

        if i < len(steps) - 1:
            arrow_cell = table.rows[0].cells[cell_idx + 1]
            arrow_cell.text = ""
            p = arrow_cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" → ")
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = ACCENT_BLUE
            arrow_cell.width = Cm(0.8)

    doc.add_paragraph()


# ========================================
# PAGE DE TITRE
# ========================================
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(30)
run = p.add_run("NOTE DE RECOMMANDATION — GENESIS")
run.font.name = 'Arial'
run.font.size = Pt(10)
run.font.bold = True
run.font.color.rgb = ACCENT_BLUE

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(15)
run = p.add_run("MISE EN PLACE D'UN GITHUB ORGANISATION")
run.font.name = 'Arial'
run.font.size = Pt(18)
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Guidelines pour l'expérimentation et le passage à l'échelle")
run.font.name = 'Arial'
run.font.size = Pt(12)
run.font.color.rgb = NAVY_SECONDARY

doc.add_paragraph()
doc.add_paragraph()

# Metadata
table = doc.add_table(rows=5, cols=2)
table.style = 'Table Grid'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
meta = [
    ("Type de document", "Recommandation transverse — Guidelines de développement"),
    ("Destinataires", "Direction, IT, Consultants seniors"),
    ("Contexte", "Structurer les pratiques de développement d'agents IA au sein du cabinet"),
    ("Principe clé", "Infrastructure agnostique du LLM — compatible Claude, GPT, Mistral, Llama, etc."),
    ("Effort de mise en place", "2-3 heures (création) + 30 min/consultant (onboarding)"),
]
for i, (k, v) in enumerate(meta):
    set_cell_shading(table.rows[i].cells[0], "F0F4F8")
    set_cell_text(table.rows[i].cells[0], k, bold=True, color=NAVY_PRIMARY, size=Pt(10))
    set_cell_text(table.rows[i].cells[1], v, size=Pt(10))
    table.rows[i].cells[0].width = Cm(4.5)
    table.rows[i].cells[1].width = Cm(11.5)

doc.add_paragraph()

# Executive summary
p = doc.add_paragraph()
run = p.add_run("Synthèse")
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY
run.font.size = Pt(11)

add_body(doc, "Ares & Co initie une démarche de développement d'agents IA pour renforcer ses capacités internes (newsletter automatisée, outils d'analyse, automatisations). Il n'existe pas aujourd'hui de pratique formalisée de développement au sein du cabinet. Cette note propose les guidelines nécessaires pour structurer cette activité naissante : d'abord dans une logique d'expérimentation (quelques consultants, un premier projet pilote), puis dans une perspective de passage à l'échelle (multiplication des agents, collaboration entre équipes).")

add_body(doc, "La recommandation centrale est la mise en place d'une organisation GitHub comme socle technique commun. Cette infrastructure est volontairement agnostique du choix de LLM : elle fonctionne de la même manière que le code s'appuie sur Claude (Anthropic), GPT (OpenAI), Mistral, Llama (Meta), ou tout autre modèle. Le choix du LLM est une décision indépendante, qui peut évoluer dans le temps sans impacter l'infrastructure de versioning et de collaboration.")

doc.add_page_break()

# ========================================
# SECTION 1: CONSTAT
# ========================================
doc.add_heading("1. Contexte : une activité de développement naissante", level=1)

add_body(doc, "Ares & Co est un cabinet de conseil de Direction Générale. Le développement logiciel ne fait pas partie de son cœur de métier. Cependant, l'émergence des LLMs (Claude, GPT, Mistral, etc.) ouvre des opportunités concrètes pour créer des outils internes augmentés par l'IA : newsletters automatisées, agents d'analyse sectorielle, automatisations de reporting.")

add_body(doc, "Aujourd'hui, il n'existe pas de pratique formalisée de développement au sein du cabinet. Les premières expérimentations (projet newsletter) sont menées de façon individuelle, sur les postes des consultants. Cette situation est normale à ce stade, mais elle ne peut pas durer si l'ambition est de passer à l'échelle.")

doc.add_heading("1.1 Ce qui fonctionne en phase d'expérimentation", level=2)

add_bullet(doc, "Un consultant explore une idée seul, sur son PC")
add_bullet(doc, "Prototypage rapide avec Claude Code ou un autre assistant IA")
add_bullet(doc, "Résultat : un premier MVP qui valide le concept")

doc.add_heading("1.2 Ce qui bloque pour passer à l'échelle", level=2)

add_table(doc, ["Problème", "Impact en phase d'expérimentation", "Impact à l'échelle"],
    [["Code sur un seul PC", "Acceptable", "Risque de perte critique"],
     ["Pas de partage", "Non bloquant (1 personne)", "Impossible de collaborer"],
     ["Pas d'historique", "Gérable manuellement", "Impossible de tracer les évolutions"],
     ["Pas de revue qualité", "Tolérable pour un prototype", "Risque d'erreurs en production"],
     ["Secrets dans le code", "Risque limité", "Risque de fuite avec la multiplication des copies"],
     ["Pas de standards", "Non pertinent (1 projet)", "Chaque consultant fait différemment"]],
    col_widths=[3.5, 6.25, 6.25])

add_body(doc, "La mise en place d'une infrastructure GitHub permet de résoudre ces problèmes dès maintenant, de façon progressive et sans freiner les expérimentations en cours.")

doc.add_page_break()

# ========================================
# SECTION 2: RECOMMANDATION
# ========================================
doc.add_heading("2. Recommandation : créer une organisation GitHub", level=1)

doc.add_heading("2.1 Qu'est-ce qu'une organisation GitHub ?", level=2)

add_body(doc, "Une organisation GitHub est un espace partagé qui regroupe :")

add_bullet(doc, "Les repositories (projets) de l'entreprise", bold_prefix="Repositories : ")
add_bullet(doc, "Les membres avec leurs droits d'accès", bold_prefix="Équipes : ")
add_bullet(doc, "Les paramètres de sécurité communs", bold_prefix="Gouvernance : ")

add_body(doc, "C'est l'équivalent d'un drive partagé, mais optimisé pour le code et avec un historique complet de toutes les modifications.")

doc.add_heading("2.2 Pourquoi GitHub plutôt qu'un autre outil ?", level=2)

add_table(doc, ["Critère", "GitHub", "Alternatives (GitLab, Bitbucket, Azure DevOps)"],
    [["Adoption mondiale", "Standard de facto, 100M+ utilisateurs", "Moins répandus"],
     ["Intégration assistants IA", "Claude Code, GitHub Copilot, Cursor, Continue", "Compatibles mais intégration moins directe"],
     ["Courbe d'apprentissage", "Documentation abondante, tutoriels", "Similaire"],
     ["Coût", "Gratuit (repos privés illimités)", "Gratuit aussi"],
     ["Interface", "Simple et intuitive", "Plus complexe (GitLab/Azure)"],
     ["Communauté", "Immense, réponses rapides", "Plus restreinte"]],
    col_widths=[3.5, 6.25, 6.25])

add_tip(doc, "GitHub est le choix naturel pour des consultants qui débutent en développement. L'écosystème est le plus mature et compatible avec tous les assistants IA de code du marché.")

doc.add_heading("2.3 Un socle agnostique du choix de LLM", level=2)

add_body(doc, "Un point fondamental : l'infrastructure GitHub est totalement indépendante du LLM utilisé. Le code versionné sur GitHub peut s'appuyer sur n'importe quel modèle d'IA :")

add_table(doc, ["Couche", "Rôle", "Exemples d'options"],
    [["Infrastructure de code", "Versionner, collaborer, sécuriser", "GitHub (recommandé) — choix unique, stable"],
     ["Assistant de développement", "Aider le consultant à coder", "Claude Code, GitHub Copilot, Cursor, Continue + Ollama"],
     ["LLM dans le produit", "IA intégrée dans l'agent créé", "Claude API, GPT API, Mistral API, Ollama (local)"]],
    col_widths=[3.5, 5, 7.5])

add_body(doc, "Ces trois couches sont indépendantes. On peut par exemple :")

add_bullet(doc, "utiliser Claude Code pour le développement, mais GPT dans le produit final")
add_bullet(doc, "commencer avec Claude API puis migrer vers un modèle local (Ollama)")
add_bullet(doc, "laisser chaque consultant choisir son assistant de développement préféré")

add_body(doc, "GitHub reste le socle commun quelle que soit la combinaison choisie. Le choix du LLM est une décision réversible qui peut évoluer au fil du temps (nouveaux modèles, évolution des prix, exigences de confidentialité) sans jamais remettre en cause l'infrastructure de collaboration.")

add_warning(doc, "En revanche, l'absence d'infrastructure Git rend difficile tout changement futur : si le code est dispersé sur les PC des consultants, migrer d'un LLM à un autre est un effort considérable projet par projet.")

doc.add_page_break()

# ========================================
# SECTION 3: BÉNÉFICES
# ========================================
doc.add_heading("3. Bénéfices concrets", level=1)

doc.add_heading("3.1 Pour les consultants", level=2)

add_table(doc, ["Avant (local)", "Après (GitHub Organisation)"],
    [["\"Où est la dernière version ?\"", "Toujours sur la branche main"],
     ["\"J'ai perdu mon code\"", "Récupérable en 1 commande (git clone)"],
     ["\"Comment je récupère le projet de Paul ?\"", "Accès immédiat à tous les repos"],
     ["\"Je ne comprends pas ce code\"", "Historique des commits explique le contexte"],
     ["\"J'ai peur de casser quelque chose\"", "Branches + Pull Requests = filet de sécurité"],
     ["\"Ma clé API est dans le .zip\"", "Secrets gérés séparément (.env ignoré)"]],
    col_widths=[8, 8])

doc.add_heading("3.2 Pour le cabinet", level=2)

add_bullet(doc, "Le code survit aux départs de consultants", bold_prefix="Pérennité : ")
add_bullet(doc, "Tous les projets au même endroit, accessibles à tous", bold_prefix="Capitalisation : ")
add_bullet(doc, "Revue de code avant mise en production", bold_prefix="Qualité : ")
add_bullet(doc, "Secrets séparés du code, accès contrôlés", bold_prefix="Sécurité : ")
add_bullet(doc, "Possibilité d'automatiser tests et déploiements", bold_prefix="Automatisation : ")

doc.add_heading("3.3 Coûts", level=2)

add_table(doc, ["Élément", "Coût"],
    [["Organisation GitHub (Team)", "Gratuit (repos privés illimités)"],
     ["Option GitHub Team (fonctions avancées)", "~4$/utilisateur/mois si nécessaire"],
     ["Temps de setup initial", "2-3 heures (une seule fois)"],
     ["Onboarding par consultant", "30 minutes (formation + premier clone)"]],
    col_widths=[10, 6])

add_success(doc, "Pour un usage standard (repos privés, équipe < 50 personnes), le plan gratuit de GitHub suffit largement.")

doc.add_page_break()

# ========================================
# SECTION 4: MISE EN PLACE
# ========================================
doc.add_heading("4. Guide de mise en place", level=1)

doc.add_heading("4.1 Étape 1 : Créer l'organisation", level=2)

add_code(doc, [
    "1. Aller sur https://github.com/organizations/plan",
    "",
    "2. Cliquer \"Create a free organization\"",
    "",
    "3. Renseigner :",
    "   - Organization name : aresandco (ou ares-and-co)",
    "   - Contact email : it@aresandco.com",
    "",
    "4. Inviter les premiers membres (optionnel, peut se faire après)",
    "",
    "5. Cliquer \"Complete setup\"",
])

add_success(doc, "L'organisation est créée. URL : github.com/aresandco")

doc.add_heading("4.2 Étape 2 : Configurer les équipes", level=2)

add_body(doc, "Créer des équipes permet de gérer les accès par groupe plutôt qu'individuellement :")

add_table(doc, ["Équipe", "Membres", "Droits suggérés"],
    [["@aresandco/admins", "IT + Partners", "Admin (tous les droits)"],
     ["@aresandco/seniors", "Consultants seniors", "Maintain (merge les PR)"],
     ["@aresandco/consultants", "Tous les consultants", "Write (push sur branches)"],
     ["@aresandco/stagiaires", "Stagiaires", "Read (lecture seule) ou Write"]],
    col_widths=[4.5, 5.5, 6])

doc.add_heading("4.3 Étape 3 : Créer le premier repository", level=2)

add_code(doc, [
    "1. Dans l'organisation, cliquer \"New repository\"",
    "",
    "2. Renseigner :",
    "   - Repository name : newsletter-banking",
    "   - Description : Agent de génération de newsletter bancaire",
    "   - Visibility : Private (visible uniquement par les membres)",
    "   - Initialize with README : Oui",
    "   - Add .gitignore : Python",
    "",
    "3. Cliquer \"Create repository\"",
])

doc.add_heading("4.4 Étape 4 : Configurer les protections", level=2)

add_body(doc, "Protéger la branche principale empêche les erreurs accidentelles :")

add_code(doc, [
    "1. Settings → Branches → Add branch protection rule",
    "",
    "2. Branch name pattern : main",
    "",
    "3. Cocher :",
    "   ☑ Require a pull request before merging",
    "   ☑ Require approvals (1 approbation minimum)",
    "   ☑ Dismiss stale approvals when new commits are pushed",
    "",
    "4. Cliquer \"Create\"",
])

add_tip(doc, "Avec cette protection, personne ne peut modifier main directement. Toute modification passe par une Pull Request qui doit être approuvée.")

doc.add_page_break()

# ========================================
# SECTION 5: WORKFLOW
# ========================================
doc.add_heading("5. Workflow quotidien recommandé", level=1)

add_flow_diagram(doc, ["Clone", "Branch", "Code", "Push", "PR", "Merge"],
                 title="Cycle de développement Git")

doc.add_heading("5.1 Pour un nouveau consultant", level=2)

add_code(doc, [
    "# 1. Cloner le projet (une seule fois)",
    "git clone https://github.com/aresandco/newsletter-banking.git",
    "cd newsletter-banking",
    "",
    "# 2. Créer une branche pour ses modifications",
    "git checkout -b feature/ajout-source-lemonde",
    "",
    "# 3. Travailler avec Claude Code",
    "claude",
    "# ... faire les modifications ...",
    "",
    "# 4. Sauvegarder et pousser",
    "git add .",
    "git commit -m \"Ajout de la source Le Monde Économie\"",
    "git push -u origin feature/ajout-source-lemonde",
    "",
    "# 5. Créer une Pull Request sur GitHub",
    "# → Aller sur github.com/aresandco/newsletter-banking",
    "# → Cliquer \"Compare & pull request\"",
    "# → Décrire les changements",
    "# → Demander une review",
])

doc.add_heading("5.2 Pour un reviewer", level=2)

add_code(doc, [
    "# 1. Recevoir une notification de PR",
    "",
    "# 2. Aller sur la PR dans GitHub",
    "",
    "# 3. Examiner les changements (onglet \"Files changed\")",
    "",
    "# 4. Laisser des commentaires si nécessaire",
    "",
    "# 5. Approuver ou demander des modifications",
    "# → \"Approve\" si c'est bon",
    "# → \"Request changes\" si des corrections sont nécessaires",
    "",
    "# 6. Merger une fois approuvé",
    "# → Cliquer \"Squash and merge\" (recommandé)",
])

add_tip(doc, "Le \"Squash and merge\" combine tous les commits de la branche en un seul commit propre sur main. Cela garde l'historique lisible.")

doc.add_page_break()

# ========================================
# SECTION 6: SÉCURITÉ
# ========================================
doc.add_heading("6. Gestion des secrets (clés API)", level=1)

doc.add_heading("6.1 Règle d'or", level=2)

add_warning(doc, "JAMAIS de clé API dans le code ou dans Git. Les clés sont stockées localement dans un fichier .env qui n'est PAS versionné.")

doc.add_heading("6.2 Configuration du .gitignore", level=2)

add_body(doc, "Le fichier .gitignore liste les fichiers à ne JAMAIS envoyer sur GitHub :")

add_code(doc, [
    "# Fichier .gitignore (à la racine du projet)",
    "",
    "# Secrets - CRITIQUE",
    ".env",
    ".env.local",
    ".env.*.local",
    "*.pem",
    "credentials.json",
    "",
    "# Environnement Python",
    "venv/",
    "__pycache__/",
    "*.pyc",
    "",
    "# IDE",
    ".vscode/",
    ".idea/",
    "",
    "# Outputs temporaires",
    "output/*.html",
    "*.log",
])

doc.add_heading("6.3 Vérification avant push", level=2)

add_code(doc, [
    "# Vérifier qu'aucun secret n'est staged",
    "git status",
    "",
    "# Si .env apparaît, c'est une erreur !",
    "# Le retirer du staging :",
    "git reset .env",
])

doc.add_heading("6.4 Pour les secrets partagés (optionnel)", level=2)

add_body(doc, "Si plusieurs consultants ont besoin des mêmes clés API (ex: clé projet partagée), utiliser GitHub Secrets :")

add_code(doc, [
    "1. Settings → Secrets and variables → Actions",
    "",
    "2. New repository secret",
    "   - Name : ANTHROPIC_API_KEY",
    "   - Value : sk-ant-xxx...",
    "",
    "3. Dans le code, accéder via variable d'environnement",
    "   (GitHub injecte automatiquement dans les workflows)",
])

add_tip(doc, "Pour un usage simple, chaque consultant peut utiliser sa propre clé API. Les secrets partagés sont utiles pour les automatisations (GitHub Actions).")

doc.add_page_break()

# ========================================
# SECTION 7: STRUCTURE RECOMMANDÉE
# ========================================
doc.add_heading("7. Structure recommandée des repositories", level=1)

add_body(doc, "Organisation suggérée des repos pour Ares & Co :")

add_table(doc, ["Repository", "Description", "Accès"],
    [["newsletter-banking", "Agent de newsletter bancaire automatisée", "Tous"],
     ["templates-genesis", "Templates Word/PPT aux couleurs Ares", "Tous"],
     ["outils-internes", "Scripts d'automatisation divers", "Tous"],
     ["formation-claude-code", "Supports de formation Claude Code", "Tous"],
     ["infra-config", "Configuration IT (optionnel)", "Admins uniquement"]],
    col_widths=[4.5, 7.5, 4])

doc.add_heading("7.1 Conventions de nommage", level=2)

add_bullet(doc, "tout en minuscules, mots séparés par des tirets", bold_prefix="Repositories : ")
add_bullet(doc, "type/description-courte (ex: feature/ajout-rss, fix/erreur-parsing)", bold_prefix="Branches : ")
add_bullet(doc, "verbe à l'impératif, < 72 caractères (ex: \"Ajoute la source Le Monde\")", bold_prefix="Commits : ")

doc.add_heading("7.2 Structure type d'un repository", level=2)

add_code(doc, [
    "nom-du-projet/",
    "├── README.md              # Description, installation, usage",
    "├── .gitignore             # Fichiers à ignorer",
    "├── requirements.txt       # Dépendances Python",
    "├── src/                   # Code source",
    "├── config/                # Configuration (sans secrets)",
    "├── templates/             # Templates (HTML, etc.)",
    "├── tests/                 # Tests automatisés (optionnel)",
    "└── docs/                  # Documentation additionnelle",
])

doc.add_page_break()

# ========================================
# SECTION 8: ONBOARDING
# ========================================
doc.add_heading("8. Onboarding d'un nouveau consultant", level=1)

add_body(doc, "Checklist pour intégrer un nouveau consultant à l'organisation GitHub :")

p = doc.add_paragraph()
run = p.add_run("Avant l'arrivée (IT/Admin) :")
run.font.bold = True

add_bullet(doc, "Inviter sur l'organisation GitHub avec son email")
add_bullet(doc, "L'ajouter à l'équipe @aresandco/consultants")
add_bullet(doc, "Partager le lien vers la documentation")

p = doc.add_paragraph()
run = p.add_run("Premier jour (consultant) :")
run.font.bold = True

add_code(doc, [
    "# 1. Accepter l'invitation GitHub (email)",
    "",
    "# 2. Installer Git (si pas déjà fait)",
    "#    https://git-scm.com/download/win",
    "",
    "# 3. Configurer son identité Git",
    "git config --global user.name \"Prénom Nom\"",
    "git config --global user.email \"prenom.nom@aresandco.com\"",
    "",
    "# 4. Cloner un premier projet",
    "git clone https://github.com/aresandco/newsletter-banking.git",
    "",
    "# 5. Créer son fichier .env avec sa clé API personnelle",
    "cd newsletter-banking",
    "echo ANTHROPIC_API_KEY=sk-ant-xxx > .env",
    "",
    "# 6. Tester",
    "python src/agent.py --list-themes",
])

add_success(doc, "Le consultant peut maintenant travailler sur tous les projets de l'organisation.")

doc.add_page_break()

# ========================================
# SECTION 9: PLAN D'ACTION
# ========================================
doc.add_heading("9. Plan d'action recommandé", level=1)

add_table(doc, ["Phase", "Actions", "Responsable", "Délai"],
    [["1. Setup", "Créer l'organisation + premier repo", "IT ou Partner tech", "2h"],
     ["2. Migration", "Migrer le projet newsletter existant", "Thomas André", "1h"],
     ["3. Documentation", "Rédiger le README du repo", "Thomas André", "30min"],
     ["4. Pilote", "Onboarder 2-3 consultants pilotes", "IT", "1h"],
     ["5. Formation", "Session de 30min sur le workflow Git", "Thomas André", "30min"],
     ["6. Déploiement", "Onboarder tous les consultants intéressés", "IT", "Progressif"]],
    col_widths=[2.5, 6, 4, 3.5])

doc.add_heading("9.1 Critères de succès", level=2)

add_bullet(doc, "L'organisation GitHub est créée et accessible")
add_bullet(doc, "Au moins 1 projet est migré et fonctionnel")
add_bullet(doc, "3+ consultants savent cloner, brancher, pusher et créer une PR")
add_bullet(doc, "Aucune clé API n'est visible dans l'historique Git")

doc.add_heading("9.2 Prochaines étapes possibles", level=2)

add_bullet(doc, "Automatiser les tests avec GitHub Actions", bold_prefix="CI/CD : ")
add_bullet(doc, "Déployer automatiquement la newsletter (Azure/AWS)", bold_prefix="Déploiement : ")
add_bullet(doc, "Ajouter des templates de PR et d'issues", bold_prefix="Gouvernance : ")

# ========================================
# FOOTER
# ========================================
doc.add_paragraph()
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("─" * 50)
run.font.color.rgb = GRAY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Ares & Co — Cabinet de conseil de Direction Générale")
run.font.name = 'Arial'
run.font.size = Pt(9)
run.font.color.rgb = GRAY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("15 Av. de la Grande Armée, 75116 Paris")
run.font.name = 'Arial'
run.font.size = Pt(8)
run.font.color.rgb = GRAY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("contact@aresandco.com | www.aresandco.com")
run.font.name = 'Arial'
run.font.size = Pt(8)
run.font.color.rgb = GRAY

# Save
doc.save("/home/user/genesis/Recommandation_GitHub_Organisation_AresCo.docx")
print("Document généré : Recommandation_GitHub_Organisation_AresCo.docx")
