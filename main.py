#!/usr/bin/env python3
"""Entry point for the LinkedIn Nomination Agent."""

import argparse
import logging
import sys

from src.agent import LinkedInNominationAgent, ScanMode


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent de détection des nominations LinkedIn parmi vos contacts."
    )
    parser.add_argument(
        "--mode",
        choices=["feed", "contacts", "both"],
        default="feed",
        help="Mode de scan: 'feed' (rapide), 'contacts' (exhaustif), 'both' (combiné). Défaut: feed",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Nombre de jours à analyser. Défaut: 7",
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
        help="Désactiver l'analyse LLM (utiliser uniquement les mots-clés).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activer le mode verbeux (debug logs).",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    agent = LinkedInNominationAgent(
        scan_mode=ScanMode(args.mode),
        use_llm=not args.no_llm,
        output_format=args.output,
        days=args.days,
    )

    nominations = agent.run()

    if not nominations:
        print("\nAucune nomination détectée cette semaine.")
        return 0

    print(f"\n{len(nominations)} nomination(s) détectée(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
