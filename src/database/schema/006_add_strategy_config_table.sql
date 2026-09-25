-- ====================================================================
-- MIGRATION 006 : TABLE STRATEGY_CONFIG (Paramètres de stratégie)
-- ====================================================================
-- Utilité : Stocke la configuration active de la stratégie d'ORIONIS
-- (capital initial, limites d'allocation, stop-loss, take-profit,
-- limite daily de trades, seuil de confiance minimal, assets autorisés).
-- Une seule ligne active (is_active = true) à la fois.

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

-- Déclencheur pour mettre à jour automatiquement updated_at
CREATE TRIGGER set_strategy_config_updated_at
    BEFORE UPDATE ON public.strategy_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.strategy_config ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.strategy_config IS 'Paramètres de stratégie ORIONIS (une ligne active)';

-- Ligne initiale conservatrice (à exécuter manuellement après création de la table)
-- Désactive les autres lignes actives puis insère la configuration de test.
INSERT INTO public.strategy_config (
    is_active,
    initial_capital_eur,
    max_allocation_per_asset_pct,
    max_total_exposure_pct,
    stop_loss_pct,
    take_profit_pct,
    max_order_amount_eur,
    daily_trade_limit,
    min_confidence_threshold,
    allowed_assets
) VALUES (
    TRUE,
    1000.00,
    30.00,
    80.00,
    10.00,
    25.00,
    250.00,
    5,
    70.00,
    ARRAY['BTC', 'ETH', 'SOL']
);
