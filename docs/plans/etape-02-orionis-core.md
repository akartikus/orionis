# ÉTAPE 02 — Orionis Core (Orchestrateur central)

> **Priorité** : 🔴 Critique
> **Prérequis** : Étapes 00 + 01 terminées
> **Objectif** : Créer le coordinateur principal qui déclenche les services,
> gère les workflows, route les données vers l'IA et orchestre l'exécution.

---

## Contexte

Actuellement, `src/main.py` joue à la fois le rôle d'API FastAPI **et** de
scheduler. Il n'y a pas de couche d'orchestration centrale : les collectors
tournent en parallèle sans coordination, il n'y a pas de workflow
« collecte → analyse → décision → exécution → notification ».

La vision prévoit un **Orionis Core** qui :
- déclenche les services (collectors, IA, portfolio manager, executor) ;
- gère les workflows (séquences d'étapes) ;
- envoie les données aux agents IA ;
- reçoit les résultats ;
- gère les événements (alertes, triggers) ;
- informe Discord.

---

## Architecture cible

```
                    OrionisCore (singleton)
                           |
            ┌──────────────┼──────────────┐
            │              │              │
     WorkflowEngine   EventBus    DecisionPipeline
     (séquences)     (pub/sub)    (analyse→décision)
            │              │              │
            └──────┬───────┴──────┬───────┘
                   │              │
            Collectors        AI Layer + Portfolio Manager + Executor
```

### Composants à créer

#### 1. `EventBus` — bus d'événements asynchrone (pub/sub)

Pattern simple in-process : les collectors et le scheduler émettent des
événements (`PRICE_DROP`, `NEWS_CRITICAL`, `DAILY_TICK`), les handlers
souscrits réagissent.

```python
# src/core/event_bus.py
class EventBus:
    async def publish(self, event_type: str, payload: dict) -> None
    def subscribe(self, event_type: str, handler: Callable) -> None
```

#### 2. `WorkflowEngine` — moteur de workflows

Définit et exécute des séquences d'étapes asynchrones avec gestion d'erreur,
retry, logging dans `orchestration_logs`.

```python
# src/core/workflow.py
class Workflow:
    name: str
    steps: list[WorkflowStep]

class WorkflowEngine:
    async def run(self, workflow: Workflow) -> OrchestrationLog
```

Workflows prédéfinis :
- `daily_analysis` : collecte → analyse IA → décisions → (validation) → exécution → rapport Discord
- `urgent_analysis` : analyse IA immédiate sur un asset → décision → notification
- `portfolio_rebalance` : vérification allocation → ajustements
- `data_sync_all` : lance tous les collectors en séquence

#### 3. `OrionisCore` — façade principale

Singleton qui câble l'EventBus, le WorkflowEngine, et expose des méthodes
haut-niveau utilisées par l'API FastAPI et le scheduler.

```python
# src/core/orionis_core.py
class OrionisCore:
    def __init__(self) -> None
    async def start(self) -> None          # init bus, workflows, subscriptions
    async def stop(self) -> None
    async def run_daily_analysis(self) -> OrchestrationLog
    async def run_urgent_analysis(self, asset: str, reason: str) -> OrchestrationLog
    async def handle_alert(self, alert: Alert) -> None
```

---

## Plan d'action

### Étape 2.1 — Créer le module `src/core/`

```
src/core/
├── __init__.py
├── event_bus.py          # EventBus async (pub/sub in-process)
├── workflow.py           # Workflow, WorkflowStep, WorkflowEngine
├── orionis_core.py             # OrionisCore (façade singleton)
├── interfaces.py         # Protocols (stubs pour couches futures)
└── workflows/
    ├── __init__.py
    ├── daily_analysis.py
    ├── urgent_analysis.py
    └── data_sync.py
```

### Étape 2.2 — Implémenter `EventBus`

- Dictionnaire `event_type → list[handler]`
- `publish()` : appelle tous les handlers en parallèle (`asyncio.gather`)
- `subscribe()` : enregistre un handler
- Gestion d'erreur par handler (un handler qui crash n'empêche pas les autres)
- Persistance : à l'émission d'un événement critique, créer une ligne dans
  `alerts` si non déjà traité

### Étape 2.3 — Implémenter `WorkflowEngine`

- Un `WorkflowStep` = `(name, async_callable, retry_count, timeout)`
- `WorkflowEngine.run()` :
  1. Crée une ligne `orchestration_logs` (status=STARTED)
  2. Exécute chaque step en séquence
  3. Sur erreur : retry, puis marquer FAILED
  4. Met à jour `orchestration_logs` (finished_at, duration, status, details)
- Retourne le log final

### Étape 2.4 — Implémenter `OrionisCore`

- Initialise l'EventBus et le WorkflowEngine
- Enregistre les handlers d'événements :
  - `PRICE_DROP` → `run_urgent_analysis(asset)`
  - `DAILY_TICK` → `run_daily_analysis()`
- Expose les méthodes haut-niveau

### Étape 2.5 — Intégrer dans `main.py`

- Instancier `OrionisCore` dans le `lifespan` de FastAPI
- Remplacer les jobs APScheduler actuels par :
  - Job portfolio sync (existant, conservé)
  - Job market sync (existant + détection d'alertes prix → EventBus)
  - Job news sync (existant + détection news critique → EventBus)
  - Job daily : `orionis_core.run_daily_analysis()` (cron 08h00)
- Ajouter endpoints API :
  - `POST /api/v1/orionis/daily-analysis`
  - `POST /api/v1/orionis/urgent-analysis`
  - `GET /api/v1/orionis/logs`

### Étape 2.6 — Stubs pour les couches dépendantes

Les workflows appellent l'AI Layer (étape 05) et le Portfolio Manager
(étape 06) qui n'existent pas encore. Créer des **stubs** (interfaces avec
`NotImplementedError` ou retour neutre) pour que les workflows soient
câblés et testables, puis implémentés dans les étapes suivantes.

```python
# src/core/interfaces.py
class AIAnalysisInterface(Protocol):
    async def analyze(self, context: AnalysisContext) -> Decision: ...

class PortfolioManagerInterface(Protocol):
    async def validate_decision(self, decision: Decision) -> ValidationResult: ...
```

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/core/__init__.py` | **Créer** |
| `src/core/event_bus.py` | **Créer** |
| `src/core/workflow.py` | **Créer** |
| `src/core/orionis_core.py` | **Créer** |
| `src/core/interfaces.py` | **Créer** |
| `src/core/workflows/*.py` | **Créer** (4 fichiers) |
| `src/main.py` | **Modifier** |
| `src/config.py` | **Modifier** |

---

## Configuration à ajouter (`config.py`)

```python
DAILY_ANALYSIS_HOUR: int = 8
DAILY_ANALYSIS_MINUTE: int = 0
PRICE_DROP_THRESHOLD_PCT: float = 8.0
PRICE_SURGE_THRESHOLD_PCT: float = 8.0
```

---

## Critères de validation

- [ ] `OrionisCore` s'initialise au démarrage de l'API (log visible)
- [ ] `EventBus.publish` appelle bien tous les handlers souscrits
- [ ] `WorkflowEngine` crée une ligne `orchestration_logs` à chaque exécution
- [ ] Le workflow `data_sync` s'exécute sans erreur
- [ ] Les endpoints `/api/v1/orionis/*` répondent
- [ ] Le job quotidien est planifié à 08h00
- [ ] `pyright` passe sans erreur

---

## Notes

- L'EventBus est **in-process** (pas de Redis/RabbitMQ) — suffisant pour un
  bot mono-instance. Évolution future possible avec Supabase Realtime.
- Les workflows doivent être **idempotents** (relance sans double-exécution).
- Toutes les étapes critiques doivent être loggées dans `orchestration_logs`.

