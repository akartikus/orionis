-- ====================================================================
-- MIGRATION 004 : TABLE MACRO_INDICATORS (Données macroéconomiques)
-- ====================================================================
-- Utilité : Stocke les indicateurs macro horodatés (taux d'intérêt,
-- inflation CPI, chômage, Dollar Index DXY, S&P 500, liquidité).
-- Source : FRED, Yahoo Finance.

CREATE TABLE IF NOT EXISTS public.macro_indicators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    indicator_name VARCHAR(50) NOT NULL,   -- 'interest_rate', 'inflation_cpi', 'unemployment', 'dxy', 'sp500', 'liquidity'
    value NUMERIC(20, 8) NOT NULL,
    unit VARCHAR(20),                      -- '%', 'index', 'USD'
    source VARCHAR(100) NOT NULL,          -- 'FRED', 'Yahoo Finance'
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour accélérer les requêtes par indicateur et date (du plus récent au plus ancien)
CREATE INDEX IF NOT EXISTS idx_macro_indicator_name_time
    ON public.macro_indicators(indicator_name, timestamp DESC);

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.macro_indicators ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.macro_indicators IS 'Indicateurs macroéconomiques horodatés (taux, inflation, DXY, S&P 500)';
