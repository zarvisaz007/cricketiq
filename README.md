# CricketIQ — Cricket Prediction Engine (MVP)

A data-driven cricket prediction system using player ratings, Elo, XGBoost,
Monte Carlo simulation, and PVOR impact scoring.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python scripts/setup_db.py

# 3. Download Cricsheet data
python scripts/download_data.py

# 4. Ingest match data into DB
python data/ingestion.py

# 5. Compute player/team ratings
python ratings/player_ratings.py

# 6. Train ML models
python models/train_all.py

# 7. Run the CLI tester
python test_cli.py
```

## Project Docs

All documentation lives in `/docs`. New AI sessions start here:

```
Read docs/session-start.md and continue.
```

## Module Overview

| Module | Purpose |
|--------|---------|
| `data/` | Cricsheet ingestion + normalization |
| `features/` | Player and team feature computation |
| `models/` | Elo, Logistic Regression, XGBoost |
| `simulation/` | Monte Carlo match simulation |
| `impact/` | PVOR player impact engine |
| `ratings/` | Player rating system |
| `nlp/` | LLM-powered reports via OpenRouter |
| `test_cli.py` | CLI interface to test all features |

## Status

MVP Phase — local testing. Telegram bot integration planned post-MVP.
