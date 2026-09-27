"""Provider OpenAI — API directe (alternative à OpenRouter).

Utile si l'on souhaite éviter la passerelle OpenRouter et appeler
directement l'API OpenAI. L'endpoint est compatible OpenAI chat
completions. Nécessite ``OPENAI_API_KEY`` dans le ``.env`` et
``LLM_PROVIDER=openai``.
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

# Endpoint OpenAI (chat completions).
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider:
    """Provider LLM via l'API OpenAI directe."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not self.api_key:
            raise LLMAuthError(
                "OPENAI_API_KEY est requis pour le provider OpenAI. "
                "Définissez-le dans le fichier .env."
            )
        self.default_model = (
            default_model if default_model is not None else "gpt-4o-mini"
        )
        self.timeout = (
            timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
        )

    def _headers(self) -> dict[str, str]:
        return {
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
        payload: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    OPENAI_CHAT_URL,
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.TimeoutException as err:
            raise LLMTimeoutError(
                f"Timeout OpenAI après {self.timeout}s : {err}"
            ) from err
        except httpx.HTTPError as err:
            raise LLMError(f"Erreur HTTP OpenAI : {err}") from err

        latency_ms = (time.monotonic() - start) * 1000

        if response.status_code == 401:
            raise LLMAuthError("Clé API OpenAI invalide (401).")
        if response.status_code == 429:
            raise LLMRateLimitError("Limite de débit OpenAI atteinte (429).")
        if response.status_code == 404:
            raise LLMModelError(
                f"Modèle OpenAI introuvable : {target_model} (404)."
            )
        if response.status_code >= 400:
            raise LLMError(
                f"Erreur OpenAI {response.status_code} : {response.text[:500]}"
            )

        data = response.json()
        content = ""
        choices = data.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content", "") or ""

        usage = data.get("usage") or {}
        used_model = data.get("model") or target_model

        logger.info(
            f"OpenAI | model={used_model} | "
            f"tokens={usage.get('total_tokens', '?')} | "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=used_model,
            usage=usage,
            raw=data,
        )
