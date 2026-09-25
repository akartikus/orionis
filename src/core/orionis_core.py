"""OrionisCore — façade principale et orchestrateur central.

Singleton qui câble l'EventBus, le WorkflowEngine, et expose des méthodes
haut-niveau utilisées par l'API FastAPI et le scheduler APScheduler.

Usage::

    from core.orionis_core import orionis_core

    await orionis_core.start()
    log = await orionis_core.run_daily_analysis()
    await orionis_core.stop()
"""

import logging
from typing import Any, Optional

from database.client import db
from database.models.orchestration_log import OrchestrationLogResponse
from core.event_bus import EventBus, EventType
from core.workflow import WorkflowEngine
from core.workflows.daily_analysis import build_daily_analysis_workflow
from core.workflows.data_sync import build_data_sync_workflow
from core.workflows.portfolio_rebalance import build_portfolio_rebalance_workflow
from core.workflows.urgent_analysis import build_urgent_analysis_workflow

logger = logging.getLogger(__name__)


class OrionisCore:
    """Orchestrateur central d'ORIONIS.

    Combine un ``EventBus`` (pub/sub in-process) et un ``WorkflowEngine``
    (séquences d'étapes) pour coordonner les collectors, l'IA, le portfolio
    manager et l'executor.
    """

    def __init__(self) -> None:
        self._event_bus = EventBus()
        self._engine = WorkflowEngine()
        self._started = False

    @property
    def event_bus(self) -> EventBus:
        """Bus d'événements partagé."""
        return self._event_bus

    @property
    def status(self) -> str:
        """Statut du core : ``'started'`` ou ``'stopped'``."""
        return "started" if self._started else "stopped"

    async def start(self) -> None:
        """Initialise l'EventBus, le WorkflowEngine et les subscriptions."""
        self._event_bus.subscribe(
            EventType.PRICE_DROP.value, self._on_price_drop
        )
        self._event_bus.subscribe(
            EventType.PRICE_SURGE.value, self._on_price_surge
        )
        self._event_bus.subscribe(
            EventType.NEWS_CRITICAL.value, self._on_news_critical
        )
        self._started = True
        logger.info("🟢 OrionisCore started — EventBus + WorkflowEngine ready")

    async def stop(self) -> None:
        """Arrête le core (cleanup)."""
        self._started = False
        logger.info("🔴 OrionisCore stopped")

    # ------------------------------------------------------------------
    # Workflows haut-niveau
    # ------------------------------------------------------------------

    async def run_daily_analysis(self) -> OrchestrationLogResponse:
        """Déclenche le workflow d'analyse quotidien complet."""
        logger.info("🔄 Starting daily_analysis workflow...")
        workflow = build_daily_analysis_workflow()
        return await self._engine.run(workflow)

    async def run_urgent_analysis(
        self, asset: str, reason: str
    ) -> OrchestrationLogResponse:
        """Déclenche une analyse urgente sur un asset spécifique."""
        logger.info(f"⚡ Starting urgent_analysis for {asset}: {reason}")
        workflow = build_urgent_analysis_workflow()
        return await self._engine.run(
            workflow, initial_context={"asset": asset, "reason": reason}
        )

    async def run_portfolio_rebalance(self) -> OrchestrationLogResponse:
        """Déclenche le workflow de re-équilibrage du portfolio."""
        logger.info("⚖️ Starting portfolio_rebalance workflow...")
        workflow = build_portfolio_rebalance_workflow()
        return await self._engine.run(workflow)

    async def run_data_sync(self) -> OrchestrationLogResponse:
        """Déclenche le workflow de synchronisation complète des données."""
        logger.info("🔄 Starting data_sync workflow...")
        workflow = build_data_sync_workflow()
        return await self._engine.run(workflow)

    # ------------------------------------------------------------------
    # Gestion des alertes
    # ------------------------------------------------------------------

    async def handle_alert(
        self,
        alert_type: str,
        asset: Optional[str] = None,
        message: str = "",
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        """Crée une alerte dans Supabase et publie l'événement sur l'EventBus.

        Args:
            alert_type: Type d'alerte (``PRICE_DROP``, ``NEWS_CRITICAL``, ...).
            asset: Asset concerné (optionnel).
            message: Message descriptif de l'alerte.
            payload: Données contextuelles supplémentaires (JSONB).
        """
        client = await db.connect()
        alert_data: dict[str, Any] = {
            "alert_type": alert_type,
            "message": message,
        }
        if asset:
            alert_data["asset"] = asset
        if payload:
            alert_data["payload"] = payload

        await client.table("alerts").insert(alert_data).execute()
        logger.info(f"🚨 Alert created: {alert_type} — {message}")

        # Publier l'événement sur le bus
        event_payload: dict[str, Any] = {"message": message}
        if asset:
            event_payload["asset"] = asset
        if payload:
            event_payload.update(payload)

        await self._event_bus.publish(alert_type, event_payload)

    # ------------------------------------------------------------------
    # Handlers d'événements
    # ------------------------------------------------------------------

    async def _on_price_drop(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Handler PRICE_DROP → déclenche une analyse urgente."""
        asset = payload.get("asset")
        if not asset:
            return
        reason = payload.get("reason", "Price drop detected")
        logger.warning(f"📉 PRICE_DROP for {asset}: {reason}")
        await self.run_urgent_analysis(asset=asset, reason=reason)

    async def _on_price_surge(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Handler PRICE_SURGE → log uniquement (pas d'analyse urgente)."""
        asset = payload.get("asset")
        if not asset:
            return
        reason = payload.get("reason", "Price surge detected")
        logger.info(f"📈 PRICE_SURGE for {asset}: {reason}")

    async def _on_news_critical(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        """Handler NEWS_CRITICAL → déclenche une analyse urgente si asset."""
        asset = payload.get("asset")
        reason = payload.get("reason", "Critical news detected")
        logger.warning(f"📰 NEWS_CRITICAL: {reason}")
        if asset:
            await self.run_urgent_analysis(asset=asset, reason=reason)


# Instance globale partagée (singleton)
orionis_core = OrionisCore()
