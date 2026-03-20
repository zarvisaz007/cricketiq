# HANDOFF.md — CricketIQ

> You are an AI agent. Read this file fully. Propose tasks. Wait for approval. Then work.
> You have no memory of previous sessions. This file is your only context.

---

## AGENT PROTOCOL

Follow these steps every session, no exceptions:

```
STEP 1 — Read this entire file fully

STEP 2 — Choose up to 3 tasks marked [ ]
          Rule: if any chosen task is long-running (>10 min), choose only that 1 task

STEP 3 — IMMEDIATELY mark all chosen tasks as [~] in this file
          Example: [~] Compute player ratings — proposed by session-A, awaiting approval
          Do this BEFORE telling the user. This prevents other agents from grabbing the same tasks.

STEP 4 — Tell the user which tasks you've reserved and ask for approval:
          "I've reserved these tasks. Shall I proceed?
           1. Compute player ratings
           2. Verify ratings
           3. Build Elo ratings"

STEP 5 — WAIT. Do NOT start any work until the user replies "yes" or "proceed".
          If user says no or changes the list — update [~] back to [ ] for rejected tasks.

STEP 6 — Do the approved tasks one by one.
          After each task: change [~] to [x] and add a one-line result.

STEP 7 — Report completion summary to the user.

STEP 8 — Add one line per completed task to AGENT LOG at the bottom.

STEP 9 — Stop. Wait for the user to clear context before doing anything else.
```

**Task lock rules:**
- `[ ]` = available — anyone can propose it
- `[~]` = reserved — proposed or in progress, do NOT touch
- `[x]` = done — never touch again
- If a `[~]` task was reserved more than 90 minutes ago with no log entry, it may be abandoned — reset to `[ ]` and re-propose

---

## PROJECT SNAPSHOT

**What it is:**
CricketIQ is a local cricket prediction engine. It uses historical match data
to predict match outcomes, rate players, and compute PVOR (player impact scores).
Output is a CLI. Telegram bot comes post-MVP.

**Current phase:** Phase 1 — Data ingestion not yet started.

**Tech:** Python 3.10+ | SQLite | XGBoost | Monte Carlo simulation | OpenRouter LLM

**Key files:**

| File | Purpose |
|------|---------|
| `frontend/test_cli.py` | Run this to test everything interactively |
| `backend/data/ingestion.py` | Parses Cricsheet JSON → SQLite |
| `backend/ratings/player_ratings.py` | Computes player ratings |
| `backend/models/train_all.py` | Trains Logistic + XGBoost models |
| `backend/simulation/monte_carlo.py` | 2000-run match simulation |
| `backend/impact/pvor.py` | PVOR = P(win with player) − P(win without) |
| `database/db.py` | SQLite schema and connection |
| `scripts/orchestrator.py` | Runs full pipeline automatically |

**Commands:**

| Command | Does |
|---------|------|
| `make setup` | Full pipeline: install → db → download → ingest → train |
| `make run` | Launch interactive CLI |
| `make reset` | Wipe DB and restart |
| `python3 scripts/orchestrator.py` | Auto-run pipeline with dependency checks |
| `python3 scripts/orchestrator.py --from ingest` | Resume pipeline from a step |

**Folder map:**
```
backend/     ← data, features, models, simulation, impact, ratings, nlp
frontend/    ← test_cli.py, bot/ (post-MVP)
database/    ← db.py
scripts/     ← orchestrator.py, setup_db.py, download_data.py
docs/        ← this file + detailed specs
agents/      ← NOVA, ATLAS, FORGE, LENS role definitions
```

---

## TASK QUEUE

### Phase 0: Setup (completed)
- [x] Create project structure
- [x] Write all docs files
- [x] Write all Python modules
- [x] Write Makefile and orchestrator
- [x] Fix import paths for backend/ structure

---

### Phase 1: Data

- [x] Install dependencies — run: `pip3 install -r requirements.txt` — all 11 packages satisfied (pandas, numpy, sklearn, xgboost, scipy, requests, dotenv, tqdm, tabulate, openai, joblib)
- [x] Initialize database — run: `python3 scripts/setup_db.py` — database/cricketiq.db created successfully
- [x] Download IPL data — run: `python3 scripts/download_data.py ipl` — 1169 match files downloaded
- [x] Download T20 international data — run: `python3 scripts/download_data.py t20s` — 5082 match files downloaded
- [x] Download ODI data — run: `python3 scripts/download_data.py odis` — 3100 match files (already present)
- [x] Ingest all data — run: `python3 backend/data/ingestion.py` — 9351 matches ingested (1169 IPL + 5082 T20 + 3100 ODI), 0 errors
- [x] Verify ingestion — check: DB has >1000 matches via `sqlite3 database/cricketiq.db "SELECT count(*) FROM matches;"` — 9351 matches confirmed

---

### Phase 2: Ratings

- [~] Compute player ratings — proposed by Claude (session-2026-03-21-B), awaiting approval — run: `python3 backend/ratings/player_ratings.py` — SLOW: 7032 T20 + ODI + Test players, takes 30+ min. Kill all other python processes first or DB will lock. Script killed mid-run last session.
- [ ] Verify ratings — check: `sqlite3 database/cricketiq.db "SELECT player_name, overall_rating FROM player_ratings ORDER BY overall_rating DESC LIMIT 10;"` — Kohli/Rohit should appear
- [ ] Build Elo ratings — run: `python3 backend/models/elo.py`
- [ ] Verify Elo — check: India/Australia in top 10 T20 teams

---

### Phase 3: Models

- [ ] Train all models — run: `python3 backend/models/train_all.py`
- [ ] Verify logistic model — check: `backend/models/logistic_T20.pkl` exists
- [ ] Verify XGBoost model — check: `backend/models/xgb_T20.pkl` exists
- [ ] Check model accuracy — should be >55% val accuracy in train output

---

### Phase 4: CLI Testing

- [ ] Launch CLI — run: `python3 frontend/test_cli.py`
- [ ] Test match prediction — option 1: India vs Australia, T20
- [ ] Test player rating — option 2: Virat Kohli, T20
- [ ] Test PVOR — option 3: Jasprit Bumrah, India vs Australia
- [ ] Test player report — option 4: any player
- [ ] Test team analysis — option 5: India
- [ ] Test top players — option 6: T20, overall
- [ ] Test smart alerts — option 7: India vs Australia
- [ ] Test Elo rankings — option 8: T20
- [ ] All 8 options return results without errors

---

### Phase 5: Post-MVP (do not start until Phase 4 complete)

- [ ] Create Telegram bot via BotFather — get token
- [ ] Add TELEGRAM_BOT_TOKEN to .env
- [ ] Implement frontend/bot/handlers.py
- [ ] Test all bot commands locally
- [ ] Deploy to Railway or DigitalOcean

---

## AGENT LOG

_Most recent entry first._

| Date | Agent | Task | Result |
|------|-------|------|--------|
| 2026-03-21 | Claude | Phase 1 complete, Phase 2 blocked | Phase 1 done (9351 matches). player_ratings.py killed mid-run due to long runtime (~30min). DB lock bug fixed (timeout=30 in db.py). Next: run player_ratings.py solo, no competing processes. |
| 2026-03-21 | Claude | Phase 1 Data complete | T20 (5082) + ODI (3100) downloaded; all 9351 matches ingested into SQLite, 0 errors |
| 2026-03-21 | Bootstrap | Project initialization | All files created, structure reorganized to backend/frontend |

---

## NOTES FOR AGENTS

- Player names must match Cricsheet format exactly (e.g. "V Kohli" in older files, "Virat Kohli" in newer)
- match_type must be exactly "T20", "ODI", or "Test" — capital letters, no spaces
- SQLite file is at: `database/cricketiq.db`
- PVOR computation takes ~10 seconds (runs 2000 simulations × 2)
- OpenRouter API key is optional — reports have rule-based fallback
- If you see import errors, check that you are running from `~/Desktop/cricketiq/`
