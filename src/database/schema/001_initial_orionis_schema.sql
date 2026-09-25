-- ====================================================================
-- ÉTAPE 0 : EXTENSIONS ET FONCTIONS UTILITAIRES
-- ====================================================================

-- 0.1 Activer la génération d'identifiants uniques (UUID)
-- Utilité : Permet de générer des identifiants complexes et uniques pour les transactions/ordres
-- sans révéler le nombre total de lignes (contrairement à des ID 1, 2, 3...).
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 0.2 Fonction automatique pour mettre à jour la date de modification (updated_at)
-- Utilité : Évite de devoir écrire manuellement le temps courant en Python à chaque 'UPDATE'.
-- PostgreSQL mettra à jour 'updated_at' tout seul dès qu'une ligne change.
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ====================================================================
-- ÉTAPE 1 : TABLE PORTFOLIO (Vue globale Bitvavo)
-- ====================================================================
-- Utilité : Stocke la totalité de ton solde Bitvavo (tes investissements personnels + la part du bot).
-- Elle sert de vue d'ensemble sur le compte réel.
CREATE TABLE IF NOT EXISTS public.portfolio (
    asset VARCHAR(20) PRIMARY KEY,                   -- Ex: 'BTC', 'ETH', 'EUR'
    total_quantity NUMERIC(38, 18) NOT NULL DEFAULT 0, -- Quantité exacte (précision crypto à 18 décimales)
    average_buy_price NUMERIC(20, 8) NOT NULL DEFAULT 0, -- Prix Moyen d'Achat (PRU)
    current_price NUMERIC(20, 8) DEFAULT 0,         -- Dernier cours connu
    total_value NUMERIC(20, 8) GENERATED ALWAYS AS (total_quantity * current_price) STORED, -- Valeur calculée auto
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Active le déclencheur pour l'horodatage
CREATE TRIGGER set_portfolio_updated_at
BEFORE UPDATE ON public.portfolio
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- SÉCURITÉ : Activation de la RLS pour fermer l'accès API anonyme
ALTER TABLE public.portfolio ENABLE ROW LEVEL SECURITY;


-- ====================================================================
-- ÉTAPE 2 : TABLE BOT_MANAGED_ASSETS (Portefeuille ORIONIS)
-- ====================================================================
-- Utilité : C'est le sous-ensemble géré STRICTEMENT par ORIONIS. 
-- Séparer ce portefeuille du portefeuille global évite que l'IA ne calcule ses gains/pertes
-- en prenant en compte tes achats manuels à toi.
CREATE TABLE IF NOT EXISTS public.bot_managed_assets (
    asset VARCHAR(20) PRIMARY KEY,
    allocated_quantity NUMERIC(38, 18) NOT NULL DEFAULT 0, -- Quantité sous gestion de l'IA
    total_invested_eur NUMERIC(20, 8) NOT NULL DEFAULT 0,  -- Total d'Euros injectés par le bot
    current_price NUMERIC(20, 8) DEFAULT 0,
    current_value NUMERIC(20, 8) GENERATED ALWAYS AS (allocated_quantity * current_price) STORED,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_bot_managed_assets_updated_at
BEFORE UPDATE ON public.bot_managed_assets
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE public.bot_managed_assets ENABLE ROW LEVEL SECURITY;


-- ====================================================================
-- ÉTAPE 3 : TABLE TRANSACTIONS (Registre des mouvements)
-- ====================================================================
-- Utilité : Historique de tous les dépôts, retraits, achats et ventes.
-- Le champ 'origin' signale si l'action a été faite par 'ORIONIS' ou 'MANUAL'.
CREATE TABLE IF NOT EXISTS public.transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange_transaction_id VARCHAR(100) UNIQUE,     -- ID natif Bitvavo (évite les doublons lors des sync)
    asset VARCHAR(20) NOT NULL,
    type VARCHAR(20) NOT NULL,                       -- 'BUY', 'SELL', 'DEPOSIT', 'WITHDRAWAL', 'FEE'
    amount NUMERIC(38, 18) NOT NULL,
    price NUMERIC(20, 8) DEFAULT 0,                  
    fee NUMERIC(20, 8) NOT NULL DEFAULT 0,           -- Frais de transaction
    origin VARCHAR(20) NOT NULL DEFAULT 'ORIONIS',   -- Distingue le bot de tes actions persos
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index : Utilité -> Accélère les recherches de transactions par actif, origine ou date
CREATE INDEX IF NOT EXISTS idx_transactions_asset ON public.transactions(asset);
CREATE INDEX IF NOT EXISTS idx_transactions_origin ON public.transactions(origin);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON public.transactions(timestamp DESC);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;


-- ====================================================================
-- ÉTAPE 4 : TABLE ORDERS (Cycle de vie des ordres)
-- ====================================================================
-- Utilité : Suit les ordres envoyés à Bitvavo (en attente, exécutés, annulés).
-- Permet de rattacher un ordre réel à une décision prise par l'IA.
CREATE TABLE IF NOT EXISTS public.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange_order_id VARCHAR(100) UNIQUE,
    symbol VARCHAR(20) NOT NULL,                     -- Paire de trading (ex: 'BTC-EUR')
    side VARCHAR(10) NOT NULL,                       -- 'BUY' ou 'SELL'
    type VARCHAR(20) NOT NULL DEFAULT 'LIMIT',       -- 'LIMIT' ou 'MARKET'
    amount NUMERIC(38, 18) NOT NULL,
    filled_amount NUMERIC(38, 18) DEFAULT 0,         -- Quantité exécutée
    price NUMERIC(20, 8),
    average_filled_price NUMERIC(20, 8) DEFAULT 0,   -- Prix réel moyen d'exécution
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',   -- 'PENDING', 'FILLED', 'CANCELED'
    origin VARCHAR(20) NOT NULL DEFAULT 'ORIONIS',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_orders_updated_at
BEFORE UPDATE ON public.orders
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_orders_status ON public.orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_origin ON public.orders(origin);

ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;


-- ====================================================================
-- ÉTAPE 5 : TABLE DECISIONS (Mémoire et explicabilité de l'IA)
-- ====================================================================
-- Utilité : Enregistre le "pourquoi" de chaque décision. C'est le journal de bord d'ORIONIS.
-- Même si l'IA décide de ne RIEN faire ('HOLD'), la décision et sa justification sont conservées.
CREATE TABLE IF NOT EXISTS public.decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,                     -- 'BUY', 'SELL', 'HOLD'
    target_allocation_pct NUMERIC(5, 2),             -- % cible du sous-portefeuille
    confidence NUMERIC(5, 2) NOT NULL,               -- Note de confiance de l'IA (0-100)
    reason TEXT NOT NULL,                            -- Raisonnement en français généré par le LLM
    model_used VARCHAR(50) NOT NULL,                 -- ex: 'glm-5', 'gpt-4o' (pour comparer les modèles)
    raw_analysis JSONB,                              -- Rapports complets des sous-agents (Tech, Fondamental, Risque)
    executed BOOLEAN NOT NULL DEFAULT FALSE,         -- Indique si cette décision s'est transformée en ordre
    performance_score NUMERIC(5, 2),                -- Évaluation a posteriori (+10% / -5%)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_asset ON public.decisions(asset);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON public.decisions(created_at DESC);

ALTER TABLE public.decisions ENABLE ROW LEVEL SECURITY;


-- ====================================================================
-- ÉTAPE 6 : TABLE MARKET_SNAPSHOTS (Historique des marchés)
-- ====================================================================
-- Utilité : Conserve des photographies régulières des prix et des indicateurs (RSI, MACD...).
-- Permet à l'IA d'analyser la tendance récente sans devoir requêter l'API Bitvavo à chaque seconde.
CREATE TABLE IF NOT EXISTS public.market_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset VARCHAR(20) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,
    volume_24h NUMERIC(30, 2),
    market_cap NUMERIC(30, 2),
    indicators JSONB,                                -- Ex: {"rsi": 65.4, "macd": "bullish"}
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_snapshots_asset_time ON public.market_snapshots(asset, timestamp DESC);

ALTER TABLE public.market_snapshots ENABLE ROW LEVEL SECURITY;