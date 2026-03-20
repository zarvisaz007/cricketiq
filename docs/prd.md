# PRD — CricketIQ: Cricket Prediction Engine

## Product Vision

CricketIQ is a data-driven cricket prediction system for users who want actionable answers — not stats.

**Core questions answered:**
- Who will win this match?
- Why will they win?
- Which player matters most?

---

## Target Users

| User | Need |
|------|------|
| Cricket fans | Quick, reliable match predictions |
| Fantasy cricket players | Player impact scores for team selection |
| Cricket analysts | Deep player/team reports |

---

## Core Value Proposition

Most prediction systems give averages. CricketIQ gives:
- **Win probability** (not just "Team A is better")
- **PVOR** (player impact, not just player stats)
- **Confidence scores** (know when to trust the prediction)

---

## Scope (MVP)

**In scope:**
- T20, ODI, Test match prediction
- IPL + International matches
- Player rating system
- PVOR player impact engine
- Player and team reports
- Smart alerts (on-demand)
- CLI test interface (local)

**Out of scope (post-MVP):**
- Telegram bot
- Live match data
- User accounts
- Web dashboard

---

## Success Criteria

- Match prediction accuracy > 60% on held-out test set
- PVOR correctly identifies star players (Bumrah, Kohli rank in top 5)
- CLI runs end-to-end without errors after setup
- Completes prediction in < 30 seconds
