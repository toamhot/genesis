"""Skill Engine for managing and using skills with Claude."""

from typing import Optional

from ..skills.base import Skill


class SkillEngine:
    """
    Engine for managing and executing skills.

    This class provides a registry for skills and utilities for
    using them with Claude.
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """
        Register a skill in the engine.

        Args:
            skill: The skill instance to register.
        """
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[Skill]:
        """
        Get a registered skill by name.

        Args:
            name: The name of the skill to retrieve.

        Returns:
            The skill instance or None if not found.
        """
        return self._skills.get(name)

    def list_skills(self) -> list[str]:
        """
        List all registered skill names.

        Returns:
            List of registered skill names.
        """
        return list(self._skills.keys())

    def get_prompt(self, name: str) -> Optional[str]:
        """
        Get the system prompt for a skill.

        Args:
            name: The name of the skill.

        Returns:
            The system prompt or None if skill not found.
        """
        skill = self.get(name)
        return skill.get_prompt_for_claude() if skill else None

    def print_skill_info(self, name: str) -> None:
        """
        Print detailed information about a skill.

        Args:
            name: The name of the skill.
        """
        skill = self.get(name)
        if not skill:
            print(f"Skill '{name}' not found.")
            return

        print(f"\n{'='*60}")
        print(f"Skill: {skill.name}")
        print(f"{'='*60}")
        print(f"\nDescription: {skill.description}")
        print(f"\nCapabilities:")
        for cap in skill.capabilities:
            print(f"  - {cap}")
        print(f"\n{'='*60}\n")
