# Features — CricketIQ

Feature list only. No implementation details here.
See docs/architecture.md for how they connect.

---

## F1: Match Prediction Engine

**Status:** In Progress

- Accepts: team1, team2, match_type, venue, toss (optional)
- Outputs: win probability for each team + confidence level
- Uses 4 layers: Elo → Logistic → XGBoost → Monte Carlo
- Final result = ensemble average of all layers

---

## F2: Player Rating System

**Status:** In Progress

- Computes batting rating (avg, SR, form, consistency)
- Computes bowling rating (economy, SR, average, form)
- Applies Bayesian smoothing (small sample correction)
- Applies recency decay (recent games weighted more)
- Formats: T20, ODI, Test rated independently

---

## F3: PVOR — Player Impact Engine

**Status:** In Progress

- Measures: P(win with player) − P(win without player)
- Uses Monte Carlo simulation internally
- Returns impact score + label (Elite/High/Medium/Low)
- Can rank all players in a squad by impact

---

## F4: Player Report Engine

**Status:** In Progress

- Uses OpenRouter LLM to generate natural language reports
- Falls back to rule-based generation if no API key
- Shows: strengths, weaknesses, predicted performance range

---

## F5: Team Analysis

**Status:** In Progress

- Shows team strengths and weaknesses
- Compares recent form, squad depth, key players
- LLM-powered summary with rule-based fallback

---

## F6: Smart Alerts

**Status:** In Progress

- Triggers: on-demand or before known match events
- Alert types:
  - High-confidence match detected (>70% probability)
  - Form spike (team winning 8+ of last 10)
  - Coin-flip alert (very close match)

---

## F7: Elo Rankings

**Status:** In Progress

- Global team rankings by format
- Updated after every match ingested
- Separate rankings for T20, ODI, Test

---

## F8: Top Players Leaderboard

**Status:** In Progress

- Lists top players by overall/batting/bowling rating
- Filterable by format
- Shows form score + games played

---

## Post-MVP (Not in current scope)

- Telegram bot interface
- Live match data integration
- Web dashboard
- Match scheduler / calendar
- Historical prediction accuracy tracker
