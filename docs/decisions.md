# Decisions Log — CricketIQ

Record every significant architectural decision here.
Format: date | decision | reason | alternatives considered

---

## 2026-03-20 | Use Cricsheet as data source

**Decision:** Use Cricsheet (free JSON downloads) instead of paid APIs.

**Reason:**
- No API key required for MVP
- Comprehensive historical data (IPL, T20I, ODI, Test)
- Ball-by-ball granularity — enables rich feature engineering
- Completely free

**Alternatives considered:**
- CricAPI (paid, ~$30/month)
- ESPN Cricinfo scraping (fragile, may break)
- Kaggle datasets (stale, less granular)

---

## 2026-03-20 | SQLite over PostgreSQL

**Decision:** Use SQLite for MVP.

**Reason:**
- No server setup required
- Single file database — easy to back up and inspect
- More than sufficient for local prediction engine
- Can migrate to PostgreSQL later if needed

**Migration path:** `data/db.py` abstracts connection — change DB_PATH to pg:// when ready.

---

## 2026-03-20 | 4-layer ensemble prediction

**Decision:** Use Elo + Logistic + XGBoost + Monte Carlo in ensemble.

**Reason:**
- Each layer captures different signal
- Ensemble reduces variance of any single model
- Progressive complexity — Elo works even with minimal data

**Layer purpose:**
- Elo: fast baseline using team history
- Logistic: linear feature relationships
- XGBoost: non-linear interactions
- Monte Carlo: simulates player-level variance

---

## 2026-03-20 | OpenRouter for LLM reports

**Decision:** Use OpenRouter (not direct OpenAI/Anthropic).

**Reason:**
- Single API key for multiple providers
- Can swap models cheaply
- Falls back gracefully if key not set

---

## 2026-03-20 | CLI first, Telegram second

**Decision:** Build test_cli.py before Telegram bot.

**Reason:**
- Faster iteration — no bot setup overhead
- Easier to debug prediction logic locally
- Same prediction functions will be reused in bot

---
