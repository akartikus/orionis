"""Workflow ``daily_analysis`` — cycle quotidien complet.

Séquence : collecte → analyse IA (stub) → validation (stub) → exécution
(stub) → rapport (stub).

Les étapes IA, validation et exécution sont des **stubs** qui seront
implémentés dans les étapes 05 (AI), 06 (Portfolio Manager) et 07
(Execution Engine).
"""

import logging
from typing import Any

from collectors.market_collector import run_market_sync
from collectors.news_collector import run_news_sync
from collectors.portfolio_collector import run_portfolio_sync
from config import settings
from core.interfaces import StubAIAnalysis, StubExecution, StubPortfolioManager
from core.workflow import Workflow, WorkflowStep

logger = logging.getLogger(__name__)

# Instances de stubs (remplacées par les vraies implémentations plus tard)
_ai_analysis = StubAIAnalysis()
_portfolio_manager = StubPortfolioManager()
_executor = StubExecution()


async def _data_collection_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Collecte toutes les données de marché, portfolio et news."""
    logger.info("Daily analysis — collecting data...")
    await run_portfolio_sync()
    await run_market_sync(settings.market_assets_list)
    await run_news_sync()
    return {"data_collection": "ok"}


async def _ai_analysis_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Analyse IA des données collectées (stub — étape 05)."""
    logger.info("Daily analysis — running AI analysis (stub)...")
    result = await _ai_analysis.analyze(ctx)
    return {"ai_analysis": result}


async def _portfolio_validation_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Validation de la décision par le Portfolio Manager (stub — étape 06)."""
    logger.info("Daily analysis — validating decision (stub)...")
    decision = ctx.get("ai_analysis", {})
    result = await _portfolio_manager.validate_decision(decision)
    return {"portfolio_validation": result}


async def _execution_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Exécution de la décision si validée (stub — étape 07)."""
    decision = ctx.get("ai_analysis", {})
    action = decision.get("action", "HOLD")
    if action == "HOLD":
        logger.info("Daily analysis — decision is HOLD, skipping execution.")
        return {"execution": "skipped"}
    logger.info("Daily analysis — executing decision (stub)...")
    result = await _executor.execute_decision(decision)
    return {"execution": result}


async def _report_step(ctx: dict[str, Any]) -> dict[str, Any]:
    """Génération du rapport quotidien (stub — étape 08)."""
    logger.info("Daily analysis — generating report (stub)...")
    return {"report": "ok"}


def build_daily_analysis_workflow() -> Workflow:
    """Construit le workflow d'analyse quotidien complet."""
    return Workflow(
        name="daily_analysis",
        steps=[
            WorkflowStep(name="data_collection", callable=_data_collection_step),
            WorkflowStep(name="ai_analysis", callable=_ai_analysis_step),
            WorkflowStep(
                name="portfolio_validation", callable=_portfolio_validation_step
            ),
            WorkflowStep(name="execution", callable=_execution_step),
            WorkflowStep(name="report", callable=_report_step),
        ],
    )
