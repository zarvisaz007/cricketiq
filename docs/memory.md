# Memory — CricketIQ Project Context

This file is a compact summary of the entire project.
New AI sessions should read this first for fast context loading.

---

## What this project is

CricketIQ is a cricket match prediction CLI tool that uses:
- Historical match data from Cricsheet (free JSON)
- Player rating system (batting + bowling + form + consistency)
- Elo rating for teams
- Logistic + XGBoost ML models
- Monte Carlo simulation (2000 runs)
- PVOR: measures individual player's win impact

Output is a win probability with confidence score and key factors.

---

## Tech

- Python 3.10+
- SQLite (database/cricketiq.db)
- scikit-learn, xgboost, numpy, pandas
- OpenRouter for LLM reports (optional, has rule-based fallback)
- No Telegram bot yet (post-MVP)

---

## Current Phase

**MVP** — local CLI testing only.

Data → DB → Ratings → Models → test_cli.py

---

## Key Files

| File | Purpose |
|------|---------|
| frontend/test_cli.py | Main interface to test all features |
| backend/data/ingestion.py | Load Cricsheet data into SQLite |
| backend/ratings/player_ratings.py | Compute player ratings |
| backend/models/train_all.py | Train all ML models |
| backend/simulation/monte_carlo.py | Monte Carlo engine |
| backend/impact/pvor.py | Player impact (PVOR) |
| scripts/orchestrator.py | Automated pipeline runner |
| Makefile | One-command shortcuts |
| docs/progress.md | What's done and what's next |

## Agents

| Name | Agent | Owns |
|------|-------|------|
| NOVA | Backend | backend/, database/, scripts/ |
| ATLAS | Frontend | frontend/ |
| FORGE | Infra | Makefile, orchestrator, .env |
| LENS | Reviewer | docs/ (read-only on code) |

---

## Important Constraints

- Player names must match Cricsheet format exactly
- match_type must be "T20", "ODI", or "Test" (exact case)
- Models only train after data is ingested
- PVOR takes ~10 seconds (runs simulations)
- SQLite file: database/cricketiq.db

---

## Last Updated

2026-03-20 — Project initialized, all code written.
Next: download data and run ingestion.
