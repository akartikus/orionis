# ÉTAPE 06 — Portfolio Manager (Risk / Allocation)

> **Priorité** : 🟠 Élevée
> **Prérequis** : Étapes 01 (strategy_config) + 05 (AI Analysis)
> **Objectif** : Valider les décisions IA contre les règles de risque,
> d'allocation et d'exposition avant exécution.

---

## Contexte

L'IA (étape 05) produit des décisions (BUY/SELL/HOLD). Mais avant d'exécuter
un ordre, il faut vérifier :

- l'allocation actuelle par asset vs limite max ;
- l'exposition totale du portefeuille ;
- la liquidité disponible (EUR) ;
- les stop-loss / take-profit ;
- le nombre de trades quotidiens (limite) ;
- le montant max par ordre ;
- le seuil de confiance minimum.

Aujourd'hui, rien de tout cela n'existe : l'`OrderExecutor` exécute sans
garde-fou (hors confirmation manuelle Discord).

---

## Architecture cible

```
Decision (IA)
      |
PortfolioManager.validate(decision)
      |
      ├── Check allocation       → asset > max_allocation_per_asset_pct ?
      ├── Check exposition totale → total > max_total_exposure_pct ?
      ├── Check liquidité         → EUR suffisant pour un BUY ?
      ├── Check stop-loss/take-profit → position en perte > seuil ?
      ├── Check daily trade limit  → nb trades aujourd'hui < limite ?
      ├── Check order amount       → montant < max_order_amount_eur ?
      ├── Check confidence         → confidence >= min_confidence_threshold ?
      └── Check allowed assets     → asset dans allowed_assets ?
      |
ValidationResult
      ├── approved: bool
      ├── adjusted_amount: float | None  (réduit si dépasse limite)
      ├── reasons: list[str]
      └── warnings: list[str]
```

---

## Composants à créer

### Structure

```
src/portfolio/
├── __init__.py
├── manager.py          # PortfolioManager
├── validator.py        # DecisionValidator (règles)
├── state.py            # PortfolioState (lecture état actuel)
└── rules.py            # Rule dataclass + constants
```

### 6.1 — `PortfolioState` (`src/portfolio/state.py`)

```python
class PortfolioState(BaseModel):
    total_value_eur: float
    eur_balance: float
    positions: dict[str, Position]
    total_exposure_pct: float
    daily_trade_count: int

class Position(BaseModel):
    asset: str
    quantity: float
    avg_price: float
    current_price: float
    value: float
    allocation_pct: float
    pnl_pct: float

class PortfolioStateReader:
    async def get_current_state(self) -> PortfolioState: ...
```

### 6.2 — `DecisionValidator` (`src/portfolio/validator.py`)

Chaque règle retourne un `RuleResult(approved, adjusted_amount, reason)`.

```python
class DecisionValidator:
    def validate_allocation(self, decision, state) -> RuleResult
    def validate_exposure(self, decision, state) -> RuleResult
    def validate_liquidity(self, decision, state) -> RuleResult
    def validate_stop_loss(self, decision, state) -> RuleResult
    def validate_take_profit(self, decision, state) -> RuleResult
    def validate_daily_limit(self, decision, state) -> RuleResult
    def validate_order_amount(self, decision, config) -> RuleResult
    def validate_confidence(self, decision, config) -> RuleResult
    def validate_allowed_asset(self, decision, config) -> RuleResult
```

### 6.3 — `PortfolioManager` (`src/portfolio/manager.py`)

```python
class PortfolioManager:
    async def validate_decision(
        self, decision: Decision
    ) -> ValidationResult:
        # 1. Read PortfolioState
        # 2. Read StrategyConfig (active)
        # 3. Run all validators
        # 4. Aggregate → ValidationResult

    async def get_portfolio_summary(self) -> PortfolioState: ...
```

### `ValidationResult`

```python
class ValidationResult(BaseModel):
    approved: bool
    original_decision: Decision
    adjusted_amount: float | None
    reasons: list[str]
    warnings: list[str]
```

---

## Exemple de workflow

```
IA → Decision(action=BUY, asset=SOL, amount=10%, confidence=75)

PortfolioManager.validate_decision():
  - allocation SOL : 35%, max : 40% → 35% + 10% = 45% > 40% → adjusted = 5%
  - exposure : 80% + 5% = 85% < 100% → OK
  - liquidité : 200€ ≥ 100€ → OK
  - confidence 75 ≥ 60 → OK
  - daily trades : 3 < 10 → OK

ValidationResult(approved=True, adjusted_amount=5%,
                 warnings=["Allocation SOL proche du max (35%)"])
```

---

## Plan d'action

| # | Tâche |
|---|---|
| 6.1 | `src/portfolio/state.py` |
| 6.2 | `src/portfolio/rules.py` |
| 6.3 | `src/portfolio/validator.py` |
| 6.4 | `src/portfolio/manager.py` |
| 6.5 | Intégration Orionis Core (entre analyse et exécution) |
| 6.6 | Endpoint `GET /api/v1/portfolio/state` |
| 6.7 | Endpoint `GET /api/v1/strategy/config` |
| 6.8 | Script `src/scripts/test_portfolio_manager.py` |

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/portfolio/__init__.py` | **Créer** |
| `src/portfolio/state.py` | **Créer** |
| `src/portfolio/rules.py` | **Créer** |
| `src/portfolio/validator.py` | **Créer** |
| `src/portfolio/manager.py` | **Créer** |
| `src/core/workflows/daily_analysis.py` | **Modifier** |
| `src/core/interfaces.py` | **Modifier** |
| `src/main.py` | **Modifier** |
| `src/scripts/test_portfolio_manager.py` | **Créer** |

---

## Critères de validation

- [ ] `validate_decision()` retourne un `ValidationResult`
- [ ] Un BUY dépassant `max_allocation_per_asset_pct` est ajusté/refusé
- [ ] Un BUY sans liquidité EUR est refusé
- [ ] Un SELL en stop-loss est approuvé (sécurité)
- [ ] Une décision `confidence < threshold` est refusée
- [ ] Le workflow `daily_analysis` valide avant exécution
- [ ] Les endpoints portfolio/state et strategy/config répondent
- [ ] `pyright` passe sans erreur

---

## Notes

- `StrategyConfig` lu depuis `strategy_config` (une ligne `is_active = true`)
- Compteur trades quotidiens : `transactions_log` du jour, `origin='ORIONIS'`
- Si décision **ajustée**, l'exécution utilise le montant ajusté
- Validations synchrones sauf lecture état initial (async Supabase)

