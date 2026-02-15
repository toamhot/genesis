#!/usr/bin/env python3
"""Entry point for the LinkedIn Nomination Agent."""

import argparse
import logging
import sys
from pathlib import Path

from src.agent import LinkedInNominationAgent, ScanMode


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_urls_from_file(filepath: str) -> list[str]:
    """Load LinkedIn URLs from a text file (one per line)."""
    path = Path(filepath)
    if not path.exists():
        print(f"Erreur: fichier introuvable: {filepath}")
        sys.exit(1)

    urls = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "linkedin.com" in line:
            urls.append(line)

    if not urls:
        print(f"Aucun lien LinkedIn trouvé dans {filepath}")
        sys.exit(1)

    return urls


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent de détection des nominations LinkedIn parmi vos contacts.",
        epilog="""
Exemples:
  python main.py --mode feed                     # Scanner le feed LinkedIn
  python main.py --url https://linkedin.com/...  # Analyser un lien partagé
  python main.py --file liens.txt --notion       # Batch + envoi vers Notion
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # --- Input mode (mutually exclusive) ---
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--mode",
        choices=["feed", "contacts", "both"],
        default=None,
        help="Mode de scan automatique: 'feed', 'contacts', 'both'.",
    )
    input_group.add_argument(
        "--url",
        type=str,
        nargs="+",
        help="Un ou plusieurs liens LinkedIn à analyser (via 'Partager').",
    )
    input_group.add_argument(
        "--file",
        type=str,
        help="Fichier texte contenant des liens LinkedIn (un par ligne).",
    )

    # --- Common options ---
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Nombre de jours à analyser (mode scan). Défaut: 7",
    )
    parser.add_argument(
        "--output",
        choices=["console", "json", "html"],
        default="console",
        help="Format de sortie. Défaut: console",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Désactiver l'analyse LLM (mots-clés uniquement).",
    )
    parser.add_argument(
        "--notion",
        action="store_true",
        help="Envoyer les résultats vers la base Notion Genesis.",
    )
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Ne pas extraire les documents joints (mode URL uniquement).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activer le mode verbeux (debug logs).",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    agent = LinkedInNominationAgent(
        scan_mode=ScanMode(args.mode) if args.mode else ScanMode.FEED,
        use_llm=not args.no_llm,
        output_format=args.output,
        days=args.days,
        push_to_notion=args.notion,
    )

    # --- URL ingestion mode ---
    if args.url or args.file:
        urls = args.url or load_urls_from_file(args.file)
        nominations = agent.ingest_urls(
            urls=urls,
            use_llm=not args.no_llm,
            extract_documents=not args.no_docs,
        )
    # --- Scan mode (default) ---
    else:
        if args.mode is None:
            args.mode = "feed"
        nominations = agent.run()

    if not nominations:
        print("\nAucune nomination détectée.")
        return 0

    print(f"\n{len(nominations)} nomination(s) détectée(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
