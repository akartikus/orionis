"""Provider OpenRouter — passerelle multi-modèles (GLM, GPT, Claude, Llama…).

OpenRouter expose une API compatible OpenAI (chat completions). C'est le
point d'entrée principal d'ORIONIS : une seule clé permet d'accéder à des
dizaines de modèles et de basculer entre eux sans changer de code.

Par défaut, le modèle utilisé est GLM-5 (``z-ai/glm-5``), configurable
via ``LLM_DEFAULT_MODEL`` dans le ``.env``.

Documentation : https://openrouter.ai/docs
"""

import logging
import time
from typing import Any

import httpx

from ai.llm.base import (
    LLMAuthError,
    LLMError,
    LLMMessage,
    LLMModelError,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
)
from config import settings

logger = logging.getLogger(__name__)

# Endpoint OpenRouter (compatible OpenAI chat completions).
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# En-têtes d'identification requises par OpenRouter.
OPENROUTER_IDENTITY_HEADERS = {
    "HTTP-Referer": "https://orionis.bot",
    "X-Title": "ORIONIS",
}


class OpenRouterProvider:
    """Provider LLM via OpenRouter.

    Utilise ``httpx.AsyncClient`` pour les requêtes HTTP. Supporte le
    JSON mode (``response_format``), la gestion d'erreurs (timeout, 401,
    429) et un **fallback automatique** vers un modèle secondaire si le
    modèle primaire est indisponible.
    """

    name = "openrouter"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
        fallback_model: str | None = None,
        reasoning_enabled: bool | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API
        if not self.api_key:
            raise LLMAuthError(
                "OPENROUTER_API est requis pour le provider OpenRouter. "
                "Définissez-le dans le fichier .env."
            )
        self.default_model = (
            default_model if default_model is not None else settings.LLM_DEFAULT_MODEL
        )
        self.timeout = (
            timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
        )
        # Modèle de repli si le modèle primaire (GLM) est indisponible.
        self.fallback_model = fallback_model or "openai/gpt-4o-mini"
        # Contrôle du raisonnement (modèles reasoning comme GLM-5). Par défaut
        # désactivé : sorties fiables, rapides et économiques. Sans cela, le
        # raisonnement peut consommer tout le budget de tokens et laisser le
        # ``content`` final vide.
        self.reasoning_enabled = (
            reasoning_enabled if reasoning_enabled is not None
            else settings.LLM_REASONING_ENABLED
        )
        self.reasoning_effort = (
            reasoning_effort if reasoning_effort is not None
            else settings.LLM_REASONING_EFFORT
        )

    def _headers(self) -> dict[str, str]:
        return {
            **OPENROUTER_IDENTITY_HEADERS,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: dict[str, Any] | None = None,
    ) -> LLMResponse:
        target_model = model if model is not None else self.default_model
        try:
            return await self._request(
                messages=messages,
                model=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        except LLMModelError:
            # Fallback automatique si le modèle primaire est indisponible.
            logger.warning(
                f"Modèle primaire '{target_model}' indisponible — "
                f"fallback vers '{self.fallback_model}'."
            )
            return await self._request(
                messages=messages,
                model=self.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )

    async def _request(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        # Contrôle du raisonnement (modèles reasoning comme GLM-5). Désactivé
        # par défaut pour des sorties fiables et économiques ; réactivable via
        # LLM_REASONING_ENABLED (avec un effort optionnel via LLM_REASONING_EFFORT).
        reasoning_param: dict[str, Any] | None = None
        if not self.reasoning_enabled:
            reasoning_param = {"enabled": False}
        elif self.reasoning_effort:
            reasoning_param = {"effort": self.reasoning_effort}
        if reasoning_param is not None:
            payload["reasoning"] = reasoning_param

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    OPENROUTER_CHAT_URL,
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.TimeoutException as err:
            raise LLMTimeoutError(
                f"Timeout OpenRouter après {self.timeout}s : {err}"
            ) from err
        except httpx.HTTPError as err:
            raise LLMError(f"Erreur HTTP OpenRouter : {err}") from err

        latency_ms = (time.monotonic() - start) * 1000

        # Gestion des codes d'erreur HTTP.
        if response.status_code == 401:
            raise LLMAuthError("Clé API OpenRouter invalide ou expirée (401).")
        if response.status_code == 429:
            raise LLMRateLimitError("Limite de débit OpenRouter atteinte (429).")
        if response.status_code == 404:
            raise LLMModelError(
                f"Modèle OpenRouter introuvable : {model} (404)."
            )
        if response.status_code >= 400:
            detail = response.text[:500]
            # Une erreur mentionnant « model » indique un modèle invalide :
            # on lève LLMModelError pour permettre le fallback automatique.
            if "model" in detail.lower():
                raise LLMModelError(
                    f"Modèle OpenRouter invalide '{model}' "
                    f"({response.status_code}) : {detail}"
                )
            raise LLMError(
                f"Erreur OpenRouter {response.status_code} : {detail}"
            )

        data = response.json()
        content = ""
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content", "") or ""

        usage = data.get("usage") or {}
        used_model = data.get("model") or model

        logger.info(
            f"OpenRouter | model={used_model} | "
            f"tokens={usage.get('total_tokens', '?')} | "
            f"cost=${usage.get('cost', 0):.6f} | "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=used_model,
            usage=usage,
            raw=data,
        )
