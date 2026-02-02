"""BCG Senior Credit Risk Expert Skill."""

from dataclasses import dataclass, field

from ..base import Skill
from .prompts import SYSTEM_PROMPT


@dataclass
class BCGCreditRiskExpert(Skill):
    """
    Expert senior du Boston Consulting Group specialise en risque de credit.

    Cette competence fournit une expertise de niveau consultant senior BCG
    dans tous les domaines du risque de credit bancaire et financier.
    """

    name: str = field(default="BCG Credit Risk Expert", init=False)
    description: str = field(
        default="Expert senior BCG specialise en risque de credit, modelisation "
        "et conformite reglementaire bancaire",
        init=False,
    )

    @property
    def system_prompt(self) -> str:
        """Return the system prompt defining BCG credit risk expertise."""
        return SYSTEM_PROMPT

    @property
    def capabilities(self) -> list[str]:
        """Return the list of capabilities for this expert."""
        return [
            "Analyse de portefeuilles de credit",
            "Evaluation de la probabilite de defaut (PD)",
            "Modelisation LGD (Loss Given Default)",
            "Modelisation EAD (Exposure at Default)",
            "Stress testing et scenarios macroeconomiques",
            "Conformite Bale III/IV",
            "Segmentation et scoring de credit",
            "Provisionnement IFRS 9",
            "Risk Appetite Framework",
            "Optimisation du capital reglementaire",
        ]
