# ORIONIS

Bot Discord et API FastAPI pour la gestion autonome d'un portefeuille crypto sur **Bitvavo**, avec synchronisation des données vers **Supabase**.

## Prérequis

- **Python 3.12+**
- Un compte **Supabase** (base de données)
- Un compte **Bitvavo** avec clés API
- Une application **Discord** (Developer Portal)

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-repo> && cd orionis

# 2. Créer un environnement virtuel
python3 -m venv .venv

# 3. Activer le venv
source .venv/bin/activate

# 4. Installer les dépendances
pip install -r src/requirements.txt
```

## Configuration

Créer un fichier `.env` à la racine du projet :

```env
# App
ENVIRONMENT=development
LOG_LEVEL=INFO

# API FastAPI (interrogée par le bot Discord ; par défaut http://127.0.0.1:8000)
FASTAPI_BASE_URL=http://127.0.0.1:8000

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=votre_cle_supabase

# Bitvavo
BITVAVO_API_KEY=votre_cle_bitvavo
BITVAVO_API_SECRET=votre_secret_bitvavo

# Discord
DISCORD_BOT_TOKEN=votre_token_bot_discord
DISCORD_GUILD_ID=identifiant_du_serveur_discord

# LLM (optionnel)
OPENROUTER_API=votre_cle_openrouter

# Scheduler — intervalles en minutes (optionnel, valeurs par défaut indiquées)
SCHEDULER_PORTFOLIO_INTERVAL_MINUTES=5
SCHEDULER_MARKET_INTERVAL_MINUTES=1
SCHEDULER_NEWS_INTERVAL_MINUTES=15

# Assets surveillés par le market sync (optionnel, comma-separated)
MARKET_SYNC_ASSETS=BTC,ETH,SOL
```

### Où trouver chaque valeur

| Variable | Source |
|---|---|
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase Dashboard → Project Settings → API |
| `BITVAVO_API_KEY` / `BITVAVO_API_SECRET` | Bitvavo → Account → API Keys |
| `DISCORD_BOT_TOKEN` | Discord Developer Portal → votre application → Bot → Token |
| `DISCORD_GUILD_ID` | Discord (mode développeur activé) → clic droit sur le serveur → « Copier l'identifiant » |

## Base de données (Supabase)

Le schéma SQL est versionné dans `src/database/schema/`. Avant le premier lancement, exécute les migrations **dans l'ordre** dans l'éditeur SQL de Supabase (Dashboard → SQL Editor) :

| Fichier | Tables créées |
|---|---|
| `001_initial_orionis_schema.sql` | `portfolio`, `bot_managed_assets`, `transactions`, `orders`, `decisions`, `market_snapshots` |
| `002_add_news_table.sql` | `news` |
| `003_add_transactions_table.sql` | `transactions_log` (journal des ordres exécutés par le bot) |
| `004_add_macro_data_table.sql` | `macro_indicators` (indicateurs macroéconomiques horodatés) |
| `005_add_onchain_data_table.sql` | `onchain_data` (métriques on-chain par actif) |
| `006_add_strategy_config_table.sql` | `strategy_config` (paramètres de stratégie + ligne initiale conservative) |
| `007_add_alerts_table.sql` | `alerts` (événements détectés : prix, news, seuils) |
| `008_add_ai_reports_table.sql` | `ai_reports` (rapports structurés des analystes IA) |
| `009_add_orchestration_logs_table.sql` | `orchestration_logs` (trace des workflows exécutés) |

> Les migrations activent **Row Level Security (RLS)** sur toutes les tables. La `SUPABASE_KEY` utilisée côté serveur doit avoir les droits suffisants (clé `service_role` pour l'écriture).

## Structure du projet

```
orionis/
├── .env                          # Variables d'environnement (non versionné)
├── pyproject.toml                # Config Pyright + setuptools
├── README.md
└── src/
    ├── config.py                 # Chargement des variables .env (Pydantic Settings)
    ├── main.py                   # API FastAPI + scheduler (APScheduler)
    ├── bot/
    │   ├── client.py             # Factory du bot Discord (create_bot)
    │   └── commands/
    │       ├── portfolio.py      # Commande /portfolio (interroge l'API FastAPI)
    │       └── trade.py          # Commande /trade (ordre au marché via l'API FastAPI)
    ├── collectors/
    │   ├── portfolio_collector.py  # Sync Bitvavo → table 'portfolio'
    │   ├── market_collector.py     # Snapshots de marché + indicateurs (RSI, MACD, EMA)
    │   └── news_collector.py      # Collecte RSS + analyse de sentiment
    ├── execution/
    │   └── order_executor.py     # Exécution d'ordres live Bitvavo (CCXT) + log Supabase
    ├── database/
    │   ├── client.py             # Client Supabase partagé (singleton)
    │   ├── models/               # Modèles Pydantic (portfolio, orders, news, macro, alerts, etc.)
    │   └── schema/               # Migrations SQL (PostgreSQL/Supabase)
    │       ├── 001_initial_orionis_schema.sql
    │       ├── 002_add_news_table.sql
    │       ├── 003_add_transactions_table.sql
    │       ├── 004_add_macro_data_table.sql
    │       ├── 005_add_onchain_data_table.sql
    │       ├── 006_add_strategy_config_table.sql
    │       ├── 007_add_alerts_table.sql
    │       ├── 008_add_ai_reports_table.sql
    │       └── 009_add_orchestration_logs_table.sql
    └── scripts/
        ├── run_bot.py            # Point d'entrée du bot Discord
        └── test_market_sync.py   # Test du MarketCollector
```

## Lancement

> ⚠️ **Toujours utiliser le venv**. Ne lancez pas `uvicorn` ou `python` système — les packages sont installés dans `.venv/`.

### API FastAPI (serveur + scheduler)

```bash
.venv/bin/uvicorn src.main:app --reload --port 8000
```

Endpoints disponibles :

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/health` | Vérifie que l'API et le scheduler sont en ligne |
| `GET` | `/api/v1/portfolio?managed_only=false` | Liste le portefeuille global Supabase |
| `POST` | `/api/v1/trade` | Exécute un ordre au marché sur Bitvavo (origin='ORIONIS') |
| `POST` | `/api/v1/sync/portfolio` | Sync manuelle du portefeuille depuis Bitvavo |
| `POST` | `/api/v1/sync/market` | Sync manuelle des données de marché |
| `POST` | `/api/v1/sync/news` | Sync manuelle des actualités crypto |

Jobs planifiés (APScheduler) :
- **Portfolio** : toutes les 5 minutes
- **Market** (BTC, ETH, SOL) : toutes les minutes
- **News** : toutes les 15 minutes

### Bot Discord

> ⚠️ **Prérequis** : le serveur FastAPI doit être démarré **avant** le bot. La commande `/portfolio` interroge l'API (`GET /api/v1/portfolio`) via `FASTAPI_BASE_URL` et ne lit plus Supabase directement.

```bash
.venv/bin/python src/scripts/run_bot.py
```

Commandes slash disponibles dans Discord :

| Commande | Description |
|---|---|
| `/portfolio` | Affiche le portefeuille global + positions Orionis (boutons de bascule) |
| `/trade` | Passe un ordre au marché sur Bitvavo (achat/vente, avec confirmation boutons) |

> **Données affichées** : `/portfolio` interroge l'API FastAPI, qui renvoie les données **déjà synchronisées** dans Supabase. Pour rafraîchir, utilisez l'endpoint `POST /api/v1/sync/portfolio` ou attendez le job planifié.

### Test des collectors (sans API ni bot)

```bash
.venv/bin/python src/main.py          # Test tous les collectors en séquence
.venv/bin/python src/scripts/test_market_sync.py   # Test du MarketCollector uniquement
```

## Notes

- **Discord** : le bot doit être invité dans le serveur avec les scopes `bot` **et** `applications.commands` pour que les commandes slash fonctionnent.
- **Discord** : activer le mode développeur (Paramètres → Avancé) pour copier l'identifiant du serveur (`DISCORD_GUILD_ID`).
- **Supabase** : le schéma doit être initialisé avant le premier lancement — exécute les migrations SQL de `src/database/schema/` (voir [Base de données (Supabase)](#base-de-données-supabase)). Tables concernées : `portfolio`, `bot_managed_assets`, `transactions`, `orders`, `decisions`, `market_snapshots`, `news`, `transactions_log`, `macro_indicators`, `onchain_data`, `strategy_config`, `alerts`, `ai_reports`, `orchestration_logs`.