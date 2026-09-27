"""Factory LLM — sélectionne le provider selon la configuration.

La factory lit ``LLM_PROVIDER`` dans la config et instancie le provider
correspondant. Les analystes (étape 05) appellent ``get_llm_provider()``
et n'ont aucune dépendance directe vers un provider spécifique — c'est
cela qui rend la couche IA interchangeable.

Providers supportés :

- ``openrouter`` (défaut) — passerelle multi-modèles, GLM par défaut
- ``openai`` — API OpenAI directe
- ``local`` — Ollama en local
"""

import logging

from ai.llm.base import LLMError, LLMProvider
from config import settings

logger = logging.getLogger(__name__)

# Cache singleton du provider instancié.
_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Retourne l'instance du provider LLM configuré (singleton).

    Lit ``LLM_PROVIDER`` ('openrouter' | 'openai' | 'local') dans la
    config et instancie le provider correspondant. L'instance est mise en
    cache pour éviter de recréer un client à chaque appel.
    """
    global _provider
    if _provider is not None:
        return _provider

    name = settings.LLM_PROVIDER.lower().strip()
    logger.info(f"Initialisation du provider LLM : {name}")

    if name == "openrouter":
        from ai.llm.openrouter import OpenRouterProvider

        _provider = OpenRouterProvider()
    elif name == "openai":
        from ai.llm.openai_provider import OpenAIProvider

        _provider = OpenAIProvider()
    elif name == "local":
        from ai.llm.local import LocalOllamaProvider

        _provider = LocalOllamaProvider()
    else:
        raise LLMError(
            f"Provider LLM inconnu : '{name}'. "
            f"Valeurs supportées : 'openrouter', 'openai', 'local'."
        )

    return _provider


def reset_llm_provider() -> None:
    """Réinitialise le cache du provider (utile pour les tests)."""
    global _provider
    _provider = None
