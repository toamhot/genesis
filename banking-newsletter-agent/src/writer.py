"""
Module de rédaction de la newsletter
Banking Newsletter Agent - Ares & Co

Ce module gère :
- La génération du contenu de la newsletter
- Le formatage Markdown et HTML
- L'export des fichiers
"""

import os
from datetime import datetime
from typing import Optional
import anthropic
from jinja2 import Template
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console

from curator import CuratedSelection
from analyzer import AnalyzedArticle

console = Console()


class NewsletterWriter:
    """Rédacteur de newsletter utilisant Claude API"""

    CATEGORY_NAMES = {
        "regulation": "Actualités Réglementaires",
        "monetary_policy": "Politique Monétaire",
        "french_banks": "Banques Françaises",
        "innovation": "Innovation & Digital",
        "ma": "M&A et Restructurations",
        "market": "Tendances Marché",
        "regulateur": "Régulateurs",
        "fintech": "Fintech",
    }

    CATEGORY_EMOJI = {
        "regulation": "📜",
        "monetary_policy": "💶",
        "french_banks": "🏦",
        "innovation": "🚀",
        "ma": "🤝",
        "market": "📊",
        "regulateur": "⚖️",
        "fintech": "💡",
    }

    EDITORIAL_SYSTEM_PROMPT = """Tu es le rédacteur en chef de la newsletter bancaire d'Ares & Co, un cabinet de conseil en stratégie.

Tu rédiges une introduction éditoriale mensuelle pour des dirigeants du secteur bancaire français et européen.

Style attendu :
- Ton professionnel mais engageant
- Analyse stratégique, pas simplement descriptif
- Point de vue Ares & Co : expertise, prospectif
- 2-3 paragraphes maximum
- En français

L'introduction doit :
1. Identifier le fil rouge / thème dominant du mois
2. Mettre en perspective les événements clés
3. Donner une vision prospective"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_claude(self, system: str, prompt: str) -> str:
        """Appelle Claude API"""
        if not self.client:
            return "[Introduction éditoriale à rédiger manuellement]"

        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    def generate_editorial(self, selection: CuratedSelection, month: str) -> str:
        """Génère l'introduction éditoriale avec Claude"""
        console.print("\n[bold blue]✍️  Génération de l'éditorial...[/bold blue]")

        # Préparer le contexte pour Claude
        articles_summary = "\n".join([
            f"- {a.article.title}: {a.ai_summary}"
            for a in selection.top_articles[:10]
        ])

        categories_summary = "\n".join([
            f"- {self.CATEGORY_NAMES.get(cat, cat)}: {len(articles)} articles"
            for cat, articles in selection.articles_by_category.items()
        ])

        prompt = f"""Rédige l'introduction éditoriale de la newsletter bancaire Ares & Co pour {month}.

**Articles sélectionnés ce mois-ci :**
{articles_summary}

**Répartition thématique :**
{categories_summary}

Rédige une introduction de 2-3 paragraphes qui met en perspective ces actualités."""

        editorial = self._call_claude(self.EDITORIAL_SYSTEM_PROMPT, prompt)
        console.print("[green]✓ Éditorial généré[/green]")

        return editorial

    def generate_markdown(
        self,
        selection: CuratedSelection,
        month: str,
        editorial: Optional[str] = None
    ) -> str:
        """Génère la newsletter au format Markdown"""
        console.print("\n[bold blue]📝 Génération du Markdown...[/bold blue]")

        # Générer l'éditorial si non fourni
        if editorial is None:
            editorial = self.generate_editorial(selection, month)

        lines = []

        # En-tête
        lines.append(f"# Newsletter Banque - {month}")
        lines.append("")
        lines.append("**Ares & Co** | Conseil en Stratégie")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Éditorial
        lines.append("## Éditorial")
        lines.append("")
        lines.append(editorial)
        lines.append("")
        lines.append("---")
        lines.append("")

        # Articles par catégorie
        for category, articles in selection.articles_by_category.items():
            if not articles:
                continue

            cat_name = self.CATEGORY_NAMES.get(category, category)
            cat_emoji = self.CATEGORY_EMOJI.get(category, "📰")

            lines.append(f"## {cat_emoji} {cat_name}")
            lines.append("")

            for article in articles:
                lines.append(f"### {article.article.title}")
                lines.append("")
                lines.append(f"*Source: {article.article.source}*")
                if article.article.published_date:
                    lines.append(f" | *{article.article.published_date.strftime('%d/%m/%Y')}*")
                lines.append("")
                lines.append(article.ai_summary)
                lines.append("")

                if article.key_facts:
                    lines.append("**Points clés :**")
                    for fact in article.key_facts[:3]:
                        lines.append(f"- {fact}")
                    lines.append("")

                lines.append(f"[Lire l'article]({article.article.url})")
                lines.append("")
                lines.append("---")
                lines.append("")

        # Pied de page
        lines.append("## À propos")
        lines.append("")
        lines.append("Cette newsletter est produite par **Ares & Co**, cabinet de conseil en stratégie.")
        lines.append("")
        lines.append("Pour plus d'informations sur notre practice Banque, contactez-nous.")
        lines.append("")
        lines.append(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*")

        content = "\n".join(lines)
        console.print("[green]✓ Newsletter Markdown générée[/green]")

        return content

    def save_markdown(
        self,
        content: str,
        output_dir: str = "output/newsletters",
        filename: Optional[str] = None
    ) -> str:
        """Sauvegarde la newsletter en fichier Markdown"""
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m")
            filename = f"newsletter-banque-{timestamp}.md"

        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"\n[bold green]💾 Newsletter sauvegardée : {filepath}[/bold green]")

        return filepath

    def generate_html(
        self,
        selection: CuratedSelection,
        month: str,
        editorial: Optional[str] = None,
        logo_url: Optional[str] = None
    ) -> str:
        """Génère la newsletter au format HTML professionnel"""
        console.print("\n[bold blue]🎨 Génération du HTML...[/bold blue]")

        if editorial is None:
            editorial = self.generate_editorial(selection, month)

        template = Template(HTML_TEMPLATE)

        html = template.render(
            month=month,
            editorial=editorial,
            categories=selection.articles_by_category,
            category_names=self.CATEGORY_NAMES,
            category_emoji=self.CATEGORY_EMOJI,
            generation_date=datetime.now().strftime('%d/%m/%Y'),
            logo_url=logo_url or ""
        )

        console.print("[green]✓ Newsletter HTML générée[/green]")
        return html

    def save_html(
        self,
        content: str,
        output_dir: str = "output/newsletters",
        filename: Optional[str] = None
    ) -> str:
        """Sauvegarde la newsletter en fichier HTML"""
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            timestamp = datetime.now().strftime("%Y-%m")
            filename = f"newsletter-banque-{timestamp}.html"

        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"\n[bold green]💾 Newsletter HTML sauvegardée : {filepath}[/bold green]")

        return filepath


# Template HTML professionnel - Ares & Co
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newsletter Banque - {{ month }} | Ares & Co</title>
    <style>
        :root {
            --primary-color: #051E5B;
            --secondary-color: #0a2d7a;
            --accent-color: #1e4db7;
            --text-color: #2d3748;
            --light-bg: #f7fafc;
            --border-color: #e2e8f0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: #f0f4f8;
        }

        .container {
            max-width: 700px;
            margin: 0 auto;
            background-color: white;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 40px 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .header .subtitle {
            font-size: 14px;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .header .month {
            font-size: 18px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.3);
        }

        .editorial {
            padding: 30px;
            background-color: var(--light-bg);
            border-bottom: 3px solid var(--accent-color);
        }

        .editorial h2 {
            color: var(--primary-color);
            font-size: 20px;
            margin-bottom: 15px;
        }

        .editorial p {
            margin-bottom: 15px;
            text-align: justify;
        }

        .category {
            padding: 30px;
            border-bottom: 1px solid var(--border-color);
        }

        .category h2 {
            color: var(--primary-color);
            font-size: 20px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--accent-color);
        }

        .article {
            margin-bottom: 25px;
            padding-bottom: 25px;
            border-bottom: 1px dashed var(--border-color);
        }

        .article:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }

        .article h3 {
            color: var(--secondary-color);
            font-size: 16px;
            margin-bottom: 8px;
        }

        .article .meta {
            font-size: 12px;
            color: #718096;
            margin-bottom: 10px;
        }

        .article .summary {
            margin-bottom: 12px;
        }

        .article .key-facts {
            background-color: var(--light-bg);
            padding: 12px 15px;
            border-radius: 5px;
            margin-bottom: 12px;
        }

        .article .key-facts strong {
            color: var(--primary-color);
            font-size: 13px;
        }

        .article .key-facts ul {
            margin: 8px 0 0 20px;
            font-size: 14px;
        }

        .article .read-more {
            display: inline-block;
            color: var(--accent-color);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
        }

        .article .read-more:hover {
            text-decoration: underline;
        }

        .footer {
            background-color: var(--primary-color);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .footer h3 {
            font-size: 16px;
            margin-bottom: 10px;
        }

        .footer p {
            font-size: 13px;
            opacity: 0.9;
            margin-bottom: 8px;
        }

        .footer .generation-date {
            font-size: 11px;
            opacity: 0.7;
            margin-top: 15px;
        }

        @media (max-width: 600px) {
            .header {
                padding: 30px 20px;
            }
            .header h1 {
                font-size: 24px;
            }
            .editorial, .category {
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{ logo_url if logo_url else 'https://www.aresandco.com/img/footer-logo.png' }}" alt="Ares & Co" style="max-height: 60px; margin-bottom: 20px;">
            <h1>Newsletter Banque</h1>
            <div class="subtitle">Conseil en Stratégie</div>
            <div class="month">{{ month }}</div>
        </div>

        <div class="editorial">
            <h2>Éditorial</h2>
            {% for paragraph in editorial.split('\\n\\n') %}
            <p>{{ paragraph }}</p>
            {% endfor %}
        </div>

        {% for category, articles in categories.items() %}
        {% if articles %}
        <div class="category">
            <h2>{{ category_emoji.get(category, '📰') }} {{ category_names.get(category, category) }}</h2>

            {% for article in articles %}
            <div class="article">
                <h3>{{ article.article.title }}</h3>
                <div class="meta">
                    {{ article.article.source }}
                    {% if article.article.published_date %}
                    | {{ article.article.published_date.strftime('%d/%m/%Y') }}
                    {% endif %}
                </div>
                <p class="summary">{{ article.ai_summary }}</p>

                {% if article.key_facts %}
                <div class="key-facts">
                    <strong>Points clés :</strong>
                    <ul>
                    {% for fact in article.key_facts[:3] %}
                        <li>{{ fact }}</li>
                    {% endfor %}
                    </ul>
                </div>
                {% endif %}

                <a href="{{ article.article.url }}" class="read-more">Lire l'article →</a>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endfor %}

        <div class="footer">
            <img src="https://www.aresandco.com/img/footer-logo.png" alt="Ares & Co" style="max-height: 40px; margin-bottom: 15px; filter: brightness(0) invert(1);">
            <h3>Ares & Co</h3>
            <p>Cabinet de conseil en stratégie</p>

            <div class="contact-info" style="margin: 20px 0; font-size: 13px;">
                <p style="margin: 5px 0;">
                    <span style="opacity: 0.8;">📍</span> 15 Av. de la Grande Armée, 75116 Paris, France
                </p>
                <p style="margin: 5px 0;">
                    <span style="opacity: 0.8;">📞</span> +33 1 40 20 44 49
                </p>
                <p style="margin: 5px 0;">
                    <span style="opacity: 0.8;">✉️</span> <a href="mailto:contact@aresandco.com" style="color: white;">contact@aresandco.com</a>
                </p>
            </div>

            <div class="social-links" style="margin: 15px 0;">
                <a href="https://www.aresandco.com/" style="color: white; text-decoration: none; margin: 0 10px;">🌐 Site web</a>
                <a href="https://www.linkedin.com/company/ares-&-company/" style="color: white; text-decoration: none; margin: 0 10px;">💼 LinkedIn</a>
            </div>

            <div class="legal" style="margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); font-size: 11px; opacity: 0.7;">
                <p>Cette newsletter est envoyée aux clients et partenaires d'Ares & Co.</p>
                <p style="margin-top: 5px;">
                    <a href="#" style="color: white;">Mentions légales</a> |
                    <a href="#" style="color: white;">Politique de confidentialité</a> |
                    <a href="mailto:contact@aresandco.com?subject=Désabonnement Newsletter Banque" style="color: white;">Se désabonner</a>
                </p>
            </div>

            <div class="generation-date" style="margin-top: 15px; font-size: 10px; opacity: 0.5;">
                Généré le {{ generation_date }}
            </div>
        </div>
    </div>
</body>
</html>
"""


if __name__ == "__main__":
    # Test avec des données fictives
    from collector import Article
    from analyzer import AnalyzedArticle
    from curator import CuratedSelection

    test_selection = CuratedSelection(
        top_articles=[],
        articles_by_category={
            "monetary_policy": [
                AnalyzedArticle(
                    article=Article(
                        id="1", title="BCE : maintien des taux directeurs",
                        url="http://example.com", source="BCE",
                        category="regulateur", published_date=datetime.now(),
                        content="", summary="", priority=1
                    ),
                    ai_summary="La BCE a décidé de maintenir ses taux directeurs inchangés.",
                    relevance_score=9.0,
                    assigned_category="monetary_policy",
                    key_facts=["Taux de dépôt : 2.00%", "Inflation sous contrôle"],
                    entities=["BCE", "Christine Lagarde"],
                    sentiment="neutral",
                    newsletter_priority=1
                )
            ]
        },
        total_collected=10,
        total_selected=1
    )

    writer = NewsletterWriter()
    md = writer.generate_markdown(test_selection, "Février 2026")
    print(md[:500])
