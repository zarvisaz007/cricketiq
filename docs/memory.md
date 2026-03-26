# Memory — CricketIQ Project Context

This file is a compact summary of the entire project.
New AI sessions should read this first for fast context loading.

---

## What this project is

CricketIQ is an AI-powered cricket prediction engine with a Telegram bot frontend. It uses:
- Historical match data from Cricsheet (9351 matches: IPL + T20I + ODI)
- 4 ML models: Elo, Logistic Regression, XGBoost, Monte Carlo simulation
- 28-feature feature registry (team, player, venue, phase, IPL-specific)
- Player rating system (batting + bowling + form + consistency)
- Dream11 fantasy team optimizer (PuLP linear programming)
- IPL-specific predictor with points table + playoff simulator
- Live scores scraped from Cricbuzz
- Upcoming matches scraper with schedule/XI pollers

Output is a rich Telegram bot with menu-driven navigation, 1-tap predictions, Dream11 teams, IPL hub, player/team analysis, and live scores.

---

## Tech

- Python 3.10+
- SQLite (database/cricketiq.db) with WAL mode
- scikit-learn, xgboost, numpy, pandas, PuLP
- python-telegram-bot (async)
- Cricbuzz web scraping (BeautifulSoup + regex)
- Cricsheet ball-by-ball data (cricsheet.org)

---

## Current State

**All 8 phases complete.** Bot is fully functional locally.

- 4 ML models trained (XGBoost T20: 86.50%, ODI: 82.64%)
- 17 handler/utility files in frontend/bot/
- 3 background pollers: live (45s), schedule (6h), XI (30min)
- Persistent "/" menu with 7 commands
- Menu-driven navigation with back button dispatch
- User-friendly formatting (emojis, visual bars, plain English)

**Deployment pending** — not yet on Railway/DigitalOcean.

---

## Running

```
make bot          # Start Telegram bot (needs TELEGRAM_BOT_TOKEN in .env)
make setup        # Full first-time setup
make schedule     # Scrape upcoming matches
make live         # Live score poller standalone
make train        # Retrain all models
make migrate      # Run all DB migrations
```

---

## Key Files

| File | Purpose |
|------|---------|
| bot/main.py | Bot entry point — registers handlers, starts pollers |
| frontend/bot/keyboards.py | All inline keyboard builders |
| frontend/bot/formatters.py | Rich text formatters |
| frontend/bot/handlers_menu.py | /start, main menu, help, back navigation |
| frontend/bot/handlers_predict.py | 4-model ensemble predictions |
| frontend/bot/handlers_ipl.py | Full IPL hub (13 handlers) |
| frontend/bot/handlers_dream11.py | Dream11 team generation |
| frontend/bot/handlers_upcoming.py | Upcoming matches + rich reports |
| frontend/bot/handlers_live.py | Live scores with refresh |
| backend/scrapers/cricbuzz_schedule.py | Upcoming matches scraper |
| backend/scrapers/cricbuzz_live.py | Live scores scraper |
| backend/scrapers/schedule_poller.py | Background polling daemon |
| backend/models/ensemble.py | Weighted ensemble combiner |
| backend/fantasy/team_selector.py | Dream11 PuLP optimizer |
| backend/features/ipl_season.py | IPL points table + playoffs |
| database/db.py | SQLite connection + migrations |
| docs/progress.md | What's done and what's next |

---

## Important Constraints

- Player names must match Cricsheet format exactly
- match_type must be "T20", "ODI", or "Test" (exact case)
- Gender filter applied everywhere (gender='male')
- Callback data must stay under 64 bytes (Telegram limit) — uses numeric indices
- Telegram 4096 char message limit — handled with _split_message() chunking
- Backend calls wrapped in asyncio.to_thread() to avoid blocking

---

## Last Updated

2026-03-26 — All phases complete, bot overhaul done.
