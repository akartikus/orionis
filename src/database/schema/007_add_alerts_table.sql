-- ====================================================================
-- MIGRATION 007 : TABLE ALERTS (Événements détectés)
-- ====================================================================
-- Utilité : Stocke les alertes détectées par les collectors ou Orionis Core
-- (chute de prix, surge, news critique, franchissement de seuil, manuel).
-- Le champ 'triggered' indique si Orionis Core a traité l'alerte.

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

-- Index pour accélérer les requêtes d'alertes non traitées (du plus récent au plus ancien)
CREATE INDEX IF NOT EXISTS idx_alerts_triggered_created
    ON public.alerts(triggered, created_at DESC);

-- Sécurité Row Level Security (RLS)
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.alerts IS 'Alertes et événements détectés (prix, news, seuils)';
