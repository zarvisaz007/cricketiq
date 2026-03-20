# API Contract — Internal Module Interfaces

All modules communicate through these defined interfaces.
Agents must NOT bypass these contracts.

---

## Match Prediction

**Input:**
```python
predict_match(
    team1: str,       # e.g. "India"
    team2: str,       # e.g. "Australia"
    match_type: str,  # "T20" | "ODI" | "Test"
    venue: str,       # e.g. "Wankhede Stadium" (optional)
    toss_winner: str  # team name (optional)
) -> dict
```

**Output:**
```python
{
    "team1": "India",
    "team2": "Australia",
    "final_prob": 63.5,        # P(team1 wins) as percentage
    "team2_prob": 36.5,
    "confidence": "High",      # "High" | "Medium" | "Low"
    "elo_prob": 61.2,
    "lr_prob": 64.0,
    "xgb_prob": 65.1,
    "mc_prob": 63.7,
    "strength_diff": 8.4,
}
```

---

## Player Rating

**Input:**
```python
get_player_rating(
    player_name: str,
    match_type: str
) -> dict
```

**Output:**
```python
{
    "player_name": "Virat Kohli",
    "match_type": "T20",
    "batting_rating": 88.5,
    "bowling_rating": 40.0,
    "overall_rating": 88.5,
    "form_score": 91.2,
    "consistency": 82.0,
    "games_played": 120,
}
```

---

## PVOR

**Input:**
```python
compute_pvor(
    player_name: str,
    team: str,
    opponent: str,
    match_type: str
) -> dict
```

**Output:**
```python
{
    "player": "Jasprit Bumrah",
    "team": "India",
    "opponent": "Australia",
    "win_with": 64.2,
    "win_without": 58.9,
    "pvor": 5.3,
    "impact_label": "Elite",
}
```

---

## Monte Carlo

**Input:**
```python
simulate_match(
    team1: str,
    team2: str,
    match_type: str,
    n_simulations: int = 2000
) -> dict
```

**Output:**
```python
{
    "team1": "India",
    "team2": "Australia",
    "team1_win_pct": 63.5,
    "team2_win_pct": 36.5,
    "confidence": "High",
    "simulations": 2000,
}
```

---

## Rules

- All probabilities are percentages (0–100), not decimals (0–1), in output dicts.
- player_name must exactly match the name in the SQLite database (Cricsheet format).
- match_type must be exactly: "T20", "ODI", or "Test" (capital T/O).
- Functions must not raise exceptions on missing data — return sensible defaults.
