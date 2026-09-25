-- ====================================================================
-- MIGRATION : TABLE TRANSACTIONS_LOG (Traçabilité des Ordres Orionis)
-- ====================================================================

CREATE TABLE IF NOT EXISTS public.transactions_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,                    -- Ex: 'BTC/EUR'
    side VARCHAR(10) NOT NULL,                      -- 'buy' ou 'sell'
    order_type VARCHAR(10) NOT NULL,                -- 'market' ou 'limit'
    amount NUMERIC(18, 8) NOT NULL,                 -- Quantité exécutée
    price NUMERIC(18, 8) NOT NULL,                  -- Prix moyen d'exécution
    cost NUMERIC(18, 2) NOT NULL,                   -- Montant total en EUR
    bitvavo_order_id VARCHAR(100),                  -- ID de l'ordre sur Bitvavo
    origin VARCHAR(20) NOT NULL DEFAULT 'ORIONIS',  -- Marquage obligatoire
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour recherche rapide par symbole et date
CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON public.transactions_log(symbol);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON public.transactions_log(created_at DESC);

-- RLS Security
ALTER TABLE public.transactions_log ENABLE ROW LEVEL SECURITY;