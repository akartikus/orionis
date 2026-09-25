"""WorkflowEngine — moteur de workflows asynchrones.

Définit et exécute des séquences d'étapes asynchrones avec gestion d'erreur,
retry, timeout et logging dans la table ``orchestration_logs`` de Supabase.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional, cast
from uuid import UUID

from database.client import db
from database.models.orchestration_log import (
    OrchestrationLogResponse,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)

# Type d'une étape de workflow : ``async def step(ctx: dict) -> dict``
StepCallable = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class WorkflowStep:
    """Une étape d'un workflow.

    Attributes:
        name: Nom de l'étape (utilisé pour le logging et les détails).
        callable: Fonction async exécutée pour cette étape.
        retry_count: Nombre de tentatives supplémentaires en cas d'échec.
        timeout: Délai maximal d'exécution en secondes (optionnel).
    """

    name: str
    callable: StepCallable
    retry_count: int = 0
    timeout: Optional[float] = None


@dataclass
class Workflow:
    """Un workflow — séquence ordonnée d'étapes asynchrones.

    Attributes:
        name: Nom du workflow (ex: ``'daily_analysis'``, ``'data_sync'``).
        steps: Liste ordonnée des étapes à exécuter.
    """

    name: str
    steps: list[WorkflowStep] = field(default_factory=list)


async def _run_step(step: WorkflowStep, ctx: dict[str, Any]) -> dict[str, Any]:
    """Exécute une étape avec retry et timeout.

    Raises:
        Exception: L'erreur de la dernière tentative si tous les retries échouent.
    """
    last_error: Optional[Exception] = None
    for attempt in range(step.retry_count + 1):
        try:
            if step.timeout is not None:
                return await asyncio.wait_for(
                    step.callable(ctx), timeout=step.timeout
                )
            return await step.callable(ctx)
        except Exception as e:
            last_error = e
            if attempt < step.retry_count:
                logger.warning(
                    f"Step '{step.name}' failed (attempt {attempt + 1}"
                    f"/{step.retry_count + 1}): {e} — retrying..."
                )
                await asyncio.sleep(1.0 * (attempt + 1))
            else:
                raise
    # Inaccessible — le loop s'exécute au moins une fois et raise toujours.
    assert last_error is not None
    raise last_error


class WorkflowEngine:
    """Moteur d'exécution des workflows avec persistance dans Supabase.

    ``run()`` crée une ligne ``orchestration_logs`` (status=STARTED), exécute
    les étapes en séquence, puis met à jour le log (finished_at, duration,
    status, details, error_message).
    """

    async def run(
        self,
        workflow: Workflow,
        initial_context: Optional[dict[str, Any]] = None,
    ) -> OrchestrationLogResponse:
        """Exécute un workflow et retourne le log d'orchestration final.

        Args:
            workflow: Le workflow à exécuter.
            initial_context: Contexte initial passé à la première étape
                (ex: ``{"asset": "BTC", "reason": "Price drop"}``).

        Returns:
            ``OrchestrationLogResponse`` — le log d'orchestration persisté.
        """
        start_time = datetime.now(timezone.utc)
        log_id = await self._create_log(workflow.name, start_time)

        ctx: dict[str, Any] = dict(initial_context or {})
        details: dict[str, Any] = {"steps": []}
        error_message: Optional[str] = None
        final_status = WorkflowStatus.SUCCESS

        for step in workflow.steps:
            step_start = datetime.now(timezone.utc)
            try:
                result = await _run_step(step, ctx)
                if result:
                    ctx.update(result)
                step_duration = int(
                    (datetime.now(timezone.utc) - step_start)
                    .total_seconds() * 1000
                )
                details["steps"].append(
                    {
                        "name": step.name,
                        "status": "SUCCESS",
                        "duration_ms": step_duration,
                    }
                )
            except Exception as e:
                step_duration = int(
                    (datetime.now(timezone.utc) - step_start)
                    .total_seconds() * 1000
                )
                details["steps"].append(
                    {
                        "name": step.name,
                        "status": "FAILED",
                        "duration_ms": step_duration,
                        "error": str(e),
                    }
                )
                error_message = f"Step '{step.name}' failed: {e}"
                final_status = WorkflowStatus.FAILED
                logger.error(
                    f"Workflow '{workflow.name}' failed at step '{step.name}': {e}"
                )
                break

        end_time = datetime.now(timezone.utc)
        duration_ms = int(
            (end_time - start_time).total_seconds() * 1000
        )

        await self._update_log(
            log_id=log_id,
            status=final_status,
            finished_at=end_time,
            duration_ms=duration_ms,
            details=details,
            error_message=error_message,
        )

        return OrchestrationLogResponse(
            id=log_id,
            workflow_name=workflow.name,
            status=final_status,
            started_at=start_time,
            finished_at=end_time,
            duration_ms=duration_ms,
            details=details,
            error_message=error_message,
        )

    async def _create_log(
        self, workflow_name: str, started_at: datetime
    ) -> UUID:
        """Insère une ligne ``orchestration_logs`` avec status=STARTED."""
        client = await db.connect()
        response = await (
            client.table("orchestration_logs")
            .insert(
                {
                    "workflow_name": workflow_name,
                    "status": WorkflowStatus.STARTED.value,
                    "started_at": started_at.isoformat(),
                }
            )
            .execute()
        )
        data = cast(list[dict[str, Any]], response.data)
        if not data:
            raise RuntimeError(
                f"Failed to create orchestration log for '{workflow_name}'"
            )
        return UUID(str(data[0]["id"]))

    async def _update_log(
        self,
        log_id: UUID,
        status: WorkflowStatus,
        finished_at: datetime,
        duration_ms: int,
        details: dict[str, Any],
        error_message: Optional[str],
    ) -> None:
        """Met à jour une ligne ``orchestration_logs`` existante."""
        client = await db.connect()
        updates: dict[str, Any] = {
            "status": status.value,
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "details": details,
        }
        if error_message:
            updates["error_message"] = error_message

        await (
            client.table("orchestration_logs")
            .update(updates)
            .eq("id", str(log_id))
            .execute()
        )

