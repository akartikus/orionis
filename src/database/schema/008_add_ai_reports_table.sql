-- ====================================================================
-- MIGRATION 008 : TABLE AI_REPORTS (Rapports des analystes IA)
-- ====================================================================
-- Utilité : Stocke les rapports complets produits par les sous-agents IA
-- (Market, Fundamental, Risk, Synthesis). Complémentaire de la table
-- 'decisions' qui stocke la décision finale uniquement.

CREATE TABLE IF NOT EXISTS public.ai_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset VARCHAR(20) NOT NULL,
    report_type VARCHAR(30) NOT NULL,       -- 'MARKET', 'FUNDAMENTAL', 'RISK', 'SYNTHESIS'
    content JSONB NOT NULL,                 -- rapport structuré du sous-agent
    model_used VARCHAR(50) NOT NULL,
    confidence NUMERIC(5, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour accélérer les requêtes par actif, type de rapport et date
CREATE INDEX IF NOT EXISTS idx_ai_reports_asset_type_time
    ON public.ai_reports(asset, report_type, created_at DESC);

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.ai_reports ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.ai_reports IS 'Rapports structurés des analystes IA (Market, Fundamental, Risk, Synthesis)';
