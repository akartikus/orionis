# ÉTAPE 04 — Data Collection Layer complet

> **Priorité** : 🟠 Élevée
> **Prérequis** : Étapes 01 + 03 (LLM pour résumé news)
> **Objectif** : Compléter la couche de collecte : Macro Collector (FRED),
> On-chain Collector, intégration CoinGecko, et amélioration du News Collector
> avec résumé IA.

---

## Contexte

Les collectors existants (Market, Portfolio, News) couvrent Bitvavo + RSS.
La vision prévoit des sources supplémentaires :

| Source | Données | Statut |
|---|---|---|
| Bitvavo | Prix, volumes, OHLC, soldes | ✅ Existant |
| CoinGecko | Market cap, rankings, données supplémentaires | ❌ Manquant |
| News RSS | Articles + sentiment | ⚠️ Rule-based |
| Macro (FRED) | Taux, inflation, chômage, DXY | ❌ Manquant |
| On-chain | Active addresses, whale flows | ❌ Manquant |

---

## 4.1 — CoinGecko Integration

### Objectif

Enrichir les `market_snapshots` avec le `market_cap` (actuellement `None`)
et des métriques supplémentaires (rank, ATH, ATL, supply).

### Implémentation — `src/collectors/coingecko_collector.py`

- API : `https://api.coingecko.com/api/v3` (gratuit, pas de clé requise,
  rate limit ~10-30 calls/min)
- Endpoints utilisés :
  - `/coins/{id}` → market_cap, ath, atl, circulating_supply
  - `/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=eur`
- Mapping asset ticker → CoinGecko coin ID : `BTC → bitcoin`, `ETH → ethereum`
- Modifier `MarketCollector.fetch_and_store_snapshot()` pour appeler
  CoinGecko après Bitvavo et peupler `market_cap`

### Alternative

Si la clé API CoinGecko Pro est disponible (`COINGECKO_API_KEY`), l'ajouter
pour des rate limits plus élevés.

---

## 4.2 — Macro Collector (FRED API)

### Objectif

Récupérer les indicateurs macroéconomiques et les stocker dans
`macro_indicators` (table créée à l'étape 01).

### Source : FRED (Federal Reserve Economic Data)

- API : `https://api.stlouisfed.org/fred/series/observations`
- Clé API gratuite : `FRED_API_KEY` (à ajouter dans `.env`)
- Séries à récupérer :

| Indicateur | Series ID | Unité |
|---|---|---|
| Taux directeur Fed | `FEDFUNDS` | % |
| Inflation CPI | `CPIAUCSL` | % |
| Chômage | `UNRATE` | % |
| Dollar Index (DXY) | `DTWEXBGS` | index |
| S&P 500 | `SP500` | index |

### Implémentation — `src/collectors/macro_collector.py`

```python
class MacroCollector:
    async def fetch_and_store_indicators(self) -> int:
        # Pour chaque série FRED configurée :
        #   1. GET /fred/series/observations?series_id=...&limit=1&sort_order=desc
        #   2. Insérer dans macro_indicators
```

- Fréquence : quotidienne (job APScheduler dédié)

---

## 4.3 — On-chain Collector

### Objectif

Récupérer des métriques on-chain et les stocker dans `onchain_data`.

### Sources possibles

1. **API publique Blockchain.com** (gratuit, limité BTC/ETH)
2. **Glassnode** (payant) — `GLASSNODE_API_KEY`
3. **CryptoQuant** (payant) — `CRYPTOQUANT_API_KEY`

### Implémentation v1 (API publique) — `src/collectors/onchain_collector.py`

Métriques v1 :
- BTC : `hash_rate`, `tx_count_24h`, `difficulty`
- ETH : `gas_price_avg`, `tx_count_24h`

- Fréquence : toutes les 6h (on-chain change lentement)
- Évolution : intégrer Glassnode/CryptoQuant si clé disponible

---

## 4.4 — News Collector : résumé IA

### Objectif

Remplacer le sentiment rule-based par un **résumé IA** + sentiment via le
LLM Provider (étape 03).

### Amélioration — modifier `src/collectors/news_collector.py`

1. Conserver la collecte RSS (feedparser) — inchangée
2. Pour chaque article, envoyer au LLM :
   - System : « Résume cet article crypto en 2 phrases et donne un sentiment
     (BULLISH/BEARISH/NEUTRAL) avec un score -1.0 à +1.0. Réponds en JSON. »
   - User : `{title} {summary}`
   - response_format: JSON mode
3. Parser la réponse JSON : `{ "summary", "sentiment_label", "sentiment_score" }`
4. Stocker le résumé IA dans `news.summary`

### Optimisation

- Batch : regrouper 5 articles par prompt LLM (économie de tokens)
- Fallback : si LLM indisponible, fallback sur sentiment rule-based
- Rate limit : max 30 articles par cycle

---

## Plan d'action

| # | Tâche | Fichier |
|---|---|---|
| 4.1 | CoinGecko + intégration MarketCollector | `coingecko_collector.py`, `market_collector.py` |
| 4.2 | Macro Collector (FRED) | `macro_collector.py` |
| 4.3 | On-chain Collector | `onchain_collector.py` |
| 4.4 | News Collector IA | `news_collector.py` (modifier) |
| 4.5 | Config + scheduler | `config.py`, `main.py` |
| 4.6 | Tests | `scripts/test_collectors.py` |

---

## Configuration à ajouter (`config.py`)

```python
COINGECKO_API_KEY: str | None = None
COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"
FRED_API_KEY: str | None = None
FRED_BASE_URL: str = "https://api.stlouisfed.org/fred"
ONCHAIN_PROVIDER: str = "blockchain"
GLASSNODE_API_KEY: str | None = None
SCHEDULER_MACRO_INTERVAL_MINUTES: int = 1440
SCHEDULER_ONCHAIN_INTERVAL_MINUTES: int = 360
SCHEDULER_COINGECKO_INTERVAL_MINUTES: int = 30
```

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/collectors/coingecko_collector.py` | **Créer** |
| `src/collectors/macro_collector.py` | **Créer** |
| `src/collectors/onchain_collector.py` | **Créer** |
| `src/collectors/market_collector.py` | **Modifier** |
| `src/collectors/news_collector.py` | **Modifier** |
| `src/config.py` | **Modifier** |
| `src/main.py` | **Modifier** |
| `src/scripts/test_collectors.py` | **Créer** |

---

## Critères de validation

- [ ] `market_snapshots` contient un `market_cap` non-null pour BTC/ETH/SOL
- [ ] `macro_indicators` contient au moins 5 indicateurs après un sync
- [ ] `onchain_data` contient des métriques BTC après un sync
- [ ] `news.summary` contient un résumé IA (pas le brut RSS)
- [ ] `news.sentiment_label` provient du LLM (fallback rule-based OK)
- [ ] Les jobs scheduler tournent aux intervalles configurés
- [ ] `test_collectors.py` valide chaque collector
- [ ] `pyright` passe sans erreur

---

## Notes

- CoinGecko free API : rate limit strict → cache TTL 5 min
- FRED : données mensuelles/journalières → sync quotidien suffit
- On-chain : commencer simple, enrichir avec Glassnode si budget
- Paralléliser les appels LLM news avec `asyncio.gather` (max 5 concurrent)

