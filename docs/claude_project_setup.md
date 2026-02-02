# Configuration du Project Claude.ai - BCG Credit Risk Expert

## Étape 1 : Créer le Project

1. Connecte-toi à [claude.ai](https://claude.ai)
2. Dans le menu de gauche, clique sur **"Projects"**
3. Clique sur **"Create Project"**
4. Nomme-le : **"BCG Credit Risk Expert"**

## Étape 2 : Configurer les Custom Instructions

Dans les paramètres du Project, section **"Custom Instructions"**, copie-colle le contenu du fichier :

```
docs/system_prompt.txt
```

## Étape 3 : Uploader tes documents

Dans la section **"Project Knowledge"** :

1. Clique sur **"Add content"** → **"Upload files"**
2. Sélectionne tes fichiers PDF et PPT
3. Claude accepte jusqu'à ~200,000 tokens de documents

### Formats supportés
- ✅ PDF
- ✅ PowerPoint (.pptx)
- ✅ Word (.docx)
- ✅ Texte (.txt, .md)
- ✅ Code source

### Conseils pour les documents

- **Nomme bien tes fichiers** : Claude utilise les noms pour le contexte
- **Organise par thème** si possible
- **Privilégie les PDF** pour les présentations (meilleure extraction du texte)

## Étape 4 : Utiliser le Project

1. Ouvre le Project créé
2. Démarre une nouvelle conversation
3. Claude aura automatiquement :
   - Le persona d'expert BCG
   - Accès à tous tes documents
   - Le style de réponse structuré

## Exemples de questions à poser

```
Comment évaluer la PD d'un portefeuille retail selon les documents fournis ?
```

```
Synthétise les principales recommandations sur le stress testing présentes dans la base documentaire.
```

```
Quelles sont les exigences Bâle IV mentionnées dans les documents et comment les implémenter ?
```

## Limites à connaître

| Limite | Valeur |
|--------|--------|
| Taille max par fichier | ~30 MB |
| Tokens max en knowledge | ~200,000 |
| Fichiers par project | Illimité |

## Mise à jour des documents

Pour ajouter ou modifier des documents :
1. Va dans les paramètres du Project
2. Section "Project Knowledge"
3. Ajoute/supprime des fichiers

Les nouvelles conversations utiliseront automatiquement les documents mis à jour.
