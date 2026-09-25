# Orionis — Feuille de route par étapes

Ce dossier contient le plan détaillé de chaque étape de développement du projet
Orionis (agent IA autonome de gestion d'un portefeuille crypto).

Chaque fichier `.md` est **auto-suffisant** : on peut le lire seul pour
comprendre le contexte, les objectifs, les fichiers à créer/modifier et les
critères de validation de l'étape.

---

## Vision rappelée

Orionis est un système complet en 7 couches :

1. **Interface utilisateur** — Bot Discord
2. **Orionis Core** — Orchestrateur (FastAPI + async)
3. **Data Collection Layer** — Market, Portfolio, News, Macro, On-chain
4. **Base de données & mémoire** — Supabase PostgreSQL
5. **Analyse IA** — Analyste marché, fondamental, risque, synthèse décisionnelle
6. **Portfolio Manager** — Limites de risque, allocation, exposition
7. **Execution Engine** — Bitvavo API (ordres validés uniquement)

---

## État actuel du projet (référence)

| Couche | Statut | Fichiers existants |
|---|---|---|
| Discord Bot | ✅ Basique | `src/bot/` (/portfolio, /trade) |
| FastAPI + Scheduler | ✅ Basique | `src/main.py` |
| Portfolio Collector | ✅ Fonctionnel | `src/collectors/portfolio_collector.py` |
| Market Collector | ✅ Fonctionnel | `src/collectors/market_collector.py` |
| News Collector | ⚠️ Rule-based | `src/collectors/news_collector.py` |
| Macro Collector | ❌ Manquant | — |
| On-chain Collector | ❌ Manquant | — |
| CoinGecko | ❌ Manquant | — |
| Orionis Core | ❌ Manquant | — |
| LLM Provider | ❌ Manquant | — |
| AI Analysis Layer | ❌ Manquant | `src/strategy/engine.py` (vide) |
| Portfolio Manager | ❌ Manquant | — |
| Execution Engine | ⚠️ Basique | `src/execution/order_executor.py` |
| Scheduler/Events | ⚠️ Intervalles | `src/main.py` (APScheduler) |
| Supabase DB | ✅ 8 tables | `src/database/schema/00*.sql` |

---

## Liste des étapes

| # | Fichier | Titre | Priorité |
|---|---|---|---|
| 00 | `etape-00-audit-corrections.md` | Audit & corrections de l'existant | 🔴 Critique |
| 01 | `etape-01-database-migrations.md` | Migrations DB complémentaires | 🔴 Critique |
| 02 | `etape-02-jarvis-core.md` | Jarvis Core — Orchestrateur central | 🔴 Critique |
| 03 | `etape-03-llm-provider.md` | LLM Provider — Abstraction IA interchangeable | 🔴 Critique |
| 04 | `etape-04-data-collection.md` | Data Collection Layer complet | 🟠 Élevée |
| 05 | `etape-05-ai-analysis.md` | AI Analysis Layer (3 analystes + synthèse) | 🔴 Critique |
| 06 | `etape-06-portfolio-manager.md` | Portfolio Manager (risk / allocation) | 🟠 Élevée |
| 07 | `etape-07-execution-enhancements.md` | Execution Engine — sécurités & lien décision | 🟠 Élevée |
| 08 | `etape-08-scheduler-events.md` | Scheduler & événements (workflow quotidien + alertes) | 🟡 Moyenne |
| 09 | `etape-09-discord-enhancements.md` | Discord Bot — nouvelles commandes & alertes | 🟡 Moyenne |
| 10 | `etape-10-testing-deployment.md` | Tests, CI & déploiement | 🟢 Finale |

---

## Ordre recommandé d'exécution

```
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10
```

Les étapes 00 à 03 sont des **fondations** : elles doivent être terminées
avant d'attaquer la couche IA (05). L'étape 04 peut être menée en parallèle
de 02/03 car les collectors sont indépendants de l'orchestrateur.

---

## Conventions de code

- **Python 3.12+**, async-first (`asyncio`, `httpx`, `ccxt.async_support`)
- **Pydantic v2** pour tous les modèles
- **Supabase async client** (singleton `db` dans `src/database/client.py`)
- **Logging** : `logging.getLogger(__name__)` partout
- **Config** : `src/config.py` (Pydantic Settings, `.env`)
- **Pas de sync blocking** dans l'event loop
- Typage statique complet (`pyright` configuré dans `pyproject.toml`)
