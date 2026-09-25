"""Workflow ``data_sync`` — lance tous les collectors en séquence.

Réutilise les fonctions de convenience existantes des collectors
(``run_portfolio_sync``, ``run_market_sync``, ``run_news_sync``).
"""

import logging
from typing import Any

from collectors.market_collector import run_market_sync
from collectors.news_collector import run_news_sync
from collectors.portfolio_collector import run_portfolio_sync
from config import settings
from core.workflow import Workflow, WorkflowStep

logger = logging.getLogger(__name__)


async def _portfolio_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Sync Bitvavo → table 'portfolio'."""
    await run_portfolio_sync()
    return {"portfolio_sync": "ok"}


async def _market_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Sync market snapshots pour les assets surveillés."""
    await run_market_sync(settings.market_assets_list)
    return {"market_sync": "ok"}


async def _news_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Collecte RSS + analyse de sentiment."""
    await run_news_sync()
    return {"news_sync": "ok"}


def build_data_sync_workflow() -> Workflow:
    """Construit le workflow de synchronisation complète des données."""
    return Workflow(
        name="data_sync",
        steps=[
            WorkflowStep(name="portfolio_sync", callable=_portfolio_step),
            WorkflowStep(name="market_sync", callable=_market_step),
            WorkflowStep(name="news_sync", callable=_news_step),
        ],
    )
