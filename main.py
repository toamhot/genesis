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
  python main.py --file liens.txt --notion        # Batch + envoi vers Notion
  python main.py --inbox                          # Traiter l'Inbox Notion (1 passe)
  python main.py --daemon                         # Surveiller l'Inbox en continu
  python main.py --setup-inbox <PAGE_ID>          # Créer les bases Notion
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
    input_group.add_argument(
        "--inbox",
        action="store_true",
        help="Traiter les liens en attente dans l'Inbox Notion (une passe).",
    )
    input_group.add_argument(
        "--daemon",
        action="store_true",
        help="Mode daemon: surveiller l'Inbox Notion en continu.",
    )
    input_group.add_argument(
        "--setup-inbox",
        type=str,
        metavar="PAGE_ID",
        help="Créer les bases Notion (Inbox + Nominations) sous la page donnée.",
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
        help="Ne pas extraire les documents joints.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Intervalle de polling en minutes (mode daemon). Défaut: 10",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Activer le mode verbeux (debug logs).",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # --- Setup Notion databases ---
    if args.setup_inbox:
        return _setup_notion(args.setup_inbox)

    agent = LinkedInNominationAgent(
        scan_mode=ScanMode(args.mode) if args.mode else ScanMode.FEED,
        use_llm=not args.no_llm,
        output_format=args.output,
        days=args.days,
        push_to_notion=args.notion or args.inbox or args.daemon,
    )

    # --- Inbox mode ---
    if args.inbox:
        nominations = agent.process_inbox(extract_documents=not args.no_docs)

    # --- Daemon mode ---
    elif args.daemon:
        from config.settings import INBOX_POLL_INTERVAL_MINUTES

        interval = args.interval or INBOX_POLL_INTERVAL_MINUTES
        agent.run_daemon(
            interval_minutes=interval,
            extract_documents=not args.no_docs,
        )
        return 0

    # --- URL ingestion mode ---
    elif args.url or args.file:
        urls = args.url or load_urls_from_file(args.file)
        nominations = agent.ingest_urls(
            urls=urls,
            use_llm=not args.no_llm,
            extract_documents=not args.no_docs,
        )

    # --- Scan mode (default) ---
    else:
        nominations = agent.run()

    if not nominations:
        print("\nAucune nomination détectée.")
        return 0

    print(f"\n{len(nominations)} nomination(s) détectée(s).")
    return 0


def _setup_notion(parent_page_id: str) -> int:
    """Create both Notion databases (Inbox + Nominations)."""
    from src.notion_client import NotionClient

    try:
        notion = NotionClient()

        print("Création de la base 'Genesis - Inbox LinkedIn'...")
        inbox_id = notion.setup_inbox(parent_page_id)
        print(f"  Inbox créée: {inbox_id}")

        print("Création de la base 'Genesis - Nominations LinkedIn'...")
        db_id = notion.setup_database(parent_page_id)
        print(f"  Nominations créée: {db_id}")

        print("\nAjoutez ces IDs dans votre .env:")
        print(f"  NOTION_INBOX_DATABASE_ID={inbox_id}")
        print(f"  NOTION_DATABASE_ID={db_id}")
        return 0

    except Exception as exc:
        print(f"\nErreur: {exc}")
        print("Vérifiez que votre NOTION_API_KEY est correcte et que la page existe.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
