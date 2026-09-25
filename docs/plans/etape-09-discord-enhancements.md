# ÉTAPE 09 — Discord Bot (nouvelles commandes & alertes)

> **Priorité** : 🟡 Moyenne
> **Prérequis** : Étapes 05 (AI) + 06 (Portfolio) + 07 (Execution) + 08 (Scheduler)
> **Objectif** : Enrichir le bot Discord avec les commandes prévues par la
> vision et un système de notifications/alertes.

---

## Contexte

Le bot actuel propose `/portfolio` et `/trade`. La vision prévoit :

| Commande | Description | Statut |
|---|---|---|
| `/portfolio` | État du portefeuille | ✅ Existant |
| `/trade` | Ordre manuel | ✅ Existant |
| `/analyse BTC` | Demander une analyse IA | ❌ Manquant |
| `/orders` | Consulter les ordres | ❌ Manquant |
| `/rapport` | Rapport quotidien à la demande | ❌ Manquant |
| `/pourquoi ETH ?` | Explication d'une décision | ❌ Manquant |
| `/decisions` | Historique des décisions | ❌ Manquant |
| `/alerts` | Alertes récentes | ❌ Manquant |
| `/config` | Voir/modifier strategy_config | ❌ Manquant |
| Notifications | Alertes push (prix, news, rapport) | ❌ Manquant |

---

## 9.1 — Commande `/analyse [asset]`

- Déclenche `AnalysisEngine.analyze_asset(asset)` via `POST /api/v1/analyse`
- Embed : décision, confiance, raisonnement, rapports des 3 analystes
- Bouton « Exécuter » si BUY/SELL (avec confirmation)

### Fichier : `src/bot/commands/analyse.py`

---

## 9.2 — Commande `/orders [status] [limit]`

- Interroge `GET /api/v1/orders`
- Affiche les ordres récents (PENDING, FILLED, CANCELED)

### Fichier : `src/bot/commands/orders.py`

---

## 9.3 — Commande `/rapport`

- Déclenche la génération du rapport quotidien à la demande
- Affiche le rapport (embed structuré)

### Fichier : `src/bot/commands/report.py`

---

## 9.4 — Commande `/pourquoi [asset]`

- Récupère la dernière décision pour cet asset depuis `decisions`
- Affiche le raisonnement (`reason`) + `raw_analysis` (3 rapports)

### Fichier : `src/bot/commands/why.py`

---

## 9.5 — Commande `/decisions [asset] [limit]`

- Liste les décisions récentes depuis `decisions`
- Affiche : date, asset, action, confiance, exécutée?, performance

### Fichier : `src/bot/commands/decisions.py`

---

## 9.6 — Commande `/alerts [severity]`

- Liste les alertes récentes depuis `alerts`
- Filtre par severity

### Fichier : `src/bot/commands/alerts.py`

---

## 9.7 — Commande `/config`

```
/config              → affiche la config active
/config edit ...     → modifie (admin only)
```

- Affiche `strategy_config` active
- Permet de modifier certains paramètres (limites, seuils)
- **Restreint aux administrateurs** Discord

### Fichier : `src/bot/commands/config_cmd.py`

---

## 9.8 — Notifications automatiques

`src/bot/notifications.py` :

```python
class DiscordNotifier:
    async def send_daily_report(self, report: ReportData): ...
    async def send_alert(self, alert: Alert): ...
    async def send_decision_notification(self, decision: Decision): ...
    async def send_execution_result(self, result: ExecutionResult): ...
```

- Channel `DISCORD_REPORT_CHANNEL_ID` pour rapports
- Channel `DISCORD_ALERT_CHANNEL_ID` pour alertes
- Les CRITICAL peuvent mentionner un rôle (`DISCORD_ADMIN_ROLE_ID`)

---

## 9.9 — Validation d'actions

Pour les décisions avec `AUTO_EXECUTE_DECISIONS=False` (dev) ou ordres
importants :

- Embed « Décision proposée »
- Boutons : ✅ Approuver / ❌ Refuser / ⏳ Plus tard
- L'approbation déclenche `POST /api/v1/decisions/{id}/execute`

---

## Plan d'action

| # | Tâche | Fichier |
|---|---|---|
| 9.1 | `/analyse` | `analyse.py` |
| 9.2 | `/orders` | `orders.py` |
| 9.3 | `/rapport` | `report.py` |
| 9.4 | `/pourquoi` | `why.py` |
| 9.5 | `/decisions` | `decisions.py` |
| 9.6 | `/alerts` | `alerts.py` |
| 9.7 | `/config` | `config_cmd.py` |
| 9.8 | Notifications | `notifications.py` |
| 9.9 | Validation flow | `analyse.py` (boutons) |
| 9.10 | Enregistrer cogs | `client.py` |
| 9.11 | Endpoints API | `main.py` |

---

## Configuration à ajouter (`config.py`)

```python
DISCORD_REPORT_CHANNEL_ID: str | None = None
DISCORD_ALERT_CHANNEL_ID: str | None = None
DISCORD_ADMIN_ROLE_ID: str | None = None
```

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/bot/commands/analyse.py` | **Créer** |
| `src/bot/commands/orders.py` | **Créer** |
| `src/bot/commands/report.py` | **Créer** |
| `src/bot/commands/why.py` | **Créer** |
| `src/bot/commands/decisions.py` | **Créer** |
| `src/bot/commands/alerts.py` | **Créer** |
| `src/bot/commands/config_cmd.py` | **Créer** |
| `src/bot/notifications.py` | **Créer** |
| `src/bot/client.py` | **Modifier** |
| `src/main.py` | **Modifier** |
| `src/config.py` | **Modifier** |

---

## Critères de validation

- [ ] `/analyse BTC` affiche une décision IA complète
- [ ] `/orders` liste les ordres avec statut
- [ ] `/rapport` génère et affiche un rapport
- [ ] `/pourquoi ETH` affiche le raisonnement
- [ ] `/decisions` liste l'historique
- [ ] `/alerts` liste les alertes
- [ ] `/config` affiche la stratégie active
- [ ] Les notifications arrivent sur les channels configurés
- [ ] Le bouton « Exécuter » déclenche l'ordre (avec confirmation)
- [ ] `pyright` passe sans erreur

---

## Notes

- Les commandes interrogent **toujours** l'API FastAPI (jamais Supabase direct)
- Embeds Discord : max 6000 chars, 25 fields → paginer si nécessaire
- `/config edit` doit être **admin-only** (permissions Discord)
- Dédupliquer les alertes similaires dans une fenêtre d'1h (anti-spam)

