# CricketIQ — AI Cricket Prediction Engine & Telegram Bot

The definitive, fully consolidated version of the CricketIQ project.
4 ML models · 28 features · Dream11 optimizer · Live scores · Full IPL hub · Rich Telegram UI

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Telegram bot token
cp .env.example .env
# Edit .env → set TELEGRAM_BOT_TOKEN=your_token_from_botfather

# 3. Start the bot
python start_bot.py
```

### Other commands
```bash
python start_bot.py --kill    # stop running bot
python start_bot.py --check   # is bot running?
make bot                      # same as python start_bot.py
make setup                    # full pipeline: install → db → ingest → train
make train                    # retrain all models
make schedule                 # scrape upcoming matches
make live                     # live score poller standalone
```

---

## Bot Features

| Feature | Description |
|---------|-------------|
| Match Predictions | 4-model ensemble: Elo + Logistic + XGBoost + Monte Carlo |
| Dream11 | PuLP optimizer with player ratings and expected points |
| IPL Hub | Points table, playoff probabilities, team/squad/player stats |
| Live Scores | Cricbuzz live scorecard with auto-refresh |
| Upcoming Matches | Rich match cards with venue, H2H, form, playing XI |
| Player Lookup | Ratings, career stats, form by role/team |
| Team Analysis | Elo ratings, squad strength, form, key players |
| Leaderboards | Elo rankings and top player lists |

---

## Project Structure

```
cricketiq/
├── start_bot.py             ← START HERE — one-command bot launcher
├── bot/
│   └── main.py              ← bot entry: handlers + 3 pollers
├── frontend/bot/            ← 10 handler modules + keyboards + formatters
│   ├── handlers_menu.py     ← /start, main menu, back navigation
│   ├── handlers_predict.py  ← 4-model ensemble predictions
│   ├── handlers_ipl.py      ← full IPL hub (13 handlers)
│   ├── handlers_dream11.py  ← Dream11 team builder
│   ├── handlers_upcoming.py ← match browser + rich reports
│   ├── handlers_live.py     ← live scorecards
│   ├── handlers_player.py   ← player profiles
│   ├── handlers_team.py     ← team analysis
│   ├── handlers_leaderboard.py
│   ├── keyboards.py         ← all inline keyboards
│   └── formatters.py        ← rich text formatters
├── backend/
│   ├── scrapers/            ← Cricbuzz live/schedule + ESPN + Cricsheet
│   ├── models/              ← Elo, Logistic, XGBoost, ensemble, IPL predictor
│   ├── features/            ← 28-feature registry (team/player/venue/phase)
│   ├── fantasy/             ← Dream11 PuLP optimizer
│   ├── impact/              ← PVOR player impact engine
│   ├── ratings/             ← player ratings, leaderboards, team strength
│   ├── simulation/          ← Monte Carlo match simulator
│   └── nlp/                 ← LLM reports via OpenRouter
├── database/
│   ├── db.py                ← SQLite connection + migrations
│   └── cricketiq.db         ← production database (9351+ matches)
├── models/                  ← trained .pkl files (XGBoost + Logistic)
├── scripts/                 ← setup_db, download_data, nightly_retrain,
│                               backfill_espn, populate_real_data, update_matches
├── data/raw/                ← Cricsheet match files (IPL/T20I/ODI/Test)
└── docs/                    ← HANDOFF, progress, architecture, decisions
```

---

## Data & Models

- **Database:** SQLite at `database/cricketiq.db` (9351 matches ingested)
- **Trained models:** `models/` — `xgb_T20.pkl`, `xgb_ODI.pkl`, `xgb_IPL.pkl`, `logistic_T20.pkl`, `logistic_ODI.pkl`
- **Raw data:** `data/raw/` — Cricsheet ball-by-ball JSON (1170 IPL + 5082 T20I + 3100 ODI + Test files)

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Required — from @BotFather |
| `OPENROUTER_API_KEY` | Optional — enables AI match reports |
| `DB_PATH` | Default: `database/cricketiq.db` |
| `LOG_LEVEL` | Default: `INFO` |

---

## Accuracy

| Model | Format | Accuracy |
|-------|--------|----------|
| XGBoost | T20 | 86.50% |
| XGBoost | ODI | 82.64% |
| Logistic | T20 | 79.93% |
| Logistic | ODI | 81.33% |

---

## Docs

- [docs/HANDOFF.md](docs/HANDOFF.md) — current state, agent log, key files
- [docs/progress.md](docs/progress.md) — phase completion checklist
- [docs/architecture.md](docs/architecture.md) — system design
- [docs/decisions.md](docs/decisions.md) — technical decisions log
