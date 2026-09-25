"""Workflow ``urgent_analysis`` — analyse immédiate sur un asset.

Déclenché par une alerte (PRICE_DROP, NEWS_CRITICAL) ou manuellement via
l'API. Analyse un asset spécifique et notifie (stub).

Le contexte initial (``asset``, ``reason``) est passé par ``OrionisCore``.
"""

import logging
from typing import Any

from core.interfaces import StubAIAnalysis
from core.workflow import Workflow, WorkflowStep

logger = logging.getLogger(__name__)

_ai_analysis = StubAIAnalysis()


async def _ai_analysis_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Analyse IA immédiate de l'asset (stub — étape 05)."""
    asset = ctx.get("asset", "unknown")
    reason = ctx.get("reason", "urgent analysis")
    logger.info(f"Urgent analysis — AI analysis for {asset} (stub): {reason}")
    result = await _ai_analysis.analyze(ctx)
    return {"ai_analysis": result}


async def _notification_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Notification de l'analyse urgente (stub — étape 08/09)."""
    asset = ctx.get("asset", "unknown")
    logger.info(
        f"Urgent analysis — notification for {asset} (stub)"
    )
    return {"notification": "ok"}


def build_urgent_analysis_workflow() -> Workflow:
    """Construit le workflow d'analyse urgente.

    Le contexte initial (``asset``, ``reason``) doit être passé via
    ``WorkflowEngine.run(workflow, initial_context={...})``.
    """
    return Workflow(
        name="urgent_analysis",
        steps=[
            WorkflowStep(name="ai_analysis", callable=_ai_analysis_step),
            WorkflowStep(name="notification", callable=_notification_step),
        ],
    )
