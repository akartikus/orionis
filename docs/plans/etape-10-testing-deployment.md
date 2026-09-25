# ÉTAPE 10 — Tests, CI & Déploiement

> **Priorité** : 🟢 Finale
> **Prérequis** : Toutes les étapes précédentes
> **Objectif** : Suite de tests, CI GitHub Actions, et fichiers de
> déploiement pour Oracle Cloud.

---

## Contexte

Le projet n'a actuellement qu'un script de test manuel (`test_market_sync.py`).
Il manque : une suite de tests, une CI, et les fichiers de déploiement
mentionnés dans `.doc/deployment-oracle-cloud.md` mais non créés.

---

## 10.1 — Suite de tests

### Framework

- **pytest** + **pytest-asyncio** + **pytest-cov**

### Structure

```
tests/
├── conftest.py              # fixtures (mock Supabase, LLM, CCXT)
├── unit/
│   ├── test_config.py
│   ├── test_indicators.py   # RSI, MACD, EMA
│   ├── test_sentiment.py
│   ├── test_validators.py   # Portfolio Manager
│   ├── test_safety.py
│   └── test_event_bus.py
├── integration/
│   ├── test_collectors.py
│   ├── test_llm_provider.py
│   ├── test_analysis.py
│   ├── test_execution.py
│   └── test_workflows.py
└── e2e/
    └── test_api.py          # FastAPI TestClient
```

### Ajouter dans `requirements.txt`

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=4.0.0
```

### Fixtures clés (`conftest.py`)

```python
@pytest.fixture
async def mock_supabase(): ...   # Mock AsyncClient
@pytest.fixture
def mock_ccxt(): ...             # Mock ccxt.bitvavo
@pytest.fixture
def mock_llm(): ...              # Mock LLMProvider
@pytest.fixture
def sample_decision(): ...
@pytest.fixture
def sample_strategy_config(): ...
```

### Couverture cible

| Module | Couverture min |
|---|---|
| `config.py` | 90% |
| `collectors/` | 70% |
| `ai/` | 80% |
| `portfolio/` | 85% |
| `execution/` | 85% |
| `core/` | 75% |

---

## 10.2 — CI GitHub Actions

`.github/workflows/ci.yml` :

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r src/requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov ruff pyright
      - run: ruff check src/
      - run: pyright src/
      - run: pytest tests/ --cov=src --cov-report=term-missing
```

### Quality gates

- `ruff` : 0 erreur
- `pyright` : 0 erreur
- `pytest` : tous passent
- Couverture ≥ 75%

---

## 10.3 — Fichiers de déploiement

Créer le dossier `deploy/` :

```
deploy/
├── orionis-api.service       # systemd FastAPI
├── orionis-bot.service       # systemd Discord bot
├── nginx.conf                # reverse proxy
├── .env.example              # template (sans secrets)
├── setup.sh                  # installation (optionnel)
└── healthcheck.sh            # curl + alerte
```

### `.env.example`

Template complet avec toutes les variables des étapes 00 à 09 :

```env
ENVIRONMENT=production
LOG_LEVEL=INFO
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=sb_secret_xxx
BITVAVO_API_KEY=xxx
BITVAVO_API_SECRET=xxx
DISCORD_BOT_TOKEN=xxx
DISCORD_GUILD_ID=xxx
DISCORD_REPORT_CHANNEL_ID=xxx
DISCORD_ALERT_CHANNEL_ID=xxx
LLM_PROVIDER=openrouter
LLM_DEFAULT_MODEL=zai-org/glm-5
OPENROUTER_API=sk-or-v1-xxx
FRED_API_KEY=xxx
AUTO_EXECUTE_DECISIONS=false
DAILY_ANALYSIS_HOUR=8
PRICE_DROP_THRESHOLD_PCT=8.0
```

### `orionis-api.service`

```ini
[Unit]
Description=Orionis FastAPI + Scheduler
After=network.target
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/orionis
ExecStart=/opt/orionis/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/opt/orionis/.env
[Install]
WantedBy=multi-user.target
```

### `orionis-bot.service`

```ini
[Unit]
Description=Orionis Discord Bot
After=orionis-api.service
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/orionis
ExecStart=/opt/orionis/.venv/bin/python src/scripts/run_bot.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/orionis/.env
[Install]
WantedBy=multi-user.target
```

---

## 10.4 — Health enrichi

```python
@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "scheduler_running": scheduler.running,
        "orionis_core_status": orionis_core.status,
        "db_connected": db._client is not None,
        "llm_provider": settings.LLM_PROVIDER,
        "last_daily_analysis": last_run_timestamp,
    }
```

---

## 10.5 — Documentation finale

Mettre à jour `README.md` : nouvelles commandes Discord, endpoints API,
variables `.env`, schéma DB complet, instructions de test, lien vers
`docs/plans/`.

---

## Plan d'action

| # | Tâche |
|---|---|
| 10.1 | Installer pytest + pytest-asyncio + pytest-cov |
| 10.2 | `tests/conftest.py` (fixtures) |
| 10.3 | Tests unitaires |
| 10.4 | Tests d'intégration |
| 10.5 | Tests E2E API |
| 10.6 | CI GitHub Actions |
| 10.7 | Fichiers `deploy/` |
| 10.8 | Enrichir `/health` |
| 10.9 | Mettre à jour `README.md` |
| 10.10 | Configurer `pyproject.toml` (pytest, ruff) |

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `tests/` (dossier complet) | **Créer** |
| `.github/workflows/ci.yml` | **Créer** |
| `deploy/orionis-api.service` | **Créer** |
| `deploy/orionis-bot.service` | **Créer** |
| `deploy/nginx.conf` | **Créer** |
| `deploy/.env.example` | **Créer** |
| `deploy/setup.sh` | **Créer** (optionnel) |
| `deploy/healthcheck.sh` | **Créer** |
| `src/main.py` | **Modifier** (/health) |
| `src/requirements.txt` | **Modifier** |
| `pyproject.toml` | **Modifier** |
| `README.md` | **Modifier** |

---

## Critères de validation

- [ ] `pytest tests/` passe avec 0 échec
- [ ] Couverture ≥ 75%
- [ ] `ruff check src/` : 0 erreur
- [ ] `pyright src/` : 0 erreur
- [ ] La CI GitHub Actions passe
- [ ] `deploy/.env.example` contient toutes les variables
- [ ] Les fichiers systemd sont valides
- [ ] `/health` retourne un statut complet
- [ ] `README.md` est à jour et complet

---

## Notes

- Les tests ne doivent **jamais** appeler de vraies API — tout mocké
- `.env.example` ne doit contenir **aucun** secret réel
- Les fichiers `deploy/` doivent être versionnés (contrairement à `.doc/`)
- Marqueur `@pytest.mark.integration` pour tests nécessitant une DB de test

