# Architecture — CricketIQ

## System Flow

```
CRICSHEET DATA (JSON files)
        │
        ▼
[data/ingestion.py]        ← Parse match + player stats
        │
        ▼
[SQLite Database]          ← Store raw data
        │
        ├──► [ratings/player_ratings.py]   ← Compute batting/bowling ratings
        │            │
        │            ▼
        │    [player_ratings table]        ← Cached ratings
        │
        ├──► [models/elo.py]               ← Build team Elo ratings
        │            │
        │            ▼
        │    [elo_ratings table]
        │
        ├──► [features/team_features.py]   ← Team strength, H2H, venue
        │
        └──► [features/player_features.py] ← Per-player stats
                     │
                     ▼
         ┌──────────────────────────────┐
         │   PREDICTION PIPELINE        │
         │                              │
         │  [models/elo.py]             │  Layer 1: Elo win probability
         │  [models/logistic.py]        │  Layer 2: Logistic regression
         │  [models/xgboost_model.py]   │  Layer 3: XGBoost
         │  [simulation/monte_carlo.py] │  Layer 4: Monte Carlo (2000 runs)
         │                              │
         │  Ensemble → Final Prediction │
         └──────────────────────────────┘
                     │
                     ├──► [impact/pvor.py]            ← Player impact scores
                     │
                     └──► [nlp/report_generator.py]   ← LLM reports via OpenRouter
                                  │
                                  ▼
                        [test_cli.py]                 ← User interface (MVP)
                        [bot/]                        ← Telegram bot (post-MVP)
```

## Key Design Decisions

1. **SQLite for MVP** — no server needed, runs locally, easy to inspect
2. **Cricsheet as data source** — free, comprehensive, no API key
3. **Layered prediction** — each layer adds accuracy, ensemble is most reliable
4. **Stateless agents** — all context lives in /docs, not in chat
5. **OpenRouter for LLM** — model-agnostic, easy to swap providers

## Data Flow Summary

```
Raw JSON → SQLite → Features → Models → Prediction → Report → User
```
