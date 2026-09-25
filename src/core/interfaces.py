"""Interfaces (Protocols) et stubs pour les couches dépendantes.

Les workflows d'Orionis Core appellent l'AI Analysis Layer (étape 05), le
Portfolio Manager (étape 06) et l'Execution Engine (étape 07). Ces couches
n'existent pas encore — des **stubs** no-op sont fournis ici pour que les
workflows soient câblés et testables dès maintenant.

Les stubs seront remplacés par les vraies implémentations dans les étapes
suivantes (05, 06, 07).
"""

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class AIAnalysisInterface(Protocol):
    """Interface du module d'analyse IA (étape 05)."""

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyse le contexte de marché et retourne une décision."""
        ...


class PortfolioManagerInterface(Protocol):
    """Interface du Portfolio Manager (étape 06)."""

    async def validate_decision(
        self, decision: dict[str, Any]
    ) -> dict[str, Any]:
        """Valide une décision par rapport aux limites de risque."""
        ...


class ExecutionInterface(Protocol):
    """Interface de l'Execution Engine (étape 07)."""

    async def execute_decision(
        self, decision: dict[str, Any]
    ) -> dict[str, Any]:
        """Exécute une décision validée sur Bitvavo."""
        ...


# -----------------------------------------------------------------------
# Stubs no-op — remplacés par les vraies implémentations (étapes 05/06/07)
# -----------------------------------------------------------------------


class StubAIAnalysis:
    """Stub d'analyse IA — retourne une décision HOLD neutre.

    Remplacé par ``AnalysisEngine`` à l'étape 05.
    """

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        logger.info("AI analysis stub called — not yet implemented (étape 05)")
        return {
            "status": "stub",
            "action": "HOLD",
            "reason": "AI analysis not yet implemented",
        }


class StubPortfolioManager:
    """Stub de validation portfolio — retourne une validation OK.

    Remplacé par ``PortfolioManager`` à l'étape 06.
    """

    async def validate_decision(
        self, decision: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info("Portfolio validation stub called — not yet implemented (étape 06)")
        return {
            "status": "stub",
            "valid": True,
            "reason": "Portfolio manager not yet implemented",
        }


class StubExecution:
    """Stub d'exécution — n'exécute rien.

    Remplacé par ``ExecutionEngine`` à l'étape 07.
    """

    async def execute_decision(
        self, decision: dict[str, Any]
    ) -> dict[str, Any]:
        logger.info("Execution stub called — not yet implemented (étape 07)")
        return {
            "status": "stub",
            "executed": False,
            "reason": "Execution engine not yet implemented",
        }
