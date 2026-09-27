"""Module ``ai.prompts`` — templates de prompt réutilisables.

Exports :

- ``ORIONIS_SYSTEM_PERSONA`` — persona système injecté comme premier
  message ``system`` dans toutes les conversations LLM
"""

from ai.prompts.system import ORIONIS_SYSTEM_PERSONA

__all__ = ["ORIONIS_SYSTEM_PERSONA"]
