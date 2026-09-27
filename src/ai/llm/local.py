"""Provider local (Ollama) — exécution de modèles en local.

Permet d'exécuter des modèles en local via Ollama
(http://localhost:11434). Implémentation fonctionnelle de l'endpoint
``/api/chat`` ; les fonctionnalités avancées (fallback, JSON mode strict)
restent à compléter lors d'une intégration réelle.

Configuration : ``LLM_PROVIDER=local`` et ``OLLAMA_BASE_URL`` (par défaut
http://localhost:11434).
"""

import logging
import time
from typing import Any

import httpx

from ai.llm.base import LLMError, LLMMessage, LLMResponse, LLMTimeoutError
from config import settings

logger = logging.getLogger(__name__)

OLLAMA_CHAT_PATH = "/api/chat"


class LocalOllamaProvider:
    """Provider LLM local via Ollama."""

    name = "local"

    def __init__(
        self,
        base_url: str | None = None,
        default_model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or "llama3.1"
        self.timeout = (
            timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
        )

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
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        # Ollama supporte le JSON mode via "format": "json".
        if response_format is not None:
            payload["format"] = "json"

        url = f"{self.base_url}{OLLAMA_CHAT_PATH}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as err:
            raise LLMTimeoutError(
                f"Timeout Ollama après {self.timeout}s : {err}"
            ) from err
        except httpx.HTTPError as err:
            raise LLMError(f"Erreur HTTP Ollama : {err}") from err

        latency_ms = (time.monotonic() - start) * 1000

        if response.status_code >= 400:
            raise LLMError(
                f"Erreur Ollama {response.status_code} : {response.text[:500]}"
            )

        data = response.json()
        content = (data.get("message") or {}).get("content", "") or ""
        prompt_tokens = data.get("prompt_eval_count", 0) or 0
        completion_tokens = data.get("eval_count", 0) or 0
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        logger.info(
            f"Ollama | model={target_model} | "
            f"tokens={usage['total_tokens']} | "
            f"latency={latency_ms:.0f}ms"
        )

        return LLMResponse(
            content=content,
            model=target_model,
            usage=usage,
            raw=data,
        )
