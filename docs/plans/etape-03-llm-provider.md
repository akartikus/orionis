# ÉTAPE 03 — LLM Provider (Abstraction IA interchangeable)

> **Priorité** : 🔴 Critique
> **Prérequis** : Étape 01 (modèles DB) terminée
> **Objectif** : Créer une couche d'abstraction LLM permettant de changer
> facilement de modèle (GLM-5, GPT, Claude, modèles locaux futurs) sans
> modifier le code des analystes.

---

## Contexte

La vision stipule explicitement : **« La couche IA doit être interchangeable. »**

Actuellement, `OPENROUTER_API` est dans le `.env` mais aucune logique ne
l'utilise. OpenRouter est une passerelle multi-modèles (GPT, Claude, GLM,
Llama…) — c'est le point d'entrée idéal. Mais l'abstraction doit aussi
supporter un appel direct à l'API OpenAI ou un modèle local (Ollama).

---

## Architecture cible

```
          AIAnalysisLayer (étape 05)
                |
         LLMProvider (abstraction)
                |
    ┌───────────┼───────────┐
    │           │           │
OpenRouter   OpenAI     Local(Ollama)
Provider     Provider   Provider
```

### Interface commune

```python
# src/ai/llm/base.py
class LLMMessage(TypedDict):
    role: str          # 'system' | 'user' | 'assistant'
    content: str

class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict        # tokens in/out
    raw: dict          # réponse brute pour debug

class LLMProvider(Protocol):
    name: str
    async def complete(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: dict | None = None,  # JSON mode
    ) -> LLMResponse: ...
```

### Implémentation OpenRouter (principale)

```python
# src/ai/llm/openrouter.py
class OpenRouterProvider(LLMProvider):
    # Endpoint: https://openrouter.ai/api/v1/chat/completions
    # Headers: Authorization: Bearer <OPENROUTER_API>
    #          HTTP-Referer: https://orionis.bot
    #          X-Title: ORIONIS
    # Modèles disponibles: 'zai-org/glm-5', 'openai/gpt-4o',
    #   'anthropic/claude-3.5-sonnet', 'meta-llama/llama-3.1-70b'…
```

### Implémentation OpenAI (alternative)

```python
# src/ai/llm/openai_provider.py
class OpenAIProvider(LLMProvider): ...
```

### Implémentation locale (futur)

```python
# src/ai/llm/local_provider.py
class LocalOllamaProvider(LLMProvider):
    # Endpoint: http://localhost:11434/api/chat
```

### Factory

```python
# src/ai/llm/factory.py
def get_llm_provider() -> LLMProvider:
    # Lit LLM_PROVIDER dans config ('openrouter' | 'openai' | 'local')
    # Retourne l'instance correspondante
```

---

## Plan d'action

### Étape 3.1 — Créer la structure `src/ai/llm/`

```
src/ai/
├── __init__.py
└── llm/
    ├── __init__.py
    ├── base.py            # LLMMessage, LLMResponse, LLMProvider (Protocol)
    ├── openrouter.py      # OpenRouterProvider
    ├── openai_provider.py # OpenAIProvider
    ├── local.py           # LocalOllamaProvider (stub pour futur)
    └── factory.py         # get_llm_provider()
```

### Étape 3.2 — Implémenter `OpenRouterProvider`

- Utiliser `httpx.AsyncClient` (déjà dans les dépendances)
- Endpoint : `https://openrouter.ai/api/v1/chat/completions`
- Support du **JSON mode** (`response_format: {"type": "json_object"}`)
- Gestion des erreurs (rate limit, timeout, modèle invalide)
- Logging : modèle utilisé, tokens consommés, latence
- Timeout configurable (défaut 30s)

### Étape 3.3 — Implémenter la factory + config

Ajouter dans `config.py` :

```python
LLM_PROVIDER: str = "openrouter"          # 'openrouter' | 'openai' | 'local'
LLM_DEFAULT_MODEL: str = "zai-org/glm-5"  # modèle par défaut
LLM_TEMPERATURE: float = 0.7
LLM_MAX_TOKENS: int = 2000
LLM_TIMEOUT_SECONDS: float = 30.0
OPENAI_API_KEY: str | None = None         # si provider=openai
OLLAMA_BASE_URL: str = "http://localhost:11434"  # si provider=local
```

### Étape 3.4 — Utilitaires de prompt

Créer `src/ai/prompts/` avec des templates réutilisables :

```
src/ai/prompts/
├── __init__.py
├── system.py        # persona système de Orionis
└── templates/       # templates par analyste (étape 05)
```

Le persona système : « Tu es Orionis, analyste crypto autonome… »

### Étape 3.5 — Test de bout en bout

Créer `src/scripts/test_llm.py` :
- Envoie un prompt simple (« Analyse BTC en 3 points »)
- Vérifie qu'on récupère une réponse cohérente
- Teste le JSON mode avec un prompt structuré
- Affiche le modèle utilisé et les tokens

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/ai/__init__.py` | **Créer** |
| `src/ai/llm/__init__.py` | **Créer** |
| `src/ai/llm/base.py` | **Créer** |
| `src/ai/llm/openrouter.py` | **Créer** |
| `src/ai/llm/openai_provider.py` | **Créer** |
| `src/ai/llm/local.py` | **Créer** (stub) |
| `src/ai/llm/factory.py` | **Créer** |
| `src/ai/prompts/__init__.py` | **Créer** |
| `src/ai/prompts/system.py` | **Créer** |
| `src/config.py` | **Modifier** (variables LLM) |
| `src/requirements.txt` | **Vérifier** (httpx déjà présent) |
| `src/scripts/test_llm.py` | **Créer** |

---

## Critères de validation

- [ ] `get_llm_provider()` retourne le bon provider selon `LLM_PROVIDER`
- [ ] `OpenRouterProvider.complete()` renvoie une réponse non vide
- [ ] Le JSON mode fonctionne (réponse parsable en dict)
- [ ] Les erreurs (timeout, 401, 429) sont catchées et loggées
- [ ] `test_llm.py` s'exécute avec succès
- [ ] `pyright` passe sans erreur
- [ ] Le code des analystes (étape 05) n'aura **aucune** dépendance directe
      vers OpenRouter — uniquement vers `LLMProvider`

---

## Notes

- OpenRouter facture au token ; logger les coûts pour suivi.
- Prévoir un **fallback** : si le modèle primaire (GLM-5) est indisponible,
  fallback automatique vers un modèle secondaire (ex: `openai/gpt-4o-mini`).
- Le `response_format` JSON mode n'est pas supporté par tous les modèles ;
  prévoir un retry sans JSON mode + parsing manuel si échec.
- Ne **jamais** envoyer de secrets ou clés API dans les prompts.
