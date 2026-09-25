"""EventBus — bus d'événements asynchrone (pub/sub in-process).

Pattern simple in-process : les collectors et le scheduler émettent des
événements (``PRICE_DROP``, ``NEWS_CRITICAL``, ``DAILY_TICK``), les handlers
souscrits réagissent.

Un handler qui lève une exception n'empêche pas les autres de s'exécuter
(l'erreur est loggée et le bus continue).
"""

import asyncio
import logging
from collections import defaultdict
from enum import Enum
from typing import Any, Awaitable, Callable, DefaultDict

logger = logging.getLogger(__name__)

# Type d'un handler d'événement : ``async def handler(event_type, payload)``.
EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class EventType(str, Enum):
    """Types d'événements gérés par l'EventBus."""

    PRICE_DROP = "PRICE_DROP"
    PRICE_SURGE = "PRICE_SURGE"
    NEWS_CRITICAL = "NEWS_CRITICAL"
    DAILY_TICK = "DAILY_TICK"
    THRESHOLD = "THRESHOLD"


class EventBus:
    """Bus d'événements asynchrone in-process (pub/sub).

    Les handlers enregistrés via ``subscribe()`` sont appelés en parallèle
    lors d'un ``publish()`` via ``asyncio.gather``.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Enregistre un handler pour un type d'événement."""
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler '{handler.__name__}' subscribed to '{event_type}'.")

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Émet un événement — appelle tous les handlers en parallèle.

        Un handler qui lève une exception n'empêche pas les autres
        de s'exécuter (l'erreur est loggée).
        """
        handlers = self._handlers.get(event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event '{event_type}'.")
            return

        logger.info(
            f"📨 Publishing event '{event_type}' to {len(handlers)} handler(s)."
        )

        results = await asyncio.gather(
            *(handler(event_type, payload) for handler in handlers),
            return_exceptions=True,
        )

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                handler_name = getattr(handler, "__name__", repr(handler))
                logger.error(
                    f"Handler '{handler_name}' failed for event '{event_type}': {result}",
                )
