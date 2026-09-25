# ÉTAPE 00 — Audit & corrections de l'existant

> **Priorité** : 🔴 Critique
> **Prérequis** : Aucun (première étape)
> **Objectif** : Coriger les bugs et incohérences détectés dans la base actuelle avant d'ajouter de nouvelles couches.

---

## Contexte

Le projet fonctionne déjà (collectors, bot Discord, API FastAPI, ordres).
Cependant, un audit du code révèle plusieurs **incohérences** entre le code
Python et le schéma SQL, ainsi que des fichiers vides. Il faut corriger ces
problèmes **avant** d'ajouter les couches IA, sous peine de propager les bugs.

> ⚠️ **Note migration DB** : Cette étape ne nécessite **aucune migration SQL**.
> Le schéma de `bot_managed_assets` (table `001_initial_orionis_schema.sql`)
> est **correct** et constitue la source de vérité. Seul le code Python est
> bugué (il utilisait les noms de colonnes de la table `portfolio` au lieu de
> ceux de `bot_managed_assets`). Les corrections se font uniquement côté code.

---

## Problèmes identifiés

### P1 — Incohérence `bot_managed_assets` (CRITIQUE)

**Schéma SQL** (`001_initial_orionis_schema.sql`, lignes 51-58) définit :

```sql
CREATE TABLE public.bot_managed_assets (
    asset VARCHAR(20) PRIMARY KEY,
    allocated_quantity NUMERIC(38, 18),   -- ← nom
    total_invested_eur NUMERIC(20, 8),    -- ← nom
    current_price NUMERIC(20, 8),
    current_value NUMERIC(20, 8) GENERATED ALWAYS AS (...),
    updated_at TIMESTAMPTZ
);
```

**Code Python** (`src/execution/order_executor.py`, méthodes
`_update_bot_managed_assets`) utilise :

```python
existing["quantity"]          # ← n'existe pas dans le schéma (devrait être allocated_quantity)
existing["avg_buy_price"]     # ← n'existe pas (devrait être total_invested_eur / allocated_quantity)
"quantity": new_qty           # ← insert/update avec mauvais nom de colonne
"avg_buy_price": price
"origin": "ORIONIS"           # ← colonne inexistante dans bot_managed_assets
```

→ **L'exécution d'un ordre va crasher** en production (Supabase rejettera la
requête avec colonnes inexistantes). Le bot Discord `/trade` ne fonctionne
donc probablement pas pour la mise à jour du sous-portefeuille.

### P2 — Discord `/portfolio` (vue Orionis) lit des colonnes inexistantes

`src/bot/commands/portfolio.py` (ligne 116-117) :

```python
qty = float(item["quantity"])           # ← devrait être allocated_quantity
buy_price = float(item["avg_buy_price"])  # ← n'existe pas
```

→ Même problème que P1 côté lecture.

### P3 — `src/strategy/engine.py` est vide

Fichier créé mais sans contenu. Sera rempli à l'étape 05 (AI Analysis).

### P4 — Modèle Pydantic `BotManagedAssetBase` désynchronisé

`src/database/models/portfolio.py` définit `allocated_quantity` et
`total_invested_eur` (correct vis-à-vis du schéma), mais le code d'exécution
et la commande Discord ne l'utilisent pas. Il faut aligner le runtime sur ces
modèles.

### P5 — `market_cap` toujours `None`

`src/collectors/market_collector.py` (ligne 153) :
`"market_cap": None  # Can be populated via CoinGecko if needed`
→ Sera adressé à l'étape 04 (intégration CoinGecko).

### P6 — `SentimentAnalyzer` rule-based uniquement

`src/collectors/news_collector.py` — le sentiment est basé sur des mots-clés.
La vision prévoit un **résumé IA** des articles. Sera amélioré à l'étape 04.

---

## Plan d'action

### Action 1 — Correction `order_executor.py`

Aligner `_update_bot_managed_assets` sur le schéma réel :

- `quantity` → `allocated_quantity`
- `avg_buy_price` → `total_invested_eur` (calcul : ancien_total_invested + montant_achat)
- Supprimer la colonne `origin` (n'existe pas dans `bot_managed_assets`)
- Pour un achat :
  - `allocated_quantity` = ancien + amount
  - `total_invested_eur` = ancien + (amount * price)
  - `current_price` = price
- Pour une vente :
  - `allocated_quantity` = ancien - amount
  - `total_invested_eur` = ancien * (new_qty / old_qty)  (proportionnel)
  - si `allocated_quantity <= 1e-6` → delete

### Action 2 — Correction `portfolio.py` (commande Discord)

- `item["quantity"]` → `item["allocated_quantity"]`
- `item["avg_buy_price"]` → calculer PRU = `total_invested_eur / allocated_quantity`

### Action 3 — Vérifier/supprimer `src/strategy/engine.py` vide

Le laisser vide avec un docstring placeholder OU le supprimer (il sera recréé
à l'étape 05). Recommandation : ajouter un docstring explicatif.

### Action 4 — Test manuel de bout en bout

Après corrections :
1. Lancer l'API : `.venv/bin/uvicorn src.main:app --reload --port 8000`
2. Déclencher un sync portfolio : `POST /api/v1/sync/portfolio`
3. Tester `/portfolio` sur Discord (vue Global + Orionis)
4. Tester un petit ordre `/trade` (ex: 0.001 ETH) et vérifier que
   `bot_managed_assets` se met à jour sans erreur

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `src/execution/order_executor.py` | **Modifier** `_update_bot_managed_assets` |
| `src/bot/commands/portfolio.py` | **Modifier** `fetch_portfolio_embed` (vue Orionis) |
| `src/strategy/engine.py` | **Modifier** (docstring placeholder) |
| `src/database/models/portfolio.py` | **Vérifier** cohérence (déjà OK) |

---

## Critères de validation

- [ ] `order_executor.py` n'utilise plus `quantity`, `avg_buy_price`, `origin`
      sur la table `bot_managed_assets`
- [ ] La commande `/portfolio` (vue Orionis) affiche les positions sans erreur
- [ ] Un ordre `/trade` d'achat met à jour `bot_managed_assets` correctement
      (colonnes `allocated_quantity` et `total_invested_eur`)
- [ ] Un ordre `/trade` de vente diminue `allocated_quantity` et supprime la
      ligne si quantité ≤ seuil
- [ ] `strategy/engine.py` contient au minimum un docstring
- [ ] L'API démarre sans erreur de typage (pyright clean)

---

## Risques

- **Données existantes** : si `bot_managed_assets` contient déjà des lignes
  avec d'anciennes colonnes (très peu probable vu le bug), il faudra peut-être
  un script de migration de données. À vérifier dans Supabase avant de corriger.
- **Tests en argent réel** : utiliser un montant très petit (ex: 0.001 ETH)
  pour valider sans risque significatif.
