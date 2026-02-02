#!/usr/bin/env python3
"""
Genesis Skills Framework - Example Usage

This script demonstrates how to use the skills framework
to get expert prompts for Claude.
"""

from src.core import SkillEngine
from src.skills import BCGCreditRiskExpert


def main():
    # Initialize the skill engine
    engine = SkillEngine()

    # Create and register the BCG Credit Risk Expert
    bcg_expert = BCGCreditRiskExpert()
    engine.register(bcg_expert)

    # List available skills
    print("Available Skills:")
    for skill_name in engine.list_skills():
        print(f"  - {skill_name}")

    # Print skill information
    engine.print_skill_info("BCG Credit Risk Expert")

    # Get the system prompt to use with Claude
    prompt = engine.get_prompt("BCG Credit Risk Expert")

    print("\n" + "=" * 60)
    print("SYSTEM PROMPT FOR CLAUDE")
    print("=" * 60)
    print(prompt)
    print("=" * 60)

    # Instructions for using with Claude
    print("\n" + "-" * 60)
    print("HOW TO USE THIS SKILL WITH CLAUDE:")
    print("-" * 60)
    print("""
1. Copy the system prompt above

2. In Claude chat, you can:
   - Paste it at the beginning of your conversation
   - Or use it as a system prompt via the API

3. Example questions to ask:
   - "Comment structurer un stress test de portefeuille credit?"
   - "Quelles sont les exigences Bale IV pour les modeles IRB?"
   - "Comment implementer le staging IFRS 9?"
    """)


if __name__ == "__main__":
    main()
