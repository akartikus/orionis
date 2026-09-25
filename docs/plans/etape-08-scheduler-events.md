# ÉTAPE 08 — Scheduler & Événements (workflow quotidien + alertes)

> **Priorité** : 🟡 Moyenne
> **Prérequis** : Étapes 02 (Orionis Core) + 05 (AI) + 07 (Execution)
> **Objectif** : Mettre en place le scheduler event-driven : workflow
> quotidien à 08h00, déclencheurs d'alertes (BTC -8%), et notifications.

---

## Contexte

Actuellement, APScheduler lance 3 jobs en intervalle fixe (portfolio 5min,
market 1min, news 15min). La vision prévoit en plus :

- un **workflow quotidien** (08h00) : collecte → analyse IA → décisions →
  rapport Discord ;
- des **événements** : BTC -8% → analyse urgente ;
- des **rapports** automatiques envoyés sur Discord ;
- une **évaluation a posteriori** des décisions (performance_score).

---

## 8.1 — Workflow quotidien (08h00)

### Séquence

```
08h00 → DAILY_TICK (EventBus)
   |
   ├── Step 1: Data sync complet (market, portfolio, news, macro, onchain)
   ├── Step 2: AI Analysis pour chaque asset (allowed_assets)
   ├── Step 3: Portfolio Manager validation de chaque décision
   ├── Step 4: Execution (si AUTO_EXECUTE_DECISIONS=True)
   ├── Step 5: Génération rapport quotidien
   └── Step 6: Envoi rapport sur Discord (channel dédié)
```

### Implémentation

Modifier `src/core/workflows/daily_analysis.py` (stub étape 02) pour
implémenter la séquence complète.

Job APScheduler **cron** (pas interval) :

```python
scheduler.add_job(
    orionis_core.run_daily_analysis,
    "cron",
    hour=settings.DAILY_ANALYSIS_HOUR,
    minute=settings.DAILY_ANALYSIS_MINUTE,
    id="daily_analysis",
)
```

---

## 8.2 — Détection d'événements prix

Après chaque `market_sync` (1 min), comparer prix actuel au précédent.
Si variation ≥ seuil → émettre événement.

```python
async def check_price_alert(asset, current_price, previous_price):
    change_pct = ((current_price - previous_price) / previous_price) * 100
    if change_pct <= -settings.PRICE_DROP_THRESHOLD_PCT:
        await event_bus.publish("PRICE_DROP", {...})
    elif change_pct >= settings.PRICE_SURGE_THRESHOLD_PCT:
        await event_bus.publish("PRICE_SURGE", {...})
```

Handler `PRICE_DROP` → `orionis_core.run_urgent_analysis(asset, reason)`.
Chaque alerte est insérée dans `alerts`.

---

## 8.3 — Détection news critique

Après `news_sync`, si article `sentiment_label='BEARISH'` et
`sentiment_score <= -0.7` → émettre `NEWS_CRITICAL`.

Handler → `orionis_core.run_urgent_analysis(related_asset, reason)`.

> Mapping article → asset : détection de mots-clés (BTC, ETH, SOL) ou
> tagging LLM.

---

## 8.4 — Rapport quotidien

`src/core/reports/daily_report.py` :

```python
class DailyReportGenerator:
    async def generate(self, decisions, portfolio_state) -> ReportData:
        # Compile : résumé portefeuille, décisions, alertes,
        # indicateurs macro, performance décisions passées
```

Envoi via le bot Discord sur un channel dédié (`DISCORD_REPORT_CHANNEL_ID`).
Format : Embed Discord riche avec sections.

---

## 8.5 — Évaluation a posteriori

Pour chaque décision exécutée il y a > 24h sans `performance_score` :

1. Récupérer prix au moment de la décision
2. Récupérer prix actuel
3. Calculer performance : `(actuel - decision) / decision * 100`
4. Mettre à jour `decisions.performance_score`

```python
scheduler.add_job(
    evaluate_past_decisions, "cron", hour=9, id="decision_evaluation",
)
```

---

## Plan d'action

| # | Tâche |
|---|---|
| 8.1 | Implémenter `daily_analysis.py` complet |
| 8.2 | Détection prix alerts dans `data_sync.py` |
| 8.3 | Détection news critiques |
| 8.4 | `src/core/reports/daily_report.py` |
| 8.5 | `src/core/reports/evaluation.py` |
| 8.6 | Jobs cron dans `main.py` |
| 8.7 | Envoi rapport Discord (`src/bot/notifications.py`) |
| 8.8 | Config (channel ID, seuils) |

---

## Configuration à ajouter (`config.py`)

```python
DISCORD_REPORT_CHANNEL_ID: str | None = None
DAILY_ANALYSIS_HOUR: int = 8
DAILY_ANALYSIS_MINUTE: int = 0
EVALUATION_HOUR: int = 9
PRICE_DROP_THRESHOLD_PCT: float = 8.0
PRICE_SURGE_THRESHOLD_PCT: float = 8.0
NEWS_CRITICAL_THRESHOLD: float = -0.7
```

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/core/workflows/daily_analysis.py` | **Modifier** |
| `src/core/workflows/data_sync.py` | **Modifier** |
| `src/core/reports/__init__.py` | **Créer** |
| `src/core/reports/daily_report.py` | **Créer** |
| `src/core/reports/evaluation.py` | **Créer** |
| `src/main.py` | **Modifier** |
| `src/config.py` | **Modifier** |
| `src/bot/notifications.py` | **Créer** |

---

## Critères de validation

- [ ] Le job quotidien se déclenche à 08h00
- [ ] Le workflow produit des décisions + rapport
- [ ] Une chute ≥ 8% déclenche `PRICE_DROP` → analyse urgente
- [ ] Une news BEARISH (≤ -0.7) déclenche `NEWS_CRITICAL`
- [ ] Les alertes sont stockées dans `alerts`
- [ ] Le rapport quotidien est généré (structuré)
- [ ] L'évaluation met à jour `performance_score`
- [ ] `pyright` passe sans erreur

---

## Notes

- En dev, déclencher manuellement via `POST /api/v1/orionis/daily-analysis`
- Le rapport Discord doit être concis (embed < 6000 chars)
- L'évaluation ne s'applique qu'aux décisions `executed=true`

