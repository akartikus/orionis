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
```

### Où trouver chaque valeur

| Variable | Source |
|---|---|
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase Dashboard → Project Settings → API |
| `BITVAVO_API_KEY` / `BITVAVO_API_SECRET` | Bitvavo → Account → API Keys |
| `DISCORD_BOT_TOKEN` | Discord Developer Portal → votre application → Bot → Token |
| `DISCORD_GUILD_ID` | Discord (mode développeur activé) → clic droit sur le serveur → « Copier l'identifiant » |

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
    │       └── portfolio.py      # Commande /portfolio (lecture Supabase)
    ├── collectors/
    │   ├── portfolio_collector.py  # Sync Bitvavo → table 'portfolio'
    │   ├── market_collector.py     # Snapshots de marché + indicateurs (RSI, MACD, EMA)
    │   └── news_collector.py      # Collecte RSS + analyse de sentiment
    ├── database/
    │   ├── client.py              # Client Supabase partagé (singleton)
    │   └── models/               # Modèles Pydantic (portfolio, orders, news, etc.)
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
| `POST` | `/api/v1/sync/portfolio` | Sync manuelle du portefeuille depuis Bitvavo |
| `POST` | `/api/v1/sync/market` | Sync manuelle des données de marché |
| `POST` | `/api/v1/sync/news` | Sync manuelle des actualités crypto |

Jobs planifiés (APScheduler) :
- **Portfolio** : toutes les 5 minutes
- **Market** (BTC, ETH, SOL) : toutes les minutes
- **News** : toutes les 15 minutes

### Bot Discord

```bash
.venv/bin/python src/scripts/run_bot.py
```

Commandes slash disponibles dans Discord :

| Commande | Description |
|---|---|
| `/portfolio` | Affiche le portefeuille global + positions Orionis (boutons de bascule) |

> **Données affichées** : `/portfolio` lit les données **déjà synchronisées** dans Supabase. Pour rafraîchir, utilisez l'endpoint `POST /api/v1/sync/portfolio` ou attendez le job planifié.

### Test des collectors (sans API ni bot)

```bash
.venv/bin/python src/main.py          # Test tous les collectors en séquence
.venv/bin/python src/scripts/test_market_sync.py   # Test du MarketCollector uniquement
```

## Notes

- **Discord** : le bot doit être invité dans le serveur avec les scopes `bot` **et** `applications.commands` pour que les commandes slash fonctionnent.
- **Discord** : activer le mode développeur (Paramètres → Avancé) pour copier l'identifiant du serveur (`DISCORD_GUILD_ID`).
- **Supabase** : les tables `portfolio`, `bot_managed_assets`, `market_snapshots`, `news` doivent exister avant le premier lancement.