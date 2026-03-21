# CricketIQ v2 — Upgrade Implementation Plan

> **Purpose:** Any new Claude Code session can read this file and immediately know what's done, what's in progress, and what to build next. No need to read the entire codebase first.
>
> **Project root:** `/Users/zarvis/Desktop/cricketiq`
> **Sister project (port source):** `/Users/zarvis/Desktop/Claude-cricket`

---

## Current State (MVP v1)

- **DB:** SQLite with 5 tables: `players`, `matches`, `player_match_stats`, `elo_ratings`, `player_ratings`
- **Models:** Elo, Logistic Regression, XGBoost (11 features, 86.5% T20 accuracy), Monte Carlo
- **CLI:** 8 features (predict, player profile, PVOR, report, team analysis, leaderboard, alerts, elo rankings)
- **Bot:** Telegram bot with 7 conversation flows (in `frontend/bot/handlers.py`)
- **Data:** 9,351 matches ingested from Cricsheet (IPL, T20I, ODI)
- **PVOR:** Monte Carlo based (~10s for 2000 sims)

---

## Phase Checklist

### Phase 0: Database Schema Upgrade [DONE]
- [x] **0.1** Create `database/migrations/001_schema_v2.py` with 9 new tables
- [x] **0.2** Add columns to `matches`: `venue_id`, `tournament_id`, `cricbuzz_match_id`
- [x] **0.3** Add columns to `player_match_stats`: `batting_position`, `bowling_slot`, `catches`, `stumpings`
- [x] **0.4** Add performance indices (21 indices created)
- [x] **0.5** Create `database/seed_venues.py` with 30 major venue data
- [x] **0.6** Update `database/db.py` with `migrate_db()` function
- [x] **0.7** Migration verified — 14 tables, 30 venues seeded

**New tables:**
```
venues              — pitch characteristics (batting/spin/pace/dew factors, avg scores)
tournaments         — tournament metadata (IPL seasons, ICC events)
innings             — per-innings summary (runs, wickets, overs, extras)
deliveries          — ball-by-ball data (batter, bowler, runs, wicket, over_number)
predictions_log     — every prediction + actual outcome
model_records       — ML model versions + accuracy metrics
pvor_match          — per-player per-match PVOR values
pvor_player_agg     — aggregated PVOR stats (30d, 90d, career)
live_matches        — active live match tracking
```

**Files to modify:** `database/db.py`
**Files to create:** `database/migrations/001_schema_v2.py`, `database/seed_venues.py`

---

### Phase 1: Feature Engineering v2 [Depends: Phase 0]

- [x] **1a** Exponential decay form in `team_features.py` and `player_features.py`
  - `weight_i = exp(-0.1 * i)` applied to both team form and player form
  - Modified: `backend/features/team_features.py`, `backend/features/player_features.py`

- [x] **1b** Phase analysis features
  - T20 phases: powerplay (1-6), middle (7-15), death (16-20)
  - Created: `backend/features/phase_features.py`
  - Modified: `backend/data/ingestion.py` (now stores deliveries, innings, batting_position, bowling_slot, catches, stumpings)

- [x] **1c** Venue/pitch features
  - Created: `backend/features/venue_features.py` (fuzzy venue matching, home advantage, pitch factors)

- [x] **1d** H2H recency features
  - Enhanced `get_head_to_head()`: decay-weighted last-5, win streak tracking
  - Modified: `backend/features/team_features.py`

- [ ] **1e** Bowler-batter matchups (DEFERRED)
  - Per-player matchup stats from deliveries table
  - Create: `backend/features/matchup_features.py`

- [x] **1f** Feature registry
  - 28 features in `FEATURE_COLS`, defaults dict, `build_feature_vector()`, `feature_vector_to_list()`
  - Created: `backend/features/feature_registry.py`

---

### Phase 2: Model Training v2 [DONE]

- [x] **2a** TimeSeriesSplit (5-fold) in both `xgboost_model.py` and `logistic.py`
- [x] **2b** Calibration: `backend/models/calibration.py` (isotonic + Platt scaling)
- [x] **2c** Ensemble: `backend/models/ensemble.py` (Brier-weighted, disagreement flag)
- [x] **2d** Prediction tracker: `backend/models/prediction_tracker.py` (log, backfill, accuracy report)
- [x] **2e** XGBoost upgraded: 300 trees, depth=5, regularization, model record logging

---

### Phase 3: Live Data Integration [DONE]

- [x] **3a** HTTP client: `backend/scrapers/http_client.py` (12 UAs, 2s rate limit, exp backoff)
- [x] **3b** Cricbuzz scraper: `backend/scrapers/cricbuzz_live.py` (JSON API + HTML fallback)
- [ ] **3c** ESPN historical scraper (DEFERRED)
- [x] **3d** Live poller: `backend/scrapers/live_poller.py` (45s daemon thread)
- [ ] **3e** CLI live scores menu — pending CLI integration

---

### Phase 4: IPL-Specific Features [Depends: Phase 0, Phase 1]

- [ ] **4a** IPL feature engineering
  - Franchise strength, home ground advantage, foreign player impact (max 4 rule)
  - IPL form (current season + last season)
  - Create: `backend/features/ipl_features.py`

- [ ] **4b** IPL-specific model
  - Separate XGBoost trained only on IPL data
  - Create: `backend/models/ipl_predictor.py`

- [ ] **4c** IPL season tracker
  - Points table, NRR, playoff probability (Monte Carlo)
  - Create: `backend/features/ipl_season.py`

- [ ] **4d** CLI IPL menu
  - "IPL Zone" submenu: predictions, points table, playoff probs, rankings
  - Modify: `frontend/test_cli.py`

---

### Phase 5: Dream11 Fantasy Team Builder [Depends: Phase 1, Phase 4]

- [ ] **5a** Dream11 scoring system
  - Full scoring: batting (+1/run, +1 boundary, +2 six, milestones), bowling (+25/wicket), fielding (+8 catch)
  - Captain 2x, VC 1.5x
  - Create: `backend/fantasy/dream11_scoring.py`

- [ ] **5b** Fantasy team selector
  - Integer linear programming (PuLP) to maximize expected fantasy points
  - Constraints: 11 players, min 1 WK / 3 BAT / 3 BOWL / 1 AR, 100 credit budget
  - Captain + VC selection (highest expected point differential)
  - Create: `backend/fantasy/team_selector.py`, `backend/fantasy/expected_points.py`, `backend/fantasy/credit_values.py`
  - **Port base from:** `Claude-cricket/src/ml/team_selector.py`

- [ ] **5c** CLI fantasy menu
  - "Dream11 Team Builder": select match, show XI with roles, C/VC, expected points breakdown
  - Modify: `frontend/test_cli.py`

---

### Phase 6: PVOR Overhaul [Depends: Phase 0, Phase 1]

- [ ] **6.1** Analytical PVOR (sub-second)
  - Replace MC-based PVOR with analytical formula:
    ```
    batting_pvor = (player_runs - replacement_avg) / replacement_std
    bowling_pvor = (replacement_wpm - player_wpm) / replacement_std
    ```
  - Replacement level = 25th percentile at same batting_position/bowling_slot
  - Keep MC-based as secondary option
  - Create: `backend/impact/pvor_analytical.py`
  - Modify: `backend/impact/pvor.py` (add mode switch)
  - **Port from:** `Claude-cricket/src/analytics/pvor.py`

- [ ] **6.2** Rolling PVOR aggregation (30d, 90d, career)
  - Store in `pvor_player_agg` table
  - Modify: `backend/impact/pvor.py`

---

### Phase 7: Telegram Bot Upgrade [Depends: Phase 2, Phase 3]

- [ ] **7.1** Port bot architecture from Claude-cricket
  - Menu: Predict, Live Scores, Player Report, Dream11 Team, IPL Zone, Leaderboards
  - Inline keyboard navigation, "Why?" button for explanations
  - Create: `bot/main.py`, `bot/formatters.py`
  - Modify: `frontend/bot/handlers.py`
  - **Port from:** `Claude-cricket/src/bot/main.py` + `handlers.py`

---

### Phase 8: Auto-Retrain & Infrastructure [Depends: Phase 2]

- [ ] **8.1** Nightly retrain script
  - Incremental data download + ingest + retrain + log metrics
  - Create: `scripts/nightly_retrain.py`

- [ ] **8.2** Orchestrator upgrade
  - Add: `scrape_espn`, `seed_venues`, `train_ipl`, `pvor_batch`, `calibrate`
  - Modify: `scripts/orchestrator.py`

- [ ] **8.3** Updated requirements.txt
  - Add: `beautifulsoup4`, `lxml`, `tenacity`, `python-telegram-bot`, `pulp`

- [ ] **8.4** Updated Makefile
  - Add: `migrate`, `scrape`, `live`, `ipl`, `fantasy`, `bot`, `retrain`

---

## Dependency Graph

```
Phase 0 (DB Schema) ─────────────────────────────────────────────
  │
  ├──> Phase 1a-1d (Decay, Venue, H2H)
  │      └──> Phase 1b (Phase analysis)
  │             └──> Phase 1f (Feature registry)
  │                    └──> Phase 2 (Models v2)
  │                           ├──> Phase 7 (Telegram Bot)
  │                           └──> Phase 8 (Auto-retrain)
  │
  ├──> Phase 3 (Live Data) ──────> Phase 7
  │
  ├──> Phase 4 (IPL) ──────────> Phase 5 (Dream11)
  │
  └──> Phase 6 (PVOR overhaul)
```

---

## 3-Session Parallel Strategy

### Session A: "Core ML Pipeline" (Phases 0 → 1 → 2)
```
Task: Build the prediction engine v2

1. Run Phase 0 (DB migration) — must complete first
2. Phase 1a: Exponential decay in team_features.py + player_features.py
3. Phase 1c: Venue features (backend/features/venue_features.py)
4. Phase 1d: H2H recency (enhance team_features.py)
5. Phase 1f: Feature registry (backend/features/feature_registry.py)
6. Phase 2a: TimeSeriesSplit in xgboost_model.py + logistic.py
7. Phase 2b: Calibration (backend/models/calibration.py)
8. Phase 2c: Ensemble (backend/models/ensemble.py)
9. Phase 2d: Prediction tracker
10. Phase 2e: Hyperparameter tuning

Prompt for Claude Code:
"Read /Users/zarvis/Desktop/cricketiq/V2_UPGRADE_PLAN.md. You are Session A.
Implement Phases 0, 1a, 1c, 1d, 1f, 2a-2e in order. Phase 0 must go first.
After each task, update the checkbox in V2_UPGRADE_PLAN.md from [ ] to [x].
Run the pipeline after Phase 0 to verify DB migration works.
Port venue schema ideas from /Users/zarvis/Desktop/Claude-cricket/src/data/db.py."
```

### Session B: "Live Data + Scrapers" (Phases 3 + 1b)
```
Task: Build live data pipeline + ball-by-ball analysis

WAIT: Check V2_UPGRADE_PLAN.md — Phase 0 checkbox 0.1 must be [x] before starting.
If not done, wait and re-check every 30 seconds.

1. Phase 3a: HTTP client (port from Claude-cricket)
2. Phase 3b: Cricbuzz live scraper (port from Claude-cricket)
3. Phase 3d: Live match poller
4. Phase 1b: Phase analysis features (needs deliveries table from Phase 0)
5. Phase 3e: CLI live scores menu
6. Phase 8.3: Update requirements.txt
7. Phase 8.4: Update Makefile

Prompt for Claude Code:
"Read /Users/zarvis/Desktop/cricketiq/V2_UPGRADE_PLAN.md. You are Session B.
First verify Phase 0 checkbox 0.1 is [x] (DB migration done). If not, wait.
Implement Phases 3a, 3b, 3d, 1b, 3e, 8.3, 8.4 in order.
Port http_client.py and cricbuzz_live.py from /Users/zarvis/Desktop/Claude-cricket/src/scrapers/.
Adapt from SQLAlchemy to raw sqlite3 (CricketIQ uses sqlite3 directly, not ORM).
After each task, update the checkbox in V2_UPGRADE_PLAN.md from [ ] to [x]."
```

### Session C: "IPL + Fantasy + PVOR" (Phases 4, 5, 6)
```
Task: Build IPL features, Dream11 builder, and PVOR overhaul

WAIT: Check V2_UPGRADE_PLAN.md — Phase 0 checkbox 0.1 must be [x] before starting.

1. Phase 6.1: Analytical PVOR (port from Claude-cricket)
2. Phase 6.2: Rolling PVOR aggregation
3. Phase 4a: IPL feature engineering
4. Phase 4b: IPL-specific model
5. Phase 4c: IPL season tracker
6. Phase 4d: CLI IPL menu
7. Phase 5a: Dream11 scoring system
8. Phase 5b: Fantasy team selector (port base from Claude-cricket)
9. Phase 5c: CLI fantasy menu

Prompt for Claude Code:
"Read /Users/zarvis/Desktop/cricketiq/V2_UPGRADE_PLAN.md. You are Session C.
First verify Phase 0 checkbox 0.1 is [x] (DB migration done). If not, wait.
Implement Phases 6, 4a-4d, 5a-5c in order.
Port PVOR from /Users/zarvis/Desktop/Claude-cricket/src/analytics/pvor.py.
Port team_selector base from /Users/zarvis/Desktop/Claude-cricket/src/ml/team_selector.py.
Adapt all code from SQLAlchemy to raw sqlite3.
After each task, update the checkbox in V2_UPGRADE_PLAN.md from [ ] to [x]."
```

### After All 3 Sessions Complete:
```
Run a single session for integration:
"Read /Users/zarvis/Desktop/cricketiq/V2_UPGRADE_PLAN.md.
All 3 parallel sessions should be done. Do:
1. Verify all checkboxes are [x]
2. Phase 7: Telegram bot upgrade (port from Claude-cricket)
3. Phase 8.1-8.2: Nightly retrain + orchestrator
4. Run full pipeline: make reset && make setup
5. Test: predict India vs Australia T20
6. Verify all CLI menus load without error"
```

---

## Key Architecture Rules

1. **DB layer:** Raw `sqlite3` — no ORM. Use `database.db.get_connection()` everywhere.
2. **Imports:** All modules use `sys.path` hack at top (see existing files for pattern).
3. **Path convention:** `from database.db import get_connection`, `from features.X import Y`
4. **Model storage:** `models/` dir (joblib `.pkl` files)
5. **No external APIs** except Cricbuzz scraping (respect rate limits).
6. **All files in project root** `/Users/zarvis/Desktop/cricketiq/` — nothing outside.

---

## Verification After Each Phase

```bash
# After Phase 0:
python3 -c "from database.db import get_connection; c=get_connection(); print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"

# After Phase 1:
python3 -c "from backend.features.feature_registry import FEATURE_COLS; print(f'{len(FEATURE_COLS)} features registered')"

# After Phase 2:
make train && python3 -c "from backend.models.xgboost_model import predict; print(predict('India','Australia','',  'T20'))"

# After Phase 3:
python3 -c "from backend.scrapers.cricbuzz_live import get_live_matches; print(get_live_matches())"

# Full test:
make run  # CLI should show all menus without error
```

---

## Target Metrics

- XGBoost accuracy: **88-90%** (up from 86.5%)
- Calibration: predicted 70% should win ~70% of the time
- Dream11 team satisfies all constraints (11 players, role balance, 100 credits)
- Live scores update during active matches
- IPL model outperforms generic T20 model on IPL matches
- PVOR computation: **sub-second** (down from ~10s)
