# Charte Graphique Ares & Co

> **Usage** : Ce fichier sert de reference pour tout livrable Ares & Co (newsletters, fichiers Excel, presentations, dashboards). A inclure dans le contexte de toute session Claude Code.

---

## 1. Identite visuelle

| Element | Valeur |
|---------|--------|
| Raison sociale | **Ares & Co** |
| Baseline | *Cabinet de conseil de Direction Generale* |
| Adresse | 15 Av. de la Grande Armee, 75116 Paris |
| Telephone | +33 1 40 20 44 49 |
| Email | contact@aresandco.com |
| Site web | https://www.aresandco.com/fr |
| LinkedIn | https://www.linkedin.com/company/ares-&-company/ |
| Logo (header) | https://www.aresandco.com/images/common-contents/logo-image/62c2a7a87e751_logo.png |
| Logo (footer) | https://www.aresandco.com/img/footer-logo.png |

---

## 2. Palette de couleurs

### Couleurs principales

| Nom | Hex | RGB | Usage |
|-----|-----|-----|-------|
| **Navy primaire** | `#051E3B` | 5, 30, 59 | En-tetes, titres, fonds principaux |
| **Navy secondaire** | `#051E5B` | 5, 30, 91 | Degradees, variantes foncees |
| **Bleu accent** | `#57AEE0` | 87, 174, 224 | Boutons, liens, elements interactifs |

### Couleurs de support

| Nom | Hex | Usage |
|-----|-----|-------|
| **Texte principal** | `#2d3748` | Corps de texte, paragraphes |
| **Texte secondaire** | `#718096` | Metadonnees, dates, infos auxiliaires |
| **Fond clair** | `#f7fafc` | Arriere-plan de sections |
| **Fond page** | `#f0f4f8` | Arriere-plan general |
| **Bordure** | `#e2e8f0` | Separateurs, contours legers |

### Couleurs thematiques (newsletter)

| Theme | Hex | Nom couleur |
|-------|-----|-------------|
| Croissance & Distribution | `#2563eb` | Bleu |
| Experience Client | `#059669` | Vert |
| Performance Operationnelle | `#dc2626` | Rouge |
| Transition Demographique | `#7c3aed` | Violet |
| Epargne & Retraite | `#ea580c` | Orange |
| Risque & Finance | `#475569` | Gris |

### Couleurs speciales

| Nom | Hex | Usage |
|-----|-----|-------|
| Terrain (fond) | `#fefce8` | Section cas client |
| Terrain (bordure) | `#eab308` | Accent section cas client |
| Partage WhatsApp | `#25D366` | Bouton partage |

---

## 3. Typographie

| Element | Police | Taille | Poids | Interligne |
|---------|--------|--------|-------|------------|
| **Titre H1** | Arial, Helvetica, sans-serif | 28px | 700 | 1.2 |
| **Titre H2** | Arial, Helvetica, sans-serif | 20px | 600 | 1.3 |
| **Titre H3** | Arial, Helvetica, sans-serif | 16px | 600 | 1.4 |
| **Corps de texte** | Arial, Helvetica, sans-serif | 14px | 400 | 1.6 |
| **Texte editorial** | Arial, Helvetica, sans-serif | 14px | 400 | 1.7 |
| **Labels / Badges** | Arial, Helvetica, sans-serif | 14px | 600 | 1.2 |
| **Meta / Dates** | Arial, Helvetica, sans-serif | 12px | 400 | 1.4 |
| **Footer** | Arial, Helvetica, sans-serif | 13px | 400 | 1.5 |
| **Mentions legales** | Arial, Helvetica, sans-serif | 10-11px | 400 | 1.4 |

> **Regle** : Police unique Arial. Hierarchie visuelle via taille et graisse uniquement.

---

## 4. Espacements et dimensions

### Conteneur principal
- **Largeur max** : 700px
- **Breakpoint mobile** : 600px

### Marges internes (padding)

| Composant | Desktop | Mobile |
|-----------|---------|--------|
| En-tete | 40px 30px | 30px 20px |
| Sections | 30px | 20px |
| Badges | 8px 20px | 8px 20px |
| Boutons CTA | 12px 25px | 12px 25px |
| Encadres | 10px 15px | 10px 15px |

### Arrondis (border-radius)

| Element | Rayon |
|---------|-------|
| Badges / Pills | 20px |
| Boutons CTA | 25px |
| Boites / Encadres | 5-8px |
| Numeros de section | 50% (cercle) |

---

## 5. Bordures et separateurs

| Element | Style |
|---------|-------|
| Separateur de section | 1px solid `#e2e8f0` |
| Soulignement titre | 3px solid (couleur theme) |
| Bordure gauche editoriale | 4px solid (couleur theme) |
| Bordure gauche terrain | 4px solid `#eab308` |
| Bordure gauche conviction | 3px solid (couleur theme) |
| Separateur articles | 1px dashed `#e2e8f0` |

---

## 6. Degradees (gradients)

```
/* En-tete principal */
background: linear-gradient(135deg, #051E3B, #051E5B);

/* Section Point de Vue */
background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
```

---

## 7. Variables CSS

```css
:root {
    --primary-color: #051E3B;
    --secondary-color: #051E5B;
    --accent-color: #57AEE0;
    --text-color: #2d3748;
    --light-bg: #f7fafc;
    --border-color: #e2e8f0;
    --theme-color: #57AEE0;
}
```

---

## 8. Regles pour fichiers Excel

Lors de la creation de fichiers Excel avec openpyxl ou xlsxwriter, appliquer les correspondances suivantes :

| Element Excel | Couleur | Police | Taille |
|---------------|---------|--------|--------|
| **Titre du classeur** | Blanc sur `#051E3B` | Arial Bold | 14pt |
| **En-tetes de colonnes** | Blanc sur `#051E5B` | Arial Bold | 11pt |
| **Sous-titres** | `#051E3B` sur `#f7fafc` | Arial Bold | 11pt |
| **Cellules donnees** | `#2d3748` sur blanc | Arial | 10pt |
| **Cellules alternees** | `#2d3748` sur `#f0f4f8` | Arial | 10pt |
| **Totaux / Synthese** | Blanc sur `#57AEE0` | Arial Bold | 11pt |
| **Alertes / KPI negatifs** | `#dc2626` | Arial Bold | 10pt |
| **KPI positifs** | `#059669` | Arial Bold | 10pt |
| **Liens hypertexte** | `#57AEE0` | Arial | 10pt |
| **Notes de bas** | `#718096` | Arial Italic | 9pt |

### Exemple openpyxl

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Styles Ares & Co
ARES_STYLES = {
    "title_font": Font(name="Arial", size=14, bold=True, color="FFFFFF"),
    "title_fill": PatternFill(start_color="051E3B", end_color="051E3B", fill_type="solid"),
    "header_font": Font(name="Arial", size=11, bold=True, color="FFFFFF"),
    "header_fill": PatternFill(start_color="051E5B", end_color="051E5B", fill_type="solid"),
    "subtitle_font": Font(name="Arial", size=11, bold=True, color="051E3B"),
    "subtitle_fill": PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid"),
    "data_font": Font(name="Arial", size=10, color="2D3748"),
    "data_alt_fill": PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid"),
    "total_font": Font(name="Arial", size=11, bold=True, color="FFFFFF"),
    "total_fill": PatternFill(start_color="57AEE0", end_color="57AEE0", fill_type="solid"),
    "accent_font": Font(name="Arial", size=10, color="57AEE0"),
    "positive_font": Font(name="Arial", size=10, bold=True, color="059669"),
    "negative_font": Font(name="Arial", size=10, bold=True, color="DC2626"),
    "note_font": Font(name="Arial", size=9, italic=True, color="718096"),
    "thin_border": Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    ),
    "center_align": Alignment(horizontal="center", vertical="center"),
}
```

---

## 9. Regles generales de style

1. **Sobriete** : Privilegier le navy et le blanc. Le bleu accent est reserve aux elements interactifs et aux mises en valeur.
2. **Hierarchie** : Jamais plus de 3 niveaux de titres visibles simultanement.
3. **Contraste** : Texte blanc sur fonds navy, texte `#2d3748` sur fonds clairs. Ratio minimum WCAG AA.
4. **Espacement** : Genereux. Privilegier l'air autour des elements plutot que la densite.
5. **Alignement** : Texte justifie pour les blocs editoriaux, aligne a gauche pour les listes et donnees.
6. **Icones** : Font Awesome 6.5 (CDN: `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css`).
7. **Responsive** : Breakpoint a 600px, reduction des paddings et empilement vertical des boutons.
