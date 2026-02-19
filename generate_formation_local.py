"""Formation autoportante - Créer un MVP en local avec Claude API (sans GitHub) - Document complet"""

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

h3 = doc.styles['Heading 3']
h3.font.name = 'Arial'
h3.font.size = Pt(11)
h3.font.color.rgb = NAVY_SECONDARY
h3.font.bold = True
h3.paragraph_format.space_before = Pt(10)
h3.paragraph_format.space_after = Pt(4)

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
    run = p.add_run("✓ SUCCÈS : ")
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.color.rgb = TEXT_COLOR
    doc.add_paragraph()

def add_instruction(doc, text):
    p = doc.add_paragraph()
    run = p.add_run("ℹ️ ")
    run.font.size = Pt(10)
    run = p.add_run(text)
    run.font.name = 'Arial'
    run.font.size = Pt(9)
    run.font.color.rgb = GRAY
    run.font.italic = True

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

def add_prompt_box(doc, title, content):
    p = doc.add_paragraph()
    run = p.add_run(f"💬 PROMPT : {title}")
    run.font.name = 'Arial'
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    table = doc.add_table(rows=1, cols=1)
    table.style = 'Table Grid'
    cell = table.rows[0].cells[0]
    set_cell_shading(cell, "F7FAFC")
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(content)
    run.font.name = 'Consolas'
    run.font.size = Pt(8)
    run.font.color.rgb = TEXT_COLOR
    doc.add_paragraph()

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
        cell.width = Cm(2.3)

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

def add_cycle_diagram(doc, title=None):
    if title:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"📊 {title}")
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = NAVY_SECONDARY

    table = doc.add_table(rows=3, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    set_cell_shading(table.rows[0].cells[0], "051E3B")
    set_cell_text(table.rows[0].cells[0], "1. PROMPT", bold=True, color=WHITE, size=Pt(9))
    table.rows[0].cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.rows[0].cells[1].text = ""
    p = table.rows[0].cells[1].paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("→")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    set_cell_shading(table.rows[0].cells[2], "57AEE0")
    set_cell_text(table.rows[0].cells[2], "2. GÉNÉRATION", bold=True, color=WHITE, size=Pt(9))
    table.rows[0].cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.rows[0].cells[3].text = ""
    p = table.rows[0].cells[3].paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("→")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    set_cell_shading(table.rows[0].cells[4], "57AEE0")
    set_cell_text(table.rows[0].cells[4], "3. TEST", bold=True, color=WHITE, size=Pt(9))
    table.rows[0].cells[4].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.rows[1].cells[0].text = ""
    p = table.rows[1].cells[0].paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("↑")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    table.rows[1].cells[4].text = ""
    p = table.rows[1].cells[4].paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("↓")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    set_cell_shading(table.rows[2].cells[0], "059669")
    set_cell_text(table.rows[2].cells[0], "5. VALIDER", bold=True, color=WHITE, size=Pt(9))
    table.rows[2].cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.rows[2].cells[1].text = ""
    p = table.rows[2].cells[1].paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("←")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    set_cell_shading(table.rows[2].cells[2], "EA580C")
    set_cell_text(table.rows[2].cells[2], "4. CORRECTION", bold=True, color=WHITE, size=Pt(9))
    table.rows[2].cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    table.rows[2].cells[3].text = ""
    p = table.rows[2].cells[3].paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("←")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = ACCENT_BLUE

    table.rows[2].cells[4].text = ""

    for row in table.rows:
        row.cells[0].width = Cm(2.5)
        row.cells[1].width = Cm(1)
        row.cells[2].width = Cm(2.8)
        row.cells[3].width = Cm(1)
        row.cells[4].width = Cm(2.5)

    doc.add_paragraph()

def add_vertical_flow(doc, steps, title=None):
    if title:
        p = doc.add_paragraph()
        run = p.add_run(f"📊 {title}")
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = NAVY_SECONDARY

    for i, (step, desc) in enumerate(steps):
        table = doc.add_table(rows=1, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.LEFT

        num_cell = table.rows[0].cells[0]
        set_cell_shading(num_cell, "57AEE0")
        num_cell.text = ""
        p = num_cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(i + 1))
        run.font.name = 'Arial'
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = WHITE
        num_cell.width = Cm(0.9)

        desc_cell = table.rows[0].cells[1]
        desc_cell.text = ""
        p = desc_cell.paragraphs[0]
        run = p.add_run(step)
        run.font.name = 'Arial'
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = NAVY_PRIMARY
        if desc:
            run = p.add_run(f"\n{desc}")
            run.font.name = 'Arial'
            run.font.size = Pt(9)
            run.font.color.rgb = GRAY
        desc_cell.width = Cm(14)

        if i < len(steps) - 1:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.3)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            run = p.add_run("↓")
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = ACCENT_BLUE

    doc.add_paragraph()


# ========================================
# PAGE DE TITRE
# ========================================
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(30)
run = p.add_run("DOCUMENT DE RÉFÉRENCE — GENESIS")
run.font.name = 'Arial'
run.font.size = Pt(10)
run.font.bold = True
run.font.color.rgb = ACCENT_BLUE

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(15)
run = p.add_run("CRÉER UN MVP AVEC CLAUDE CODE")
run.font.name = 'Arial'
run.font.size = Pt(20)
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Approche 100% locale — Sans GitHub")
run.font.name = 'Arial'
run.font.size = Pt(12)
run.font.color.rgb = NAVY_SECONDARY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(8)
run = p.add_run("Guide pratique autoportant")
run.font.name = 'Arial'
run.font.size = Pt(11)
run.font.italic = True
run.font.color.rgb = GRAY

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("Cas d'application : Newsletter Banking automatisée")
run.font.name = 'Arial'
run.font.size = Pt(11)
run.font.italic = True
run.font.color.rgb = GRAY

doc.add_paragraph()
doc.add_paragraph()

# Metadata
table = doc.add_table(rows=6, cols=2)
table.style = 'Table Grid'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
meta = [
    ("Public cible", "Consultants Ares & Co souhaitant créer des outils assistés par IA"),
    ("Prérequis techniques", "Aucun — ce guide part de zéro"),
    ("Approche", "100% locale — pas besoin de GitHub ni de connaître Git"),
    ("Temps de lecture", "30-45 minutes pour comprendre la méthode"),
    ("Temps de réalisation", "2-3 heures pour reproduire le projet complet"),
    ("Résultat", "Un MVP fonctionnel de newsletter automatisée"),
]
for i, (k, v) in enumerate(meta):
    set_cell_shading(table.rows[i].cells[0], "F0F4F8")
    set_cell_text(table.rows[i].cells[0], k, bold=True, color=NAVY_PRIMARY, size=Pt(10))
    set_cell_text(table.rows[i].cells[1], v, size=Pt(10))
    table.rows[i].cells[0].width = Cm(4)
    table.rows[i].cells[1].width = Cm(12)

doc.add_paragraph()

p = doc.add_paragraph()
run = p.add_run("Objectif de ce document")
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY
run.font.size = Pt(11)

add_body(doc, "Ce guide vous permet de comprendre et reproduire la création d'un MVP (Minimum Viable Product) en utilisant Claude Code comme assistant de développement. Tout se fait en local sur votre machine : pas besoin de GitHub, de Git, ni de connaître le versioning. Vous n'avez pas besoin de savoir programmer — Claude Code génère le code pour vous. Votre rôle est de structurer le projet et de formuler les bonnes demandes.")

add_tip(doc, "Cette version simplifiée supprime toute la complexité liée à Git et GitHub. Si vous souhaitez ajouter le versioning plus tard, référez-vous au guide complet avec GitHub.")

doc.add_page_break()

# ========================================
# TABLE DES MATIÈRES
# ========================================
doc.add_heading("Table des matières", level=1)

add_table(doc, ["Section", "Contenu", "Page"],
    [["1", "Glossaire des termes techniques", "3"],
     ["2", "Le produit qu'on va construire", "5"],
     ["3", "Installation des outils", "7"],
     ["4", "La méthode Claude Code", "10"],
     ["5", "Construction pas à pas", "12"],
     ["6", "Personnaliser et faire évoluer", "19"],
     ["7", "Résoudre les problèmes", "21"],
     ["8", "Aide-mémoire des commandes", "23"]],
    col_widths=[2, 11, 3])

doc.add_page_break()

# ========================================
# SECTION 1: GLOSSAIRE
# ========================================
doc.add_heading("1. Glossaire des termes techniques", level=1)

add_instruction(doc, "Consultez cette section chaque fois qu'un terme vous semble obscur. Les mots en gras dans le document sont définis ici.")

add_table(doc, ["Terme", "Définition", "Analogie"],
    [["Script", "Fichier texte contenant des instructions que l'ordinateur exécute ligne par ligne", "Une recette de cuisine"],
     ["Module", "Script conçu pour être réutilisé par d'autres scripts", "Un ingrédient préparé (sauce, pâte...)"],
     ["API", "Interface permettant à deux programmes de communiquer entre eux", "Un serveur qui transmet vos commandes à la cuisine"],
     ["Clé API", "Code secret qui vous identifie auprès d'un service", "Badge d'accès à un bâtiment"],
     ["Claude Code", "Assistant IA en ligne de commande qui génère du code pour vous", "Un développeur expert à vos côtés"],
     ["Claude API", "Service d'Anthropic pour utiliser l'IA Claude dans vos programmes", "Le cerveau IA que votre code appelle"],
     ["CLI", "Interface en ligne de commande — on tape du texte au lieu de cliquer", "Parler au lieu de pointer du doigt"],
     ["Terminal", "Application où l'on tape les commandes texte", "La fenêtre noire avec du texte"],
     ["PowerShell", "Le terminal de Windows", "Équivalent Windows du Terminal Mac"],
     ["Variable", "Conteneur qui stocke une valeur (texte, nombre...)", "Une boîte étiquetée"],
     ["Environnement virtuel", "Espace Python isolé avec ses propres outils", "Une cuisine temporaire dédiée au projet"],
     ["Dossier de projet", "Le dossier qui contient tous les fichiers de votre projet", "Votre bureau de travail dédié"],
     ["RSS", "Format standard pour les flux d'actualités", "Tuyau qui amène les articles automatiquement"],
     ["JSON", "Format structuré pour échanger des données", "Tableau bien organisé lisible par les machines"],
     ["YAML", "Format de configuration lisible par les humains", "Fichier de réglages simplifié"],
     ["Sauvegarde", "Copie de votre dossier projet à un instant donné", "Photocopie de votre classeur"]],
    col_widths=[3, 8.5, 4.5])

doc.add_page_break()

# ========================================
# SECTION 2: LE PRODUIT
# ========================================
doc.add_heading("2. Le produit qu'on va construire", level=1)

doc.add_heading("2.1 Vue d'ensemble", level=2)

add_body(doc, "Nous allons créer un agent Python qui génère automatiquement une newsletter mensuelle sur le secteur bancaire. L'agent collecte des articles, les analyse avec l'IA, sélectionne les plus pertinents, rédige un éditorial, et produit une page HTML prête à être envoyée.")

add_flow_diagram(doc, ["Sources RSS", "Collecte", "Analyse IA", "Sélection", "Rédaction", "HTML"],
                 title="Pipeline de génération de la newsletter")

add_body(doc, "Chaque étape est gérée par un module Python distinct. Cette séparation permet de modifier une partie sans toucher aux autres.")

doc.add_heading("2.2 Les 5 modules du projet", level=2)

add_table(doc, ["Module", "Rôle", "Ce qu'il produit"],
    [["collector.py", "Récupère les articles des flux RSS", "Liste d'articles bruts (titre, URL, date, contenu)"],
     ["analyzer.py", "Analyse chaque article avec Claude API", "Articles enrichis : résumé, score, catégorie, faits clés"],
     ["curator.py", "Sélectionne les 6 meilleurs articles", "Sélection filtrée par pertinence et thème"],
     ["writer.py", "Génère l'éditorial et le cas terrain", "Textes rédigés style McKinsey"],
     ["agent.py", "Orchestre tous les modules", "Newsletter HTML complète"]],
    col_widths=[3, 5.5, 7.5])

doc.add_heading("2.3 Ce qui est paramétrable", level=2)

add_body(doc, "Le projet est conçu pour être facilement adaptable sans toucher au code principal :")

add_table(doc, ["Je veux modifier...", "Fichier concerné", "Type de modification"],
    [["Les sources d'actualités", "config/sources.yaml", "Ajouter/supprimer des URL de flux RSS"],
     ["Les thèmes éditoriaux", "config/themes.yaml", "Changer les mots-clés et descriptions"],
     ["Le nombre d'articles", "src/agent.py", "Modifier le paramètre max_articles"],
     ["Le ton de l'éditorial", "src/persona.py", "Ajuster les consignes du prompt"],
     ["Les couleurs et le design", "templates/newsletter_v2.html", "Modifier les codes couleur #hex"],
     ["Le modèle IA utilisé", "src/writer.py", "Remplacer claude-sonnet par claude-opus"]],
    col_widths=[4, 4.5, 7.5])

doc.add_heading("2.4 Structure des fichiers", level=2)

add_code(doc, [
    "C:\\Projets\\newsletter\\",
    "│",
    "├── config/                         # Configuration",
    "│   ├── sources.yaml                #   Liste des 17 flux RSS",
    "│   └── themes.yaml                 #   Les 6 thèmes éditoriaux",
    "│",
    "├── src/                            # Code source",
    "│   ├── agent.py                    #   Orchestrateur principal",
    "│   ├── collector.py                #   Collecte RSS",
    "│   ├── analyzer.py                 #   Analyse IA",
    "│   ├── curator.py                  #   Sélection",
    "│   ├── writer.py                   #   Rédaction",
    "│   └── persona.py                  #   Prompts de personnalité",
    "│",
    "├── templates/                      # Gabarits",
    "│   └── newsletter_v2.html          #   Template HTML",
    "│",
    "├── output/                         # Résultats",
    "│   └── newsletter-2026-03.html     #   Newsletter générée",
    "│",
    "├── .env                            # Clé API (secret, local)",
    "└── requirements.txt                # Liste des dépendances",
])

doc.add_page_break()

# ========================================
# SECTION 3: INSTALLATION
# ========================================
doc.add_heading("3. Installation des outils", level=1)

add_instruction(doc, "Cette section détaille l'installation de chaque outil. Suivez les étapes dans l'ordre. Pas besoin d'installer Git ni GitHub !")

add_vertical_flow(doc, [
    ("Python", "Le langage de programmation — base de tout le projet"),
    ("Node.js", "Nécessaire pour installer Claude Code"),
    ("Claude Code", "L'assistant IA qui génère le code pour vous"),
    ("Clé API Claude", "Le badge d'accès aux services d'IA Claude"),
], title="Ordre d'installation (4 étapes)")

doc.add_heading("3.1 Installer Python", level=2)

add_body(doc, "Python est le langage de programmation que nous utilisons. Il est gratuit et largement utilisé.")

p = doc.add_paragraph()
run = p.add_run("Étapes d'installation :")
run.font.bold = True

add_code(doc, [
    "1. Ouvrir votre navigateur et aller sur :",
    "   https://www.python.org/downloads/",
    "",
    "2. Cliquer sur le bouton jaune \"Download Python 3.x.x\"",
    "   (prenez la dernière version proposée)",
    "",
    "3. Une fois téléchargé, lancer l'installateur",
    "",
    "4. ⚠️ IMPORTANT : Sur le premier écran, cocher la case :",
    "   \"Add Python to PATH\" (en bas de la fenêtre)",
    "",
    "5. Cliquer sur \"Install Now\"",
    "",
    "6. Attendre la fin de l'installation, puis fermer",
])

p = doc.add_paragraph()
run = p.add_run("Vérification :")
run.font.bold = True

add_body(doc, "Ouvrez PowerShell (tapez \"PowerShell\" dans la barre de recherche Windows) et tapez :")

add_code(doc, ["python --version"])

add_success(doc, "Vous devez voir s'afficher : Python 3.11.x (ou version supérieure)")

add_warning(doc, "Si vous voyez \"python n'est pas reconnu\", Python n'est pas dans le PATH. Désinstallez et réinstallez en cochant bien \"Add Python to PATH\".")

doc.add_heading("3.2 Installer Node.js", level=2)

add_body(doc, "Node.js est nécessaire pour installer Claude Code. C'est un environnement d'exécution JavaScript.")

add_code(doc, [
    "1. Aller sur : https://nodejs.org/",
    "",
    "2. Télécharger la version LTS (Long Term Support)",
    "",
    "3. Lancer l'installateur, garder les options par défaut",
    "",
    "4. Cliquer \"Next\" puis \"Install\"",
])

p = doc.add_paragraph()
run = p.add_run("Vérification :")
run.font.bold = True

add_code(doc, ["node --version"])

add_success(doc, "Vous devez voir : v20.x.x (ou supérieur)")

doc.add_heading("3.3 Installer Claude Code", level=2)

add_body(doc, "Claude Code est l'assistant IA qui va nous aider à écrire le code. Il s'installe via npm (le gestionnaire de paquets de Node.js).")

add_code(doc, [
    "# Ouvrir PowerShell en tant qu'administrateur :",
    "# (clic droit sur PowerShell → \"Exécuter en tant qu'administrateur\")",
    "",
    "npm install -g @anthropic-ai/claude-code",
])

add_body(doc, "Explication de la commande :")
add_bullet(doc, "est le gestionnaire de paquets de Node.js (Node Package Manager)", bold_prefix="npm : ")
add_bullet(doc, "signifie \"installer\"", bold_prefix="install : ")
add_bullet(doc, "signifie \"globalement\" — accessible depuis n'importe quel dossier", bold_prefix="-g : ")
add_bullet(doc, "est le paquet officiel de Claude Code", bold_prefix="@anthropic-ai/claude-code : ")

p = doc.add_paragraph()
run = p.add_run("Vérification :")
run.font.bold = True

add_code(doc, ["claude --version"])

add_success(doc, "Vous devez voir : claude-code/1.x.x")

doc.add_heading("3.4 Obtenir une clé API Claude", level=2)

add_body(doc, "La clé API permet à votre code de communiquer avec les serveurs de Claude. Elle est personnelle et facturée à l'usage.")

add_code(doc, [
    "1. Aller sur : https://console.anthropic.com/",
    "",
    "2. Créer un compte ou se connecter",
    "",
    "3. Dans le menu, cliquer sur \"API Keys\"",
    "",
    "4. Cliquer \"Create Key\"",
    "",
    "5. Donner un nom (ex: \"newsletter-projet\")",
    "",
    "6. Copier la clé affichée (commence par sk-ant-...)",
    "",
    "7. ⚠️ IMPORTANT : Sauvegarder cette clé dans un endroit sûr",
    "   Elle ne sera plus visible après fermeture de la page",
])

add_warning(doc, "Ne partagez JAMAIS votre clé API. Ne l'envoyez pas par email. Elle permet d'utiliser votre compte et génère des coûts.")

doc.add_page_break()

# ========================================
# SECTION 4: MÉTHODE
# ========================================
doc.add_heading("4. La méthode Claude Code", level=1)

add_instruction(doc, "Cette section explique comment interagir efficacement avec Claude Code. Ces principes s'appliquent à tout projet, pas seulement à la newsletter.")

doc.add_heading("4.1 Les 4 règles d'or", level=2)

# Règle 1
p = doc.add_paragraph()
run = p.add_run("Règle 1 : Décomposer avant de coder")
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY
run.font.size = Pt(11)

add_body(doc, "Ne jamais demander un projet entier d'un coup. Toujours découper en petites briques indépendantes.")

add_code(doc, [
    "❌ MAUVAIS :",
    "\"Crée-moi un système complet de newsletter automatisée\"",
    "",
    "✅ BON :",
    "\"Crée un module Python qui récupère les articles d'un flux RSS\"",
    "",
    "Puis ensuite :",
    "\"Maintenant, crée un module qui analyse un article avec Claude API\"",
    "",
    "Puis ensuite :",
    "\"Maintenant, crée un module qui sélectionne les 6 meilleurs articles\"",
])

add_tip(doc, "Un module = une responsabilité. Si vous pouvez décrire ce que fait le module en une phrase, c'est la bonne taille.")

# Règle 2
p = doc.add_paragraph()
run = p.add_run("Règle 2 : Donner le contexte métier")
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY
run.font.size = Pt(11)

add_body(doc, "Claude Code est plus efficace quand il comprend le contexte. Expliquez QUI utilise, POUR QUI, POURQUOI.")

add_code(doc, [
    "❌ MAUVAIS :",
    "\"Génère un résumé de l'article\"",
    "",
    "✅ BON :",
    "\"Génère un résumé de 2-3 phrases destiné à un Directeur Général de banque.",
    " L'objectif est d'identifier les implications stratégiques pour son établissement,",
    " pas juste de résumer les faits. Le ton doit être analytique et orienté décision.\"",
])

# Règle 3
p = doc.add_paragraph()
run = p.add_run("Règle 3 : Itérer par petits pas")
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY
run.font.size = Pt(11)

add_body(doc, "Le développement avec Claude Code est un dialogue. On génère, on teste, on corrige, on améliore.")

add_body(doc, "Le cycle de développement typique suit ce schéma :")

add_cycle_diagram(doc, title="Cycle d'itération avec Claude Code")

add_body(doc, "À chaque tour de boucle, le code s'améliore. En 2-3 itérations, un module est généralement fonctionnel.")

add_tip(doc, "Si une erreur survient, copiez-collez le message d'erreur COMPLET dans Claude Code. Il analyse et corrige automatiquement dans 90% des cas.")

# Règle 4
p = doc.add_paragraph()
run = p.add_run("Règle 4 : Montrer des exemples")
run.font.bold = True
run.font.color.rgb = NAVY_PRIMARY
run.font.size = Pt(11)

add_body(doc, "Un exemple concret vaut mieux que dix lignes d'explication. Donnez un BON et un MAUVAIS exemple.")

add_code(doc, [
    "❌ MAUVAIS :",
    "\"Écris un éditorial de qualité professionnelle\"",
    "",
    "✅ BON :",
    "\"Écris un éditorial dans ce style :",
    "",
    "EXEMPLE BON : 'Trois signaux convergents cette semaine dessinent",
    "une inflexion majeure dans la stratégie des banques de détail...'",
    "",
    "EXEMPLE MAUVAIS : 'Ce mois-ci a été riche en actualités bancaires.",
    "Voici un résumé des principales informations...'\"",
])

doc.add_heading("4.2 Quand on est bloqué", level=2)

add_body(doc, "Claude Code peut vous aider à structurer votre réflexion AVANT même de coder. N'hésitez pas à lui demander conseil.")

add_code(doc, [
    "# Pour comprendre par où commencer :",
    "\"Je veux créer une newsletter automatisée. Quelles sont les briques",
    " techniques dont j'ai besoin ? Propose-moi une architecture simple.\"",
    "",
    "# Pour décomposer une tâche complexe :",
    "\"Je dois analyser des articles avec l'IA. Décompose cette tâche",
    " en étapes simples que je peux implémenter une par une.\"",
    "",
    "# Pour choisir entre plusieurs approches :",
    "\"Pour stocker ma liste de sources RSS, vaut-il mieux utiliser",
    " un fichier YAML, JSON, ou une base de données ? Compare les options.\"",
    "",
    "# Quand on ne comprend pas quelque chose :",
    "\"Je ne comprends pas comment fonctionne feedparser.",
    " Montre-moi un exemple minimal qui récupère les articles d'un flux.\"",
    "",
    "# Pour simplifier :",
    "\"Explique-moi ce concept comme si j'avais 10 ans.\"",
])

add_tip(doc, "Claude Code est votre binôme développeur. Traitez-le comme un collègue expert à qui vous pouvez poser toutes vos questions, même les plus basiques.", "🤝")

doc.add_heading("4.3 Sauvegarder votre travail (sans Git)", level=2)

add_body(doc, "Sans Git, la sauvegarde se fait manuellement. Voici la bonne pratique :")

add_code(doc, [
    "# Après chaque module terminé, faites une copie du dossier projet :",
    "",
    "# 1. Ouvrez l'explorateur Windows",
    "# 2. Allez dans C:\\Projets\\",
    "# 3. Clic droit sur le dossier 'newsletter' → Copier",
    "# 4. Clic droit → Coller",
    "# 5. Renommez la copie, par exemple :",
    "#    newsletter-backup-module1",
    "#    newsletter-backup-module2",
    "#    etc.",
])

add_tip(doc, "Faites une sauvegarde AVANT de demander un changement important à Claude Code. Si le résultat ne vous convient pas, vous pourrez revenir à la version précédente.")

add_warning(doc, "Sans Git, il n'y a pas de moyen de revenir en arrière automatiquement. Les copies manuelles sont votre filet de sécurité !")

doc.add_page_break()

# ========================================
# SECTION 5: CONSTRUCTION
# ========================================
doc.add_heading("5. Construction pas à pas", level=1)

add_instruction(doc, "Suivez ces étapes dans l'ordre. Testez après chaque étape avant de passer à la suivante. En cas de problème, consultez la Section 7.")

add_vertical_flow(doc, [
    ("Créer le projet", "Initialisation du dossier et environnement Python"),
    ("Module Collecteur", "Récupère les articles des flux RSS"),
    ("Module Analyseur", "Analyse chaque article avec Claude API"),
    ("Module Curateur", "Sélectionne les 6 meilleurs articles"),
    ("Module Rédacteur", "Génère l'éditorial et le cas terrain"),
    ("Orchestrateur + HTML", "Assemble le tout et produit la newsletter finale"),
], title="Les 6 étapes de construction")

doc.add_heading("5.1 Créer le projet", level=2)

add_body(doc, "Ouvrez PowerShell et exécutez ces commandes une par une. Chaque commande est expliquée.")

add_table(doc, ["Commande", "Ce qu'elle fait", "Ce que vous voyez"],
    [["mkdir C:\\Projets\\newsletter", "Crée un dossier 'newsletter'", "Rien (c'est normal)"],
     ["cd C:\\Projets\\newsletter", "Entre dans ce dossier", "Le chemin change dans le prompt"],
     ["python -m venv venv", "Crée l'environnement Python", "Rien (patientez quelques secondes)"],
     [".\\venv\\Scripts\\Activate", "Active l'environnement", "(venv) apparaît au début du prompt"]],
    col_widths=[5.5, 5.5, 5])

add_success(doc, "Votre prompt affiche maintenant : (venv) C:\\Projets\\newsletter>")

add_tip(doc, "Pas de 'git init' nécessaire ! On travaille directement dans le dossier, sans versioning.")

doc.add_heading("5.2 Installer les dépendances", level=2)

add_code(doc, ["pip install anthropic feedparser pyyaml jinja2 python-dotenv rich tenacity"])

add_body(doc, "Cette commande installe les librairies nécessaires :")

add_bullet(doc, "communiquer avec Claude API", bold_prefix="anthropic : ")
add_bullet(doc, "lire les flux RSS", bold_prefix="feedparser : ")
add_bullet(doc, "lire les fichiers de configuration", bold_prefix="pyyaml : ")
add_bullet(doc, "générer le HTML à partir de templates", bold_prefix="jinja2 : ")
add_bullet(doc, "charger les variables d'environnement", bold_prefix="python-dotenv : ")
add_bullet(doc, "affichage coloré dans le terminal", bold_prefix="rich : ")
add_bullet(doc, "réessayer automatiquement en cas d'erreur réseau", bold_prefix="tenacity : ")

add_success(doc, "Vous voyez \"Successfully installed...\" suivi de la liste des packages")

doc.add_heading("5.3 Configurer la clé API", level=2)

add_code(doc, [
    "# Créer le fichier .env avec votre clé API",
    "# Remplacez sk-ant-xxx par votre vraie clé",
    "",
    "echo ANTHROPIC_API_KEY=sk-ant-xxx > .env",
])

add_body(doc, "Vérifiez que le fichier existe :")

add_code(doc, ["type .env"])

add_success(doc, "Vous devez voir : ANTHROPIC_API_KEY=sk-ant-xxx")

add_warning(doc, "Le fichier .env contient votre clé secrète. Ne le partagez jamais. Si vous faites des copies de sauvegarde, la clé sera dans la copie — c'est normal pour un usage local.")

doc.add_heading("5.4 Lancer Claude Code", level=2)

add_code(doc, ["claude"])

add_success(doc, "L'interface Claude Code s'ouvre avec un prompt > — vous êtes prêt à coder !")

add_body(doc, "À partir de maintenant, vous tapez vos demandes dans Claude Code, pas dans PowerShell.")

doc.add_page_break()

# ========================================
# MODULE 1: COLLECTOR
# ========================================
doc.add_heading("5.5 Module 1 : Le collecteur RSS", level=2)

add_body(doc, "Ce module récupère les articles des flux RSS configurés.")

add_prompt_box(doc, "Créer le collecteur RSS",
"""Crée un module Python src/collector.py qui :

1. Lit une liste de sources RSS depuis config/sources.yaml
2. Pour chaque source, récupère les articles publiés dans les 30 derniers jours
3. Retourne une liste d'objets Article avec les champs :
   - id: identifiant unique
   - title: titre de l'article
   - url: lien vers l'article
   - source: nom de la source
   - published_date: date de publication
   - content: contenu ou résumé de l'article

Le fichier config/sources.yaml doit avoir cette structure :
sources:
  - name: "BCE"
    url: "https://www.ecb.europa.eu/rss/press.html"
    category: "regulateur"
  - name: "Les Echos Banque"
    url: "https://www.lesechos.fr/rss/rss_finance_banque.xml"
    category: "presse_fr"

Utilise la librairie feedparser pour parser les flux RSS.
Gère proprement les erreurs réseau (timeout, flux indisponible).
Affiche la progression avec rich.console.""")

add_body(doc, "Test du module :")

add_code(doc, [
    "# Dans Claude Code, demandez :",
    "\"Montre-moi comment tester le collecteur\"",
    "",
    "# Ou directement dans PowerShell (après avoir quitté Claude Code avec Ctrl+C) :",
    "python -c \"from src.collector import Collector; c = Collector(); articles = c.collect(); print(f'{len(articles)} articles collectés')\"",
])

add_success(doc, "Vous devez voir : \"X articles collectés\" (le nombre dépend des sources)")

add_tip(doc, "Sauvegardez votre projet ! Copiez le dossier newsletter et renommez la copie 'newsletter-backup-module1'.", "💾")

doc.add_page_break()

# ========================================
# MODULE 2: ANALYZER
# ========================================
doc.add_heading("5.6 Module 2 : L'analyseur IA", level=2)

add_body(doc, "Ce module analyse chaque article avec Claude API pour extraire des informations structurées.")

add_prompt_box(doc, "Créer l'analyseur IA",
"""Crée un module Python src/analyzer.py qui analyse les articles avec Claude API.

Pour chaque article, Claude doit retourner un JSON avec :
- ai_summary: résumé stratégique de 2-3 phrases, en français, orienté décideur
- relevance_score: score de pertinence de 0 à 10 pour un DG de banque française
- assigned_category: une catégorie parmi [regulation, monetary_policy, french_banks, innovation, ma, market, fintech]
- key_facts: liste de 2-3 faits clés actionnables
- title_fr: traduction du titre en français si l'article est en anglais

Configuration :
- Modèle : claude-sonnet-4-20250514
- Le system prompt doit incarner un Senior Partner de cabinet de conseil (McKinsey/BCG) spécialisé dans le secteur bancaire, avec 25 ans d'expérience

Contraintes techniques :
- Traiter les articles par batch pour optimiser les appels API
- Gérer les erreurs API avec retry (utiliser tenacity)
- Afficher la progression avec rich""")

add_body(doc, "Test du module :")

add_code(doc, [
    "# Demandez à Claude Code :",
    "\"Crée un script de test qui analyse 3 articles et affiche les résultats\"",
])

add_success(doc, "Vous voyez les résumés et scores de chaque article analysé")

doc.add_page_break()

# ========================================
# MODULE 3: CURATOR
# ========================================
doc.add_heading("5.7 Module 3 : Le curateur", level=2)

add_body(doc, "Ce module sélectionne les meilleurs articles selon des critères précis.")

add_prompt_box(doc, "Créer le curateur",
"""Crée un module Python src/curator.py qui sélectionne les 6 meilleurs articles.

Critères de sélection (dans l'ordre de priorité) :
1. Score de pertinence >= 7/10
2. Priorité aux articles français (sources françaises ou entités françaises mentionnées)
3. Diversité des catégories : maximum 2 articles par catégorie
4. Si un thème du mois est spécifié, filtrer par mots-clés (config/themes.yaml)

Le fichier config/themes.yaml contient :
themes:
  growth_distribution:
    name: "Croissance & Distribution"
    keywords: [agences, réseau, conquête, parts de marché]
    color: "#2563eb"
  customer_experience:
    name: "Expérience Client"
    keywords: [digital, parcours, NPS, omnicanal, app]
    color: "#059669"
  # ... autres thèmes

Le module doit :
- Trier par score décroissant
- Appliquer les filtres
- Retourner un objet CuratedSelection avec :
  - top_articles: liste des 6 articles sélectionnés
  - articles_by_category: articles groupés par catégorie
  - total_collected: nombre total d'articles analysés
  - total_selected: nombre d'articles retenus""")

add_body(doc, "Test du module :")

add_code(doc, ["\"Crée un test qui montre les 6 articles sélectionnés avec leur score et catégorie\""])

add_success(doc, "Vous voyez la liste des 6 articles retenus, triés par pertinence")

doc.add_page_break()

# ========================================
# MODULE 4: WRITER
# ========================================
doc.add_heading("5.8 Module 4 : Le rédacteur", level=2)

add_body(doc, "Ce module génère les contenus éditoriaux : l'éditorial principal et le cas terrain.")

add_prompt_box(doc, "Créer le rédacteur - Éditorial",
"""Crée un module Python src/writer.py avec une méthode generate_editorial().

L'éditorial doit :
- Faire 450-550 mots, soit 4-5 paragraphes
- Adopter un style Senior Partner McKinsey/BCG : assertif, analytique, orienté décideur
- Suivre cette structure :

1. THÈSE CENTRALE (1 paragraphe)
   Ouvrir avec une affirmation forte et différenciante.

2. PREUVES ET SIGNAUX (2 paragraphes)
   Développer 2-3 dynamiques qui soutiennent la thèse.

3. SO WHAT - IMPLICATIONS STRATÉGIQUES (1 paragraphe)
   Traduire en enjeux concrets pour un DG de banque.

4. CONVICTION (dernière phrase, en gras)
   Format : **Notre conviction : [affirmation tranchée et mémorable].**""")

add_prompt_box(doc, "Créer le rédacteur - Cas terrain",
"""Ajoute une méthode generate_terrain() au module writer.py.

Cette méthode génère un mini-cas "Terrain Ares & Co".

Structure stricte :
- TITRE: [5-10 mots]
- PROBLÈME: [2-3 phrases avec chiffres]
- APPROCHE: [2-3 phrases méthodologie]
- RÉSULTATS: [2-3 phrases résultats quantifiés]

Règles :
- Client toujours anonymisé
- Chiffres crédibles et précis
- Maximum 150 mots au total""")

add_body(doc, "Test du module :")

add_code(doc, ["\"Génère un éditorial de test et affiche-le\""])

add_success(doc, "Vous voyez un éditorial structuré de ~500 mots avec une conviction en gras à la fin")

doc.add_page_break()

# ========================================
# MODULE 5: AGENT + HTML
# ========================================
doc.add_heading("5.9 Module 5 : L'orchestrateur et le template HTML", level=2)

add_body(doc, "Le dernier module assemble le tout et génère le HTML final.")

add_prompt_box(doc, "Créer l'orchestrateur",
"""Crée le module principal src/agent.py qui orchestre tout le pipeline.

Interface en ligne de commande avec argparse :
- python agent.py --list-themes        → Affiche les 6 thèmes disponibles
- python agent.py --theme xxx          → Lance la génération pour ce thème
- python agent.py --month "Mars 2026"  → Spécifie le mois pour l'en-tête

Workflow d'exécution :
1. Charger la configuration (sources.yaml, themes.yaml)
2. Collecter les articles (collector.py)
3. Analyser avec Claude (analyzer.py)
4. Sélectionner les meilleurs (curator.py)
5. Générer l'éditorial et le terrain (writer.py)
6. Assembler le HTML et sauvegarder dans output/

Afficher la progression de chaque étape avec rich.""")

add_prompt_box(doc, "Créer le template HTML",
"""Crée le fichier templates/newsletter_v2.html (template Jinja2).

Design :
- Header avec dégradé bleu marine (#051E3B → #051E5B)
- Logo Ares & Co
- Baseline "Cabinet de conseil de Direction Générale"

Sections :
1. ÉDITORIAL - Le texte généré
2. RADAR - Les 6 articles avec : numéro, titre, source, date, résumé, lien
3. TERRAIN ARES & CO - Le cas anonymisé (fond jaune clair)
4. CALL TO ACTION - Contact + bouton email

Contraintes :
- Responsive (breakpoint 600px)
- Police Arial
- Couleur accent : #57AEE0""")

add_body(doc, "Test final :")

add_code(doc, [
    "# Quitter Claude Code (Ctrl+C) puis dans PowerShell :",
    "python src/agent.py --list-themes",
    "",
    "# Lancer une génération complète :",
    "python src/agent.py --theme customer_experience --month \"Mars 2026\"",
    "",
    "# Ouvrir le résultat :",
    "explorer output",
    "# Puis double-cliquer sur le fichier .html",
])

add_success(doc, "La newsletter HTML s'ouvre dans votre navigateur avec l'éditorial, les 6 articles et le cas terrain")

doc.add_page_break()

# ========================================
# SECTION 6: PERSONNALISER
# ========================================
doc.add_heading("6. Personnaliser et faire évoluer", level=1)

add_instruction(doc, "Une fois le projet fonctionnel, voici comment l'adapter à vos besoins sans toucher au code principal.")

doc.add_heading("6.1 Ajouter une source RSS", level=2)

add_body(doc, "Ouvrez config/sources.yaml dans un éditeur de texte (Bloc-notes ou VS Code) et ajoutez un bloc :")

add_code(doc, [
    "sources:",
    "  # ... sources existantes ...",
    "  ",
    "  - name: \"Le Monde Économie\"",
    "    url: \"https://www.lemonde.fr/economie/rss_full.xml\"",
    "    category: \"presse_fr\"",
])

add_tip(doc, "Pour ouvrir un fichier YAML, faites un clic droit → \"Ouvrir avec\" → Bloc-notes (ou VS Code si installé).")

doc.add_heading("6.2 Modifier un thème éditorial", level=2)

add_body(doc, "Ouvrez config/themes.yaml et modifiez les mots-clés :")

add_code(doc, [
    "themes:",
    "  customer_experience:",
    "    name: \"Expérience Client\"",
    "    keywords:",
    "      - digital",
    "      - parcours client",
    "      - NPS",
    "      - satisfaction",
    "      - omnicanal",
    "      - application mobile   # Ajouté",
    "    color: \"#059669\"",
])

doc.add_heading("6.3 Changer le ton de l'éditorial", level=2)

add_body(doc, "Lancez Claude Code dans le dossier du projet et demandez :")

add_code(doc, [
    "\"Ouvre src/persona.py et modifie le prompt pour que le ton soit",
    " plus direct et les phrases plus courtes. Maximum 15 mots par phrase.\"",
])

doc.add_heading("6.4 Modifier les couleurs", level=2)

add_body(doc, "Demandez à Claude Code :")

add_code(doc, [
    "\"Ouvre templates/newsletter_v2.html et remplace la couleur",
    " principale #051E3B par #1a365d (bleu plus clair)\"",
])

doc.add_heading("6.5 Ajouter une section", level=2)

add_body(doc, "Demandez à Claude Code :")

add_code(doc, [
    "\"Ajoute une section 'Chiffre du mois' entre l'éditorial et le radar.",
    " Cette section affiche un chiffre clé avec sa source et un commentaire.\"",
])

doc.add_heading("6.6 Partager le projet avec un collègue", level=2)

add_body(doc, "Sans GitHub, voici comment partager votre projet :")

add_code(doc, [
    "1. Compressez le dossier C:\\Projets\\newsletter en .zip",
    "   (clic droit → Envoyer vers → Dossier compressé)",
    "",
    "2. Envoyez le fichier .zip par email ou via Teams",
    "",
    "3. Votre collègue décompresse le .zip",
    "",
    "4. Il doit juste :",
    "   a) Installer Python, Node.js et Claude Code (Section 3)",
    "   b) Créer son propre fichier .env avec SA clé API",
    "   c) Activer l'environnement : .\\venv\\Scripts\\Activate",
    "   d) Réinstaller les dépendances : pip install -r requirements.txt",
])

add_warning(doc, "Ne partagez PAS le fichier .env ! Chaque consultant doit utiliser sa propre clé API.")

doc.add_page_break()

# ========================================
# SECTION 7: PROBLÈMES
# ========================================
doc.add_heading("7. Résoudre les problèmes", level=1)

doc.add_heading("7.1 Erreurs fréquentes et solutions", level=2)

add_table(doc, ["Message d'erreur", "Cause probable", "Solution"],
    [["'python' n'est pas reconnu", "Python pas dans le PATH système", "Réinstaller Python en cochant 'Add Python to PATH'"],
     ["'pip' n'est pas reconnu", "Environnement virtuel pas activé", "Exécuter : .\\venv\\Scripts\\Activate"],
     ["'npm' n'est pas reconnu", "Node.js pas installé", "Installer Node.js depuis nodejs.org"],
     ["'claude' n'est pas reconnu", "Claude Code pas installé", "Exécuter : npm install -g @anthropic-ai/claude-code"],
     ["ModuleNotFoundError: No module named 'xxx'", "Librairie pas installée", "Exécuter : pip install xxx"],
     ["Invalid API key", "Clé API incorrecte ou mal copiée", "Vérifier .env : pas d'espaces, clé complète"],
     ["Connection error / timeout", "Pas de connexion internet", "Vérifier votre connexion réseau"],
     ["Permission denied", "Droits insuffisants", "Relancer PowerShell en administrateur"],
     ["FileNotFoundError", "Fichier ou dossier manquant", "Vérifier le chemin avec : dir"],
     ["SyntaxError", "Erreur dans le code Python", "Coller l'erreur complète dans Claude Code"],
     ["JSONDecodeError", "Réponse API mal formatée", "Réessayer ou demander à Claude Code de corriger"]],
    col_widths=[5, 5.5, 5.5])

doc.add_heading("7.2 Commandes de diagnostic", level=2)

add_table(doc, ["Commande", "Ce qu'elle vérifie"],
    [["python --version", "Python est installé et accessible"],
     ["node --version", "Node.js est installé"],
     ["claude --version", "Claude Code est installé"],
     ["pip list", "Liste les librairies installées"],
     ["dir", "Affiche les fichiers du dossier actuel"],
     ["type .env", "Affiche le contenu du fichier .env"]],
    col_widths=[5, 11])

doc.add_heading("7.3 La règle d'or du débogage", level=2)

add_tip(doc, "Face à une erreur que vous ne comprenez pas : copiez le message d'erreur COMPLET (toutes les lignes) et collez-le dans Claude Code. Il analyse et propose une correction dans 90% des cas.", "🔧")

doc.add_page_break()

# ========================================
# SECTION 8: AIDE-MÉMOIRE
# ========================================
doc.add_heading("8. Aide-mémoire des commandes", level=1)

doc.add_heading("8.1 Commandes PowerShell", level=2)

add_table(doc, ["Commande", "Description"],
    [["dir", "Lister les fichiers et dossiers"],
     ["cd nom_dossier", "Entrer dans un dossier"],
     ["cd ..", "Remonter d'un niveau"],
     ["mkdir nom", "Créer un nouveau dossier"],
     ["type fichier.txt", "Afficher le contenu d'un fichier"],
     ["explorer .", "Ouvrir le dossier actuel dans l'explorateur Windows"],
     ["python script.py", "Exécuter un script Python"],
     ["python --version", "Afficher la version de Python"],
     [".\\venv\\Scripts\\Activate", "Activer l'environnement virtuel"],
     ["deactivate", "Désactiver l'environnement virtuel"]],
    col_widths=[5.5, 10.5])

doc.add_heading("8.2 Commandes Claude Code", level=2)

add_table(doc, ["Action", "Description"],
    [["claude", "Lancer Claude Code dans le dossier actuel"],
     ["/help", "Afficher l'aide"],
     ["/clear", "Effacer l'historique de conversation"],
     ["Ctrl+C", "Interrompre la génération en cours / quitter"],
     ["Coller une erreur", "Claude analyse et propose une correction"],
     ["\"Lis le fichier X\"", "Claude affiche le contenu du fichier"],
     ["\"Explique ce code\"", "Claude explique ce que fait le code"],
     ["\"Montre la structure du projet\"", "Claude liste l'arborescence"]],
    col_widths=[5.5, 10.5])

doc.add_heading("8.3 Raccourcis utiles", level=2)

add_table(doc, ["Raccourci", "Action"],
    [["Ctrl+C", "Copier / Interrompre une commande"],
     ["Ctrl+V", "Coller"],
     ["Tab", "Autocomplétion (noms de fichiers, commandes)"],
     ["↑ / ↓", "Naviguer dans l'historique des commandes"],
     ["Ctrl+L", "Effacer l'écran du terminal"]],
    col_widths=[5, 11])

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
doc.save("/home/user/genesis/Formation_Newsletter_Local_SansGitHub_AresCo.docx")
print("Document généré : Formation_Newsletter_Local_SansGitHub_AresCo.docx")
