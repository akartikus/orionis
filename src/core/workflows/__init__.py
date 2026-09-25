"""Workflows prédéfinis d'Orionis Core."""

from core.workflows.daily_analysis import build_daily_analysis_workflow
from core.workflows.data_sync import build_data_sync_workflow
from core.workflows.portfolio_rebalance import build_portfolio_rebalance_workflow
from core.workflows.urgent_analysis import build_urgent_analysis_workflow

__all__ = [
    "build_daily_analysis_workflow",
    "build_data_sync_workflow",
    "build_portfolio_rebalance_workflow",
    "build_urgent_analysis_workflow",
]
