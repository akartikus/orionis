-- ====================================================================
-- MIGRATION 009 : TABLE ORCHESTRATION_LOGS (Trace des workflows)
-- ====================================================================
-- Utilité : Trace l'exécution des workflows d'Orionis Core
-- (daily_analysis, urgent_analysis, portfolio_rebalance).
-- Stocke le statut, les durées et un résumé JSONB des étapes.

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

-- Index pour accélérer les requêtes par statut et date (du plus récent au plus ancien)
CREATE INDEX IF NOT EXISTS idx_orch_logs_status_started
    ON public.orchestration_logs(status, started_at DESC);

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.orchestration_logs ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.orchestration_logs IS 'Trace des workflows exécutés par Orionis Core';
