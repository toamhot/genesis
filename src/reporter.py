"""Reporting module to format and output nomination results."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import OUTPUT_DIR
from src.nomination_detector import Nomination

logger = logging.getLogger(__name__)
console = Console()


class Reporter:
    """Generate reports of detected nominations."""

    def __init__(self, output_format: str = "console"):
        self._output_format = output_format

    def report(self, nominations: list[Nomination]) -> str | None:
        """Generate a report based on the configured output format.

        Returns the file path if output was saved to a file, None for console output.
        """
        if not nominations:
            console.print(
                "\n[yellow]Aucune nomination détectée cette semaine.[/yellow]\n"
            )
            return None

        if self._output_format == "json":
            return self._report_json(nominations)
        elif self._output_format == "html":
            return self._report_html(nominations)
        else:
            self._report_console(nominations)
            return None

    def _report_console(self, nominations: list[Nomination]) -> None:
        """Display nominations in the terminal using rich."""
        table = Table(
            title=f"Nominations de la semaine ({len(nominations)} détectées)",
            show_lines=True,
        )
        table.add_column("Nom", style="bold cyan", min_width=20)
        table.add_column("Nouveau rôle", style="green", min_width=25)
        table.add_column("Entreprise", style="magenta", min_width=15)
        table.add_column("Type", style="yellow", min_width=12)
        table.add_column("Confiance", justify="right", min_width=8)
        table.add_column("Date", min_width=12)

        type_labels = {
            "new_position": "Nouveau poste",
            "promotion": "Promotion",
            "appointment": "Nomination",
            "other": "Autre",
        }

        for nom in nominations:
            confidence_pct = f"{nom.confidence:.0%}"
            nom_type = type_labels.get(nom.nomination_type, nom.nomination_type)
            table.add_row(
                nom.person_name,
                nom.new_role or "-",
                nom.company or "-",
                nom_type,
                confidence_pct,
                nom.posted_at[:10] if nom.posted_at != "unknown" else "-",
            )

        console.print()
        console.print(table)
        console.print()

        # Print detailed view
        for i, nom in enumerate(nominations, 1):
            console.print(
                Panel(
                    f"[bold]{nom.person_name}[/bold] — {nom.person_headline}\n\n"
                    f"[green]{nom.summary()}[/green]\n\n"
                    f"[dim]{nom.source_text[:300]}{'...' if len(nom.source_text) > 300 else ''}[/dim]"
                    + (
                        f"\n\n[link={nom.person_profile_url}]Voir le profil[/link]"
                        if nom.person_profile_url
                        else ""
                    ),
                    title=f"#{i}",
                    border_style="blue",
                )
            )

    def _report_json(self, nominations: list[Nomination]) -> str:
        """Export nominations as JSON."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = OUTPUT_DIR / f"nominations_{timestamp}.json"

        data = {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "total_nominations": len(nominations),
            "nominations": [
                {
                    "person_name": n.person_name,
                    "person_headline": n.person_headline,
                    "person_profile_url": n.person_profile_url,
                    "new_role": n.new_role,
                    "company": n.company,
                    "nomination_type": n.nomination_type,
                    "confidence": n.confidence,
                    "summary": n.summary(),
                    "source_text": n.source_text,
                    "posted_at": n.posted_at,
                }
                for n in nominations
            ],
        }

        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        console.print(f"\n[green]Report saved to {filepath}[/green]\n")
        logger.info("JSON report saved to %s", filepath)
        return str(filepath)

    def _report_html(self, nominations: list[Nomination]) -> str:
        """Export nominations as an HTML report."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = OUTPUT_DIR / f"nominations_{timestamp}.html"

        type_labels = {
            "new_position": "Nouveau poste",
            "promotion": "Promotion",
            "appointment": "Nomination",
            "other": "Autre",
        }

        rows = ""
        for nom in nominations:
            nom_type = type_labels.get(nom.nomination_type, nom.nomination_type)
            name_link = (
                f'<a href="{nom.person_profile_url}" target="_blank">{nom.person_name}</a>'
                if nom.person_profile_url
                else nom.person_name
            )
            rows += f"""
            <tr>
                <td>{name_link}</td>
                <td>{nom.new_role or '-'}</td>
                <td>{nom.company or '-'}</td>
                <td>{nom_type}</td>
                <td>{nom.confidence:.0%}</td>
                <td>{nom.posted_at[:10] if nom.posted_at != 'unknown' else '-'}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nominations LinkedIn - Rapport hebdomadaire</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 1000px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        h1 {{ color: #0a66c2; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: white;
                 border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
        th {{ background: #0a66c2; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f0f7ff; }}
        a {{ color: #0a66c2; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Nominations LinkedIn de la semaine</h1>
    <p class="meta">Généré le {datetime.now(tz=timezone.utc).strftime('%d/%m/%Y à %H:%M UTC')}
    — {len(nominations)} nomination(s) détectée(s)</p>
    <table>
        <thead>
            <tr>
                <th>Nom</th>
                <th>Nouveau rôle</th>
                <th>Entreprise</th>
                <th>Type</th>
                <th>Confiance</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>{rows}
        </tbody>
    </table>
</body>
</html>"""

        filepath.write_text(html)
        console.print(f"\n[green]HTML report saved to {filepath}[/green]\n")
        logger.info("HTML report saved to %s", filepath)
        return str(filepath)
