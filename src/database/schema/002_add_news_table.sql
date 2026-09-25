-- ====================================================================
-- MIGRATION : TABLE NEWS (Actualités Crypto & Sentiment)
-- ====================================================================

CREATE TABLE IF NOT EXISTS public.news (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT UNIQUE NOT NULL,                       -- Clé unique pour éviter les doublons à l'upsert
    source VARCHAR(255) NOT NULL,                    -- Ex: 'https://cointelegraph.com/rss'
    sentiment_label VARCHAR(20) NOT NULL DEFAULT 'NEUTRAL', -- 'BULLISH', 'BEARISH', 'NEUTRAL'
    sentiment_score NUMERIC(5, 2) NOT NULL DEFAULT 0.0,    -- Score de -1.0 à +1.0
    published_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour accélérer les requêtes de recherche d'actualités récentes
CREATE INDEX IF NOT EXISTS idx_news_published_at ON public.news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON public.news(sentiment_label);

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.news ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.news IS 'Articles d actualités crypto et scores de sentiment associés';