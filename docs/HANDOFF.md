# HANDOFF.md — CricketIQ

> You are an AI agent. Read this file fully for project context.
> Then read docs/progress.md for task status.

---

## PROJECT SNAPSHOT

**What it is:**
CricketIQ is an AI-powered cricket prediction engine with a Telegram bot frontend. 4 ML models (Elo, Logistic Regression, XGBoost, Monte Carlo), 28 features, Dream11 fantasy optimizer, IPL analytics, live Cricbuzz scores. Menu-driven bot with rich formatting, 1-tap predictions, full IPL hub.

**Current state:** All 8 phases complete. Bot fully functional locally. Deployment pending.

**Tech:** Python 3.10+ | SQLite | XGBoost | scikit-learn | PuLP | python-telegram-bot | Cricbuzz scraping

**Key files:**

| File | Purpose |
|------|---------|
| `bot/main.py` | Bot entry — registers handlers, starts pollers |
| `frontend/bot/handlers_menu.py` | Main menu, /start, back navigation dispatch |
| `frontend/bot/handlers_predict.py` | 4-model ensemble predictions |
| `frontend/bot/handlers_ipl.py` | Full IPL hub (13 handlers) |
| `frontend/bot/keyboards.py` | All inline keyboard builders |
| `frontend/bot/formatters.py` | Rich text formatters (user-friendly) |
| `backend/scrapers/cricbuzz_schedule.py` | Upcoming matches scraper |
| `backend/scrapers/cricbuzz_live.py` | Live scores scraper |
| `backend/fantasy/team_selector.py` | Dream11 PuLP optimizer |
| `backend/features/ipl_season.py` | IPL points table + playoff sim |
| `database/db.py` | SQLite connection + migrations |

**Commands:**

| Command | Does |
|---------|------|
| `make bot` | Start Telegram bot (needs TELEGRAM_BOT_TOKEN in .env) |
| `make setup` | Full pipeline: install → db → download → ingest → train |
| `make train` | Retrain all models |
| `make migrate` | Run all DB migrations |
| `make schedule` | Scrape upcoming matches |
| `make live` | Live score poller standalone |
| `make reset` | Wipe DB and restart |

**Folder map:**
```
bot/             ← main.py entry point
frontend/bot/    ← keyboards, formatters, 10 handler modules
backend/         ← models, features, ratings, simulation, fantasy, scrapers
database/        ← db.py, migrations/
scripts/         ← orchestrator, setup_db, download_data
docs/            ← this file + progress, memory, architecture
```

---

## TASK QUEUE

### Completed

- [x] Phase 0: Project setup
- [x] Phase 1: Data layer (9351 matches from Cricsheet)
- [x] Phase 2: Ratings (6559 player ratings, Elo for all teams)
- [x] Phase 3: Models (XGBoost T20: 86.50%, Logistic T20: 79.93%)
- [x] Phase 4: CLI testing (all 8 options verified)
- [x] Phase 5: Telegram bot v1 (7 ConversationHandlers)
- [x] Phase 6: v2 core (28 features, IPL predictor, Dream11, live scraper)
- [x] Phase 7: Bot overhaul (14 new files, modular handlers, 3 pollers)
- [x] Phase 8: UX overhaul (persistent menu, back button, rich formatting, full IPL hub)

### Pending

- [ ] Deploy to Railway or DigitalOcean

---

## NOTES FOR AGENTS

- Player names must match Cricsheet format (e.g. "V Kohli", "JJ Bumrah")
- match_type must be exactly "T20", "ODI", or "Test"
- Gender filter applied everywhere — `gender='male'`
- Callback data must stay under 64 bytes (Telegram limit)
- Telegram 4096 char limit — use _split_message() for long responses
- Backend calls must use `asyncio.to_thread()` — never block the bot event loop
- sys.path manipulation at top of each frontend file for backend imports
- SQLite file: database/cricketiq.db
- Bot token: .env as TELEGRAM_BOT_TOKEN

---

## AGENT LOG

_Most recent entry first._

| Date | Task | Result |
|------|------|--------|
| 2026-03-26 | UX overhaul | Persistent "/" menu, back button dispatch table, rich match reports, user-friendly formatting, full IPL hub (8 new handlers), cross-agent consistency fixes |
| 2026-03-26 | Bot overhaul | 14 new files: keyboards, formatters, 10 handler modules. Modular architecture. 3 background pollers. 7 commands + 30+ callback handlers |
| 2026-03-21 | Telegram bot v1 | 7 ConversationHandlers, inline keyboards, asyncio.to_thread for blocking calls |
| 2026-03-21 | CLI v2 overhaul | Hierarchical navigation, player profiles with last 10 innings, team selectors |
| 2026-03-21 | Phase 3+4 complete | All models trained + verified. XGBoost T20: 86.50%. All 8 CLI options working |
| 2026-03-21 | Phase 1+2 complete | 9351 matches ingested. 6559 player ratings. Elo built. Gender filter added |
| 2026-03-20 | Project initialized | All files created, structure organized |

---

## Last Updated

2026-03-26
