# ÉTAPE 05 — AI Analysis Layer (3 analystes + synthèse)

> **Priorité** : 🔴 Critique
> **Prérequis** : Étapes 02 (Orionis Core) + 03 (LLM Provider) + 04 (collectors)
> **Objectif** : Construire le cerveau analytique : analyste marché, analyste
> fondamental, analyste risque, et synthèse décisionnelle.

---

## Contexte

C'est la pièce maîtrente manquante. `src/strategy/engine.py` est vide.
La vision prévoit 4 sous-agents qui reçoivent données marché, portefeuille,
news, historique, et produisent une analyse structurée.

---

## Architecture cible

```
         AnalysisContext (données agrégées)
                    |
     ┌──────────────┼──────────────┐
     │              │              │
 MarketAnalyst  FundamentalAnalyst  RiskAnalyst
     │              │              │
     └──────┬───────┴──────┬───────┘
            │              │
     ai_reports (3)   DecisionSynthesizer
            │              │
            └──────┬───────┘
                   │
            Decision (BUY/SELL/HOLD)
                   │
            decisions (table)
```

---

## Structure à créer

```
src/ai/
├── llm/                    # (étape 03 — déjà créé)
├── prompts/
│   ├── system.py           # persona Orionis
│   ├── market.py           # template analyste marché
│   ├── fundamental.py      # template analyste fondamental
│   ├── risk.py             # template analyste risque
│   └── synthesis.py        # template synthèse
├── analysts/
│   ├── __init__.py
│   ├── base.py             # BaseAnalyst (classe abstraite)
│   ├── market.py           # MarketAnalyst
│   ├── fundamental.py      # FundamentalAnalyst
│   └── risk.py             # RiskAnalyst
├── synthesizer.py          # DecisionSynthesizer
├── context.py              # AnalysisContext builder
└── engine.py               # AnalysisEngine (orchestre tout)
```

---

## Composants détaillés

### 5.1 — `AnalysisContext` (`src/ai/context.py`)

Agrège toutes les données depuis Supabase :

```python
class AnalysisContext(BaseModel):
    asset: str
    market_snapshot: dict
    price_history: list[dict]
    indicators: dict               # RSI, MACD, EMA…
    news: list[dict]               # articles + sentiment
    macro: dict                    # indicateurs macro
    onchain: dict
    portfolio_position: dict | None
    recent_decisions: list[dict]

class ContextBuilder:
    async def build(self, asset: str) -> AnalysisContext: ...
```

### 5.2 — `BaseAnalyst` (`src/ai/analysts/base.py`)

```python
class BaseAnalyst(ABC):
    report_type: str  # 'MARKET' | 'FUNDAMENTAL' | 'RISK'
    async def analyze(self, context: AnalysisContext) -> AIReport:
        # 1. Construit le prompt (template + context)
        # 2. Appelle LLMProvider.complete() avec JSON mode
        # 3. Parse → AIReport
        # 4. Stocke dans ai_reports
```

### 5.3 — `MarketAnalyst`

Analyse : tendance, momentum, volatilité, cycles.
Entrées : prix, volumes, indicateurs (RSI, MACD, EMA, SMA).

Sortie JSON :
```json
{
  "trend": "bullish|bearish|neutral",
  "momentum": "strong|weak|diverging",
  "volatility": "high|medium|low",
  "cycle_phase": "accumulation|markup|distribution|decline",
  "market_state": "positif|neutre|négatif",
  "risk_level": "faible|moyen|élevé",
  "confidence": 0-100,
  "reasoning": "..."
}
```

### 5.4 — `FundamentalAnalyst`

Analyse : utilité, adoption, activité réseau, tokenomics, concurrence.
Entrées : on-chain, news, market_cap, supply.

Sortie JSON :
```json
{
  "utility_score": 0-100,
  "adoption_score": 0-100,
  "network_activity": "high|medium|low",
  "tokenomics": "favorable|neutral|unfavorable",
  "competition": "leading|challenged|lagging",
  "fundamental_state": "positif|neutre|négatif",
  "confidence": 0-100,
  "reasoning": "..."
}
```

### 5.5 — `RiskAnalyst`

Cherche les faiblesses : pire hypothèse, risques ignorés, taille de position.
Entrées : portfolio_position, exposure, strategy_config.

Sortie JSON :
```json
{
  "worst_case_scenario": "...",
  "ignored_risks": ["..."],
  "position_size_risk": "too_large|appropriate|too_small",
  "correlation_risk": "high|medium|low",
  "liquidity_risk": "high|medium|low",
  "overall_risk": "faible|moyen|élevé",
  "confidence": 0-100,
  "reasoning": "..."
}
```

### 5.6 — `DecisionSynthesizer` (`src/ai/synthesizer.py`)

Combine les 3 rapports → décision finale.

```python
class DecisionSynthesizer:
    async def synthesize(
        self, context: AnalysisContext, reports: list[AIReport]
    ) -> Decision:
        # Prompt : « Voici 3 rapports pour {asset}. Synthétise
        #   BUY/SELL/HOLD avec allocation, confiance, raison. JSON. »
```

Sortie → `Decision` stockée dans `decisions` + `raw_analysis` (JSONB).

### 5.7 — `AnalysisEngine` (`src/ai/engine.py`)

Remplace `src/strategy/engine.py` (vide) :

```python
class AnalysisEngine:
    def __init__(self, llm: LLMProvider): ...
    async def analyze_asset(self, asset: str) -> Decision:
        # 1. Build context
        # 2. Run 3 analysts en parallèle (asyncio.gather)
        # 3. Synthesize
        # 4. Store in decisions + ai_reports
    async def analyze_portfolio(self) -> list[Decision]: ...
```

---

## Plan d'action

| # | Tâche |
|---|---|
| 5.1 | `src/ai/context.py` |
| 5.2 | `src/ai/analysts/base.py` |
| 5.3 | `src/ai/analysts/market.py` |
| 5.4 | `src/ai/analysts/fundamental.py` |
| 5.5 | `src/ai/analysts/risk.py` |
| 5.6 | `src/ai/synthesizer.py` |
| 5.7 | `src/ai/engine.py` (remplace strategy/engine.py) |
| 5.8 | Prompts (system, market, fundamental, risk, synthesis) |
| 5.9 | Intégration Orionis Core (workflow daily_analysis) |
| 5.10 | Endpoint `POST /api/v1/analyse?asset=BTC` |
| 5.11 | Script `src/scripts/test_analysis.py` |

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/ai/context.py` | **Créer** |
| `src/ai/analysts/*.py` | **Créer** (4 fichiers) |
| `src/ai/synthesizer.py` | **Créer** |
| `src/ai/engine.py` | **Créer** |
| `src/ai/prompts/*.py` | **Créer** (5 fichiers) |
| `src/strategy/engine.py` | **Supprimer/rediriger** |
| `src/core/workflows/daily_analysis.py` | **Modifier** |
| `src/main.py` | **Modifier** |
| `src/scripts/test_analysis.py` | **Créer** |

---

## Critères de validation

- [ ] `analyze_asset("BTC")` produit une `Decision` valide
- [ ] Les 3 rapports sont stockés dans `ai_reports`
- [ ] La décision est stockée dans `decisions` avec `raw_analysis`
- [ ] `action` ∈ {BUY, SELL, HOLD}, `confidence` ∈ [0, 100]
- [ ] Le workflow `daily_analysis` produit des décisions pour tous les assets
- [ ] `POST /api/v1/analyse?asset=BTC` retourne la décision
- [ ] `test_analysis.py` valide une analyse complète
- [ ] `pyright` passe sans erreur

---

## Notes

- Les 3 analystes tournent **en parallèle** (`asyncio.gather`)
- Le `ContextBuilder` doit être résilient (si on-chain absent, continuer)
- Logger le coût en tokens de chaque analyse
- Prévoir un mode « dry-run » (analyse sans exécution)

