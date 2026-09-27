"""Module ``ai.llm`` — abstraction LLM interchangeable.

Exports publics :

- ``LLMMessage`` / ``LLMResponse`` — structures de données normalisées
- ``LLMProvider`` — interface commune (Protocol) que tous les providers
  (OpenRouter, OpenAI, local) implémentent
- ``get_llm_provider`` — factory qui sélectionne le provider selon
  ``LLM_PROVIDER`` dans la configuration
- Exceptions : ``LLMError`` et ses sous-classes (timeout, auth, rate limit…)

Les analystes IA (étape 05) n'importent **jamais** un provider spécifique :
ils dépendent uniquement de ``LLMProvider`` via ``get_llm_provider()``.
"""

from ai.llm.base import (
    LLMAuthError,
    LLMError,
    LLMMessage,
    LLMModelError,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
    LLMTimeoutError,
)
from ai.llm.factory import get_llm_provider, reset_llm_provider

__all__ = [
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "LLMError",
    "LLMTimeoutError",
    "LLMAuthError",
    "LLMRateLimitError",
    "LLMModelError",
    "get_llm_provider",
    "reset_llm_provider",
]
