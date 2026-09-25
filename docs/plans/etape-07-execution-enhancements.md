# ÉTAPE 07 — Execution Engine (sécurités & lien décision)

> **Priorité** : 🟠 Élevée
> **Prérequis** : Étapes 05 (AI) + 06 (Portfolio Manager)
> **Objectif** : Renforcer l'Execution Engine avec sécurités, lien
> décision→ordre, suivi d'ordres, et journalisation complète.

---

## Contexte

L'`OrderExecutor` actuel (`src/execution/order_executor.py`) exécute des
ordres marché manuels via Discord `/trade`. Il manque :

- le lien entre une **décision IA** et l'ordre exécuté ;
- le suivi du **cycle de vie des ordres** (table `orders` inutilisée) ;
- les **sécurités** (pas de retrait, limites de montant, journalisation) ;
- l'exécution **automatique** (via workflow Orionis Core) avec validation
  préalable du Portfolio Manager ;
- la gestion des **ordres limit** (pas seulement marché).

---

## Architecture cible

```
Decision (validée par PortfolioManager)
      |
ExecutionEngine.execute_decision(decision, validation)
      |
      ├── Vérifications finales (safety checks)
      ├── Création ordre dans 'orders' (status=PENDING)
      ├── Appel Bitvavo API (create_order)
      ├── Mise à jour 'orders' (status=FILLED, exchange_order_id)
      ├── Log dans 'transactions_log'
      ├── Mise à jour 'bot_managed_assets'
      ├── Marquer 'decisions.executed = true'
      └── Retour ExecutionResult
```

---

## Composants à créer/modifier

### Structure

```
src/execution/
├── __init__.py
├── engine.py            # ExecutionEngine (nouveau)
├── order_executor.py    # Conservé pour compatibilité /trade manuel
├── safety.py            # SafetyChecker
└── tracker.py           # OrderTracker
```

### 7.1 — `ExecutionEngine` (`src/execution/engine.py`)

```python
class ExecutionEngine:
    async def execute_decision(
        self, decision: Decision, validation: ValidationResult
    ) -> ExecutionResult:
        # 1. Safety checks finaux
        # 2. Calculer montant (adjusted_amount si présent)
        # 3. Créer ordre dans 'orders' (PENDING)
        # 4. Appeler Bitvavo (market ou limit)
        # 5. Update 'orders' (FILLED + exchange_order_id)
        # 6. Log 'transactions_log'
        # 7. Update 'bot_managed_assets'
        # 8. Marquer 'decisions.executed = true'

    async def execute_manual_order(self, symbol, side, amount) -> dict: ...
```

### 7.2 — `SafetyChecker` (`src/execution/safety.py`)

Vérifications de **dernière chance** avant l'appel API réel :

```python
class SafetyChecker:
    def check_no_withdrawal(self, operation) -> None     # refuse retraits
    def check_amount_limit(self, amount_eur, max_eur) -> None
    def check_symbol_allowed(self, symbol, allowed) -> None
    def check_daily_limit(self, daily_count, limit) -> None
```

→ Lève `SafetyViolationError` si une règle est violée.

### 7.3 — `OrderTracker` (`src/execution/tracker.py`)

Suit le cycle de vie dans la table `orders` :

```python
class OrderTracker:
    async def create_order_record(self, decision) -> str: ...
    async def mark_filled(self, order_id, exchange_id, avg_price, filled): ...
    async def mark_canceled(self, order_id, reason): ...
    async def sync_pending_orders(self): ...
        # Pour chaque PENDING, vérifier statut réel sur Bitvavo (fetch_order)
```

### 7.4 — Lien `decisions` ↔ `orders`

- Créer une ligne `orders` avec `origin='ORIONIS'` à chaque exécution
- Lier `decisions.order_id` ← `orders.id`
- Marquer `decisions.executed = true` après succès
- `decisions.performance_score` sera calculé ultérieurement

### 7.5 — Support ordres limit (optionnel v1)

Ajouter la possibilité de passer un ordre **limit** (avec prix). Le
`OrderTracker` suivra les PENDING jusqu'à exécution ou expiration.

---

## Plan d'action

| # | Tâche |
|---|---|
| 7.1 | `src/execution/safety.py` |
| 7.2 | `src/execution/tracker.py` |
| 7.3 | `src/execution/engine.py` |
| 7.4 | Refactor `order_executor.py` (déléguer à engine) |
| 7.5 | Intégration workflow Orionis Core |
| 7.6 | Migration `010_add_decisions_order_link.sql` |
| 7.7 | Endpoint `GET /api/v1/orders` |
| 7.8 | Script `src/scripts/test_execution.py` |

---

## Migration `010_add_decisions_order_link.sql`

```sql
ALTER TABLE public.decisions
    ADD COLUMN IF NOT EXISTS order_id UUID REFERENCES public.orders(id);
ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS decision_id UUID REFERENCES public.decisions(id);
```

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/execution/__init__.py` | **Créer/Modifier** |
| `src/execution/safety.py` | **Créer** |
| `src/execution/tracker.py` | **Créer** |
| `src/execution/engine.py` | **Créer** |
| `src/execution/order_executor.py` | **Modifier** |
| `src/core/workflows/daily_analysis.py` | **Modifier** |
| `src/main.py` | **Modifier** |
| `src/database/schema/010_*.sql` | **Créer** |
| `src/scripts/test_execution.py` | **Créer** |

---

## Configuration à ajouter (`config.py`)

```python
AUTO_EXECUTE_DECISIONS: bool = False  # dev: False, prod: True
```

---

## Critères de validation

- [ ] `execute_decision()` crée une ligne `orders` puis exécute sur Bitvavo
- [ ] `decisions.executed` passe à `true` après succès
- [ ] `decisions.order_id` est peuplé
- [ ] `SafetyChecker` refuse un montant > `max_order_amount_eur`
- [ ] `SafetyChecker` refuse toute opération de retrait
- [ ] `OrderTracker.sync_pending_orders()` met à jour les statuts
- [ ] `GET /api/v1/orders` liste les ordres avec statut
- [ ] L'exécution automatique passe par validation + safety
- [ ] `pyright` passe sans erreur

---

## Notes

- **Sécurité absolue** : aucun code ne doit appeler `withdraw`/`transfer`.
- `AUTO_EXECUTE_DECISIONS=False` en dev → les décisions sont stockées mais
  non exécutées automatiquement (dry-run).
- En cas d'échec API Bitvavo, l'ordre reste PENDING → retry ou CANCELED.
- Logger **chaque étape** pour audit complet.

