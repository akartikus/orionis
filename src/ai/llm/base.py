"""LLM Provider — interface commune (Protocol).

Définit l'abstraction que tous les providers LLM (OpenRouter, OpenAI,
local) doivent implémenter. Les analystes IA (étape 05) dépendent
uniquement de ``LLMProvider``, jamais d'un provider spécifique — ce qui
rend la couche IA interchangeable (un simple changement de
``LLM_PROVIDER`` dans le ``.env`` bascule d'un modèle à un autre).
"""

import logging
from typing import Any, Protocol, TypedDict

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMMessage(TypedDict):
    """Message de conversation au format chat-completions.

    ``role`` vaut ``'system'`` | ``'user'`` | ``'assistant'``.
    """

    role: str
    content: str


class LLMResponse(BaseModel):
    """Réponse normalisée d'un provider LLM.

    Quel que soit le provider, ``complete()`` renvoie toujours cette
    structure pour que les analystes n'aient pas à gérer des formats
    différents.
    """

    content: str
    model: str
    usage: dict[str, Any]  # tokens in/out + coût éventuel
    raw: dict[str, Any]  # réponse brute du provider (debug)


class LLMProvider(Protocol):
    """Interface commune pour tous les providers LLM.

    Une implémentation expose :

    - ``name`` : identifiant du provider ('openrouter', 'openai', 'local')
    - ``complete()`` : génération asynchrone d'une complétion
    """

    name: str

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Génère une complétion à partir d'une liste de messages.

        Args:
            messages: Conversation au format chat-completions.
            model: Modèle cible (``None`` → modèle par défaut du provider).
            temperature: Créativité (0.0 = déterministe, 2.0 = aléatoire).
            max_tokens: Nombre maximum de tokens générés.
            response_format: Mode de réponse (ex: ``{"type": "json_object"}``
                pour forcer une sortie JSON).

        Returns:
            Une ``LLMResponse`` normalisée.
        """
        ...


# -----------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------


class LLMError(Exception):
    """Erreur de base pour tous les providers LLM."""


class LLMTimeoutError(LLMError):
    """Délai dépassé lors de l'appel au LLM."""


class LLMAuthError(LLMError):
    """Erreur d'authentification (clé API invalide ou manquante)."""


class LLMRateLimitError(LLMError):
    """Limite de débit atteinte (rate limit 429)."""


class LLMModelError(LLMError):
    """Modèle invalide ou indisponible (permet le fallback automatique)."""
