# Architecture — CricketIQ

## System Flow

```
CRICSHEET DATA (JSON files)
        │
        ▼
[data/ingestion.py]        ← Parse 9351 matches → SQLite
        │
        ▼
[SQLite Database]          ← matches, player_match_stats, elo_ratings, player_ratings, upcoming_matches
        │
        ├──► [ratings/player_ratings.py]   ← Batting + bowling + form + consistency
        ├──► [models/elo.py]               ← Team Elo ratings
        ├──► [features/feature_registry.py]← 28 features (team, player, venue, phase, IPL)
        └──► [scrapers/]                   ← Cricbuzz live + schedule scraping
                     │
                     ▼
         ┌──────────────────────────────┐
         │   PREDICTION PIPELINE        │
         │                              │
         │  [models/elo.py]         15% │  Elo win probability
         │  [models/logistic.py]    20% │  Logistic regression
         │  [models/xgboost_model]  40% │  XGBoost (most accurate)
         │  [monte_carlo.py]        25% │  2000-run simulation
         │                              │
         │  [models/ensemble.py]        │  Weighted ensemble → final %
         └──────────────────────────────┘
                     │
                     ├──► [fantasy/team_selector.py]  ← Dream11 LP optimizer (PuLP)
                     ├──► [models/ipl_predictor.py]   ← IPL-specific (6 extra features)
                     └──► [features/ipl_season.py]    ← Points table + playoff simulator
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │   TELEGRAM BOT FRONTEND  │
                     │                          │
                     │  bot/main.py             │  Entry point, handler registration
                     │  keyboards.py            │  Inline keyboard builders
                     │  formatters.py           │  Rich text formatters
                     │  handlers_menu.py        │  Navigation + /start
                     │  handlers_upcoming.py    │  Match browsing
                     │  handlers_predict.py     │  Predictions
                     │  handlers_dream11.py     │  Dream11 teams
                     │  handlers_ipl.py         │  IPL hub (13 handlers)
                     │  handlers_player.py      │  Player lookup
                     │  handlers_team.py        │  Team analysis
                     │  handlers_live.py        │  Live scores
                     │  handlers_leaderboard.py │  Rankings
                     └──────────────────────────┘
                                  │
                     ┌────────────┼────────────┐
                     │            │            │
                  Live Poller  Schedule    XI Poller
                   (45s)      Poller(6h)   (30min)
```

## Folder Map

```
bot/
  main.py                    ← Entry point: registers handlers, starts pollers, set_my_commands()

frontend/bot/
  keyboards.py               ← All inline keyboard builders (main menu, match list, IPL zone, pagination)
  formatters.py              ← Rich text formatters (predictions, Dream11, scorecards, player profiles)
  handlers_menu.py           ← /start, main menu, help, back navigation dispatch table
  handlers_upcoming.py       ← Upcoming matches browsing + rich match detail reports
  handlers_predict.py        ← 4-model ensemble predictions (1-tap + manual flow)
  handlers_dream11.py        ← Dream11 team generation
  handlers_ipl.py            ← Full IPL hub (points table, playoffs, teams, squads, players, stats)
  handlers_player.py         ← Player lookup (search by name + browse by team)
  handlers_team.py           ← Team analysis (Elo + form + squad)
  handlers_live.py           ← Live scores with refresh
  handlers_leaderboard.py    ← Elo rankings + top players
  handlers.py                ← LEGACY (kept, no longer imported)

backend/
  models/
    elo.py                   ← Elo rating system
    logistic.py              ← Logistic regression model
    xgboost_model.py         ← XGBoost model
    ipl_predictor.py         ← IPL-specific predictor (6 extra features)
    ensemble.py              ← Weighted ensemble combiner
  simulation/
    monte_carlo.py           ← 2000-run match simulation
  features/
    feature_registry.py      ← 28 features registered
    team_features.py         ← Team strength, H2H, form
    player_features.py       ← Player batting/bowling stats
    ipl_features.py          ← IPL-specific features
    ipl_season.py            ← Points table + playoff simulator
    venue_features.py        ← Venue analysis
    phase_features.py        ← Match phase features
  ratings/
    player_ratings.py        ← Composite batting+bowling+form+consistency rating
  fantasy/
    team_selector.py         ← PuLP LP optimizer for Dream11
  scrapers/
    cricbuzz_live.py         ← Live scores scraper
    cricbuzz_schedule.py     ← Upcoming matches + playing XI scraper
    schedule_poller.py       ← Background polling daemon (6h schedule, 30min XI)
    live_poller.py           ← Live score poller (45s)
    http_client.py           ← Rate-limited HTTP client with UA rotation

database/
  db.py                      ← SQLite connection + init + migrate_db()
  migrations/
    001_schema_v2.py         ← 9 tables + columns + 21 indices
    002_upcoming_matches.py  ← upcoming_matches table

scripts/
  orchestrator.py            ← Automated pipeline runner
  setup_db.py                ← Database initialization
  download_data.py           ← Cricsheet data downloader
```

## Key Design Patterns

### Callback Data Schema
All Telegram callbacks use `prefix|param` format, staying under 64 bytes:
- `predict_match|{cricbuzz_id}` — predict from upcoming match
- `d11_match|{cricbuzz_id}` — Dream11 from upcoming match
- `ipl_td|{index}` — IPL team detail (numeric index into user_data list)
- `pl_profile|{index}` — Player profile (numeric index)

### Navigation Stack
`context.user_data["nav_stack"]` stores breadcrumb trail. `back_callback()` pops the stack and dispatches to the correct handler via the `ROUTES` dict in handlers_menu.py. Lazy imports in route dispatchers prevent circular dependencies.

### Async Pattern
All blocking backend calls (DB queries, ML inference, web scraping) wrapped in `asyncio.to_thread()` to keep the bot responsive.

### Message Splitting
Telegram enforces 4096 char limit. `_split_message()` does line-aware chunking — never breaks mid-line.

### Background Pollers
Three daemon threads with `threading.Event` for clean shutdown:
- **Live poller** (45s) — scrapes Cricbuzz live scores
- **Schedule poller** (6h) — scrapes upcoming matches
- **XI poller** (30min) — scrapes playing XI for matches starting within 2 hours

---

## Last Updated

2026-03-26
