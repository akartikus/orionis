"""Workflow ``portfolio_rebalance`` — vérification et ajustement d'allocation.

Vérifie l'allocation actuelle par rapport à la ``strategy_config`` et
ajuste si nécessaire (stub — implémenté à l'étape 06).
"""

import logging
from typing import Any

from core.workflow import Workflow, WorkflowStep

logger = logging.getLogger(__name__)


async def _check_allocation_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Vérifie l'allocation actuelle (stub — étape 06)."""
    logger.info("Portfolio rebalance — checking allocation (stub)...")
    return {"check_allocation": "ok"}


async def _rebalance_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Ajuste l'allocation si nécessaire (stub — étape 06)."""
    logger.info("Portfolio rebalance — rebalancing (stub)...")
    return {"rebalance": "ok"}


def build_portfolio_rebalance_workflow() -> Workflow:
    """Construit le workflow de re-équilibrage du portfolio."""
    return Workflow(
        name="portfolio_rebalance",
        steps=[
            WorkflowStep(name="check_allocation", callable=_check_allocation_step),
            WorkflowStep(name="rebalance", callable=_rebalance_step),
        ],
    )
