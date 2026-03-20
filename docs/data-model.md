# Data Model — CricketIQ SQLite Schema

## Tables

### `matches`
One row per match.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| match_type | TEXT | "T20", "ODI", "Test" |
| team1 | TEXT | First team (canonical name) |
| team2 | TEXT | Second team |
| venue | TEXT | Stadium name |
| date | TEXT | YYYY-MM-DD |
| toss_winner | TEXT | Team that won toss |
| toss_decision | TEXT | "bat" or "field" |
| winner | TEXT | Winning team (NULL if no result) |
| result_margin | INTEGER | Runs or wickets |
| result_type | TEXT | "runs" or "wickets" |
| source_file | TEXT UNIQUE | Cricsheet filename (prevents duplicates) |

---

### `player_match_stats`
One row per player per innings per match.

| Column | Type | Description |
|--------|------|-------------|
| match_id | INTEGER FK | References matches.id |
| player_name | TEXT | Cricsheet player name |
| team | TEXT | Player's team in this match |
| innings | INTEGER | 1 or 2 |
| runs | INTEGER | Runs scored |
| balls_faced | INTEGER | Balls faced |
| fours | INTEGER | Boundaries scored |
| sixes | INTEGER | Sixes scored |
| dismissed | INTEGER | 1 if out, 0 if not out |
| overs_bowled | REAL | Overs bowled (decimal) |
| runs_conceded | INTEGER | Runs given while bowling |
| wickets | INTEGER | Wickets taken |
| dot_balls | INTEGER | Dot balls bowled |

---

### `elo_ratings`
Current Elo rating per team per format.

| Column | Type | Description |
|--------|------|-------------|
| team_name | TEXT | Canonical team name |
| match_type | TEXT | "T20", "ODI", "Test" |
| elo | REAL | Current Elo (starts at 1500) |
| last_updated | TEXT | ISO timestamp |

---

### `player_ratings`
Computed player ratings (refreshed after new data).

| Column | Type | Description |
|--------|------|-------------|
| player_name | TEXT | Player name |
| match_type | TEXT | Format |
| batting_rating | REAL | 0–100 batting score |
| bowling_rating | REAL | 0–100 bowling score |
| overall_rating | REAL | 0–100 combined |
| form_score | REAL | 0–100 recent form |
| consistency | REAL | 0–100 (lower std_dev = higher) |
| games_played | INTEGER | Total innings + bowling appearances |
| last_updated | TEXT | ISO timestamp |

---

## Key Relationships

```
matches (1) ──────── (N) player_match_stats
                              │
                              ▼
                    player_ratings (computed)
                    elo_ratings (computed)
```

## Notes

- Player names use Cricsheet format exactly (e.g. "V Kohli" in some datasets, "Virat Kohli" in others)
- Team names are normalized via `data/normalization.py`
- `player_ratings` and `elo_ratings` are derived/computed — can be recomputed anytime
