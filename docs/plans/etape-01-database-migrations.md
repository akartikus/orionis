# ÉTAPE 01 — Migrations DB complémentaires

> **Priorité** : 🔴 Critique
> **Prérequis** : Étape 00 terminée
> **Objectif** : Ajouter les tables manquantes nécessaires aux futures couches
> (macro économique, on-chain, alertes, configuration de stratégie, rapports IA).

---

## Contexte

Le schéma actuel (`001`, `002`, `003`) couvre : `portfolio`,
`bot_managed_assets`, `transactions`, `orders`, `decisions`, `market_snapshots`,
`news`, `transactions_log`.

Les couches à venir (Macro Collector, On-chain, Orionis Core, AI Analysis,
Portfolio Manager, Event Scheduler) nécessitent de nouvelles tables pour
stocker :

- les données macroéconomiques (taux, inflation, chômage…) ;
- les données on-chain (activité réseau, whale movements…) ;
- la configuration de stratégie (capital initial, limites d'allocation, stop-loss) ;
- les alertes / événements détectés (BTC -8%, news critique…) ;
- les rapports IA structurés (sortie des 3 analystes + synthèse) ;
- les logs d'orchestration (workflow exécutés, statuts) ;
- le journal d'audit d'exécution (sécurité, limites).

---

## Tables à créer

### Migration `004_add_macro_data_table.sql`

Table `macro_indicators` — données macroéconomiques horodatées.

```sql
CREATE TABLE IF NOT EXISTS public.macro_indicators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indicator_name VARCHAR(50) NOT NULL,   -- 'interest_rate', 'inflation_cpi', 'unemployment', 'dxy', 'sp500', 'liquidity'
    value NUMERIC(20, 8) NOT NULL,
    unit VARCHAR(20),                      -- '%', 'index', 'USD'
    source VARCHAR(100) NOT NULL,          -- 'FRED', 'Yahoo Finance'
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_macro_indicator_name_time
    ON public.macro_indicators(indicator_name, timestamp DESC);
ALTER TABLE public.macro_indicators ENABLE ROW LEVEL SECURITY;
```

### Migration `005_add_onchain_data_table.sql`

Table `onchain_data` — métriques on-chain par actif.

```sql
CREATE TABLE IF NOT EXISTS public.onchain_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset VARCHAR(20) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,      -- 'active_addresses', 'hash_rate', 'tx_count', 'whale_inflow'
    value NUMERIC(30, 8) NOT NULL,
    source VARCHAR(100) NOT NULL,          -- 'Glassnode', 'CryptoQuant', 'Blockchain'
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_onchain_asset_metric_time
    ON public.onchain_data(asset, metric_name, timestamp DESC);
ALTER TABLE public.onchain_data ENABLE ROW LEVEL SECURITY;
```

### Migration `006_add_strategy_config_table.sql`

Table `strategy_config` — paramètres de stratégie (une ligne active).

```sql
CREATE TABLE IF NOT EXISTS public.strategy_config (
    id SERIAL PRIMARY KEY,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    initial_capital_eur NUMERIC(20, 8) NOT NULL,
    max_allocation_per_asset_pct NUMERIC(5, 2) NOT NULL DEFAULT 40.00,
    max_total_exposure_pct NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    stop_loss_pct NUMERIC(5, 2) DEFAULT 15.00,
    take_profit_pct NUMERIC(5, 2) DEFAULT 30.00,
    max_order_amount_eur NUMERIC(20, 8) NOT NULL DEFAULT 500.00,
    daily_trade_limit INT NOT NULL DEFAULT 10,
    min_confidence_threshold NUMERIC(5, 2) NOT NULL DEFAULT 60.00,
    allowed_assets TEXT[],
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TRIGGER set_strategy_config_updated_at
    BEFORE UPDATE ON public.strategy_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
ALTER TABLE public.strategy_config ENABLE ROW LEVEL SECURITY;
```


### Migration `007_add_alerts_table.sql`

Table `alerts` — événements détectés (chute de prix, news critique, seuil).

```sql
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(30) NOT NULL,       -- 'PRICE_DROP', 'PRICE_SURGE', 'NEWS_CRITICAL', 'THRESHOLD', 'MANUAL'
    asset VARCHAR(20),
    severity VARCHAR(10) NOT NULL DEFAULT 'INFO',  -- 'INFO', 'WARNING', 'CRITICAL'
    message TEXT NOT NULL,
    payload JSONB,                          -- données contextuelles
    triggered BOOLEAN NOT NULL DEFAULT FALSE,      -- Orionis Core a-t-il traité ?
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered_created
    ON public.alerts(triggered, created_at DESC);
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
```

### Migration `008_add_ai_reports_table.sql`

Table `ai_reports` — rapports complets des analystes IA (complémentaire de
`decisions` qui stocke la décision finale).

```sql
CREATE TABLE IF NOT EXISTS public.ai_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset VARCHAR(20) NOT NULL,
    report_type VARCHAR(30) NOT NULL,       -- 'MARKET', 'FUNDAMENTAL', 'RISK', 'SYNTHESIS'
    content JSONB NOT NULL,                 -- rapport structuré du sous-agent
    model_used VARCHAR(50) NOT NULL,
    confidence NUMERIC(5, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_reports_asset_type_time
    ON public.ai_reports(asset, report_type, created_at DESC);
ALTER TABLE public.ai_reports ENABLE ROW LEVEL SECURITY;
```

### Migration `009_add_orchestration_logs_table.sql`

Table `orchestration_logs` — trace des workflows exécutés par Orionis Core.

```sql
CREATE TABLE IF NOT EXISTS public.orchestration_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_name VARCHAR(50) NOT NULL,     -- 'daily_analysis', 'urgent_analysis', 'portfolio_rebalance'
    status VARCHAR(20) NOT NULL,            -- 'STARTED', 'SUCCESS', 'FAILED', 'SKIPPED'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    duration_ms INT,
    details JSONB,                          -- résumé des étapes, erreurs
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_orch_logs_status_started
    ON public.orchestration_logs(status, started_at DESC);
ALTER TABLE public.orchestration_logs ENABLE ROW LEVEL SECURITY;
```

---

## Plan d'action

1. Créer les 6 fichiers SQL dans `src/database/schema/` (004 → 009)
2. Exécuter chaque migration dans l'ordre via le SQL Editor Supabase
3. Créer les modèles Pydantic dans `src/database/models/` :
   - `macro.py` → `MacroIndicatorBase/Create/Response`
   - `onchain.py` → `OnchainDataBase/Create/Response`
   - `strategy_config.py` → `StrategyConfigBase/Create/Response`
   - `alert.py` → `AlertBase/Create/Response`
   - `ai_report.py` → `AIReportBase/Create/Response`
   - `orchestration_log.py` → `OrchestrationLogBase/Create/Response`
4. Mettre à jour `src/database/models/__init__.py` (exports)
5. Insérer une ligne initiale dans `strategy_config` (capital de test, limites
   conservatrices) marquée `is_active = true`
6. Mettre à jour le `README.md` (section Base de données)

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/database/schema/004_*.sql` → `009_*.sql` | **Créer** (6 fichiers) |
| `src/database/models/macro.py` | **Créer** |
| `src/database/models/onchain.py` | **Créer** |
| `src/database/models/strategy_config.py` | **Créer** |
| `src/database/models/alert.py` | **Créer** |
| `src/database/models/ai_report.py` | **Créer** |
| `src/database/models/orchestration_log.py` | **Créer** |
| `src/database/models/__init__.py` | **Modifier** |
| `README.md` | **Modifier** |

---

## Critères de validation

- [ ] Les 6 migrations s'exécutent sans erreur dans Supabase
- [ ] Les tables apparaissent avec RLS activée
- [ ] Les modèles Pydantic passent `pyright`
- [ ] Une ligne `strategy_config` active existe avec valeurs conservatives
- [ ] Le `README.md` mentionne toutes les nouvelles tables
- [ ] `__init__.py` exporte tous les nouveaux modèles

---

## Schéma complet après cette étape

```
portfolio              ✅ (001)
bot_managed_assets     ✅ (001)
transactions           ✅ (001)
orders                 ✅ (001)
decisions              ✅ (001)
market_snapshots       ✅ (001)
news                   ✅ (002)
transactions_log       ✅ (003)
macro_indicators       🆕 (004)
onchain_data           🆕 (005)
strategy_config        🆕 (006)
alerts                 🆕 (007)
ai_reports             🆕 (008)
orchestration_logs     🆕 (009)
```

