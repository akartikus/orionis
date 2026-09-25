-- ====================================================================
-- MIGRATION 005 : TABLE ONCHAIN_DATA (Métriques on-chain)
-- ====================================================================
-- Utilité : Stocke les métriques on-chain par actif (adresses actives,
-- hash rate, nombre de transactions, whale inflow).
-- Source : Glassnode, CryptoQuant, Blockchain native.

CREATE TABLE IF NOT EXISTS public.onchain_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset VARCHAR(20) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,      -- 'active_addresses', 'hash_rate', 'tx_count', 'whale_inflow'
    value NUMERIC(30, 8) NOT NULL,
    source VARCHAR(100) NOT NULL,          -- 'Glassnode', 'CryptoQuant', 'Blockchain'
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour accélérer les requêtes par actif, métrique et date
CREATE INDEX IF NOT EXISTS idx_onchain_asset_metric_time
    ON public.onchain_data(asset, metric_name, timestamp DESC);

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.onchain_data ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.onchain_data IS 'Métriques on-chain par actif (adresses actives, hash rate, whale inflow)';
