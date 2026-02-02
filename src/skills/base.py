"""Base class for all skills in the Genesis framework."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Skill(ABC):
    """
    Abstract base class for defining skills/experts.

    Each skill represents a specialized expert persona that can be used
    with Claude to provide domain-specific expertise.
    """

    name: str = field(init=False)
    description: str = field(init=False)

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt that defines this skill's expertise."""
        pass

    @property
    def capabilities(self) -> list[str]:
        """Return a list of capabilities this skill provides."""
        return []

    def get_prompt_for_claude(self) -> str:
        """
        Generate a formatted prompt ready to use with Claude.

        Returns:
            str: The complete system prompt for Claude.
        """
        return self.system_prompt

    def __str__(self) -> str:
        return f"Skill: {self.name}\nDescription: {self.description}"

    def __repr__(self) -> str:
        return f"<Skill(name='{self.name}')>"
