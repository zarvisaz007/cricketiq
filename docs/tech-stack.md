# Tech Stack — CricketIQ

## Core

| Technology | Version | Why |
|------------|---------|-----|
| Python | 3.10+ | Primary language — best ML ecosystem |
| SQLite | built-in | Simple, local, no server needed for MVP |
| pandas | 2.0+ | Data manipulation |
| numpy | 1.24+ | Numerical computation, Monte Carlo sampling |

## Machine Learning

| Library | Why |
|---------|-----|
| scikit-learn | Logistic regression, preprocessing pipelines |
| xgboost | Best single model for tabular prediction |
| scipy | Statistical distributions (Gamma for MC simulation) |
| joblib | Model serialization (save/load trained models) |

## Data

| Source | Type | Content |
|--------|------|---------|
| Cricsheet | Free JSON downloads | Ball-by-ball IPL, T20I, ODI, Test data |
| No API required | — | Historical data only for MVP |

## LLM / Reports

| Service | Why |
|---------|-----|
| OpenRouter | Single API for multiple LLM providers |
| openai SDK | Compatible with OpenRouter's API format |
| Model: gpt-4o-mini | Fast, cheap, good enough for reports |

## Post-MVP (Telegram Bot)

| Library | Why |
|---------|-----|
| python-telegram-bot | Standard Telegram bot library |
| APScheduler | Scheduled smart alerts |

## Not Used (and Why)

| Technology | Why not |
|------------|---------|
| PostgreSQL | Overkill for MVP local setup |
| FastAPI | No API needed until Telegram integration |
| Docker | Unnecessary complexity for local MVP |
| Redis | No caching layer needed at this scale |
