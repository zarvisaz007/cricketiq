"""
ratings/player_ratings.py
Computes and stores player ratings using the CricketIQ formula.

Batting Rating =
    0.40 * normalized_average
    + 0.30 * normalized_strike_rate
    + 0.20 * recent_form
    + 0.10 * consistency

Bowling Rating =
    0.35 * normalized_economy (inverted)
    + 0.30 * normalized_bowling_sr (inverted)
    + 0.20 * normalized_average (inverted)
    + 0.15 * recent_form

With Bayesian smoothing: blend with prior of 50 when few games played.
"""
import sys
import os
from datetime import datetime
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection
from features.player_features import get_batting_stats, get_bowling_stats, get_recent_form

# Bayesian prior: shrink toward 50 when few games
PRIOR_STRENGTH = 10  # equivalent to N games at rating 50


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to 0-100 range."""
    if max_val == min_val:
        return 50.0
    return max(0, min(100, (value - min_val) / (max_val - min_val) * 100))


def compute_batting_rating(player_name: str, match_type: str) -> float:
    stats = get_batting_stats(player_name, match_type)
    form = get_recent_form(player_name, match_type)

    if stats["innings"] < 3:
        return _bayesian_smooth(50.0, stats["innings"])

    # Normalize components (using reasonable cricket benchmarks)
    avg_score = _normalize(stats["average"], 0, 60)         # 60 avg = 100 score
    sr_score = _normalize(stats["strike_rate"], 60, 200)    # 200 sr = 100 score
    consistency = _normalize(max(0, 100 - stats["std_dev"]), 0, 100)  # lower std = more consistent

    raw_rating = (
        avg_score * 0.40 +
        sr_score * 0.30 +
        form * 0.20 +
        consistency * 0.10
    )

    return round(_bayesian_smooth(raw_rating, stats["innings"]), 2)


def compute_bowling_rating(player_name: str, match_type: str) -> float:
    stats = get_bowling_stats(player_name, match_type)
    form = get_recent_form(player_name, match_type)

    if stats["matches"] < 3 or stats["total_wickets"] < 2:
        return _bayesian_smooth(50.0, stats["matches"])

    # Lower economy / bowling_sr / average = better → invert scores
    econ_score = _normalize(max(0, 15 - stats["economy"]), 0, 10)     # 5.0 econ = 100
    bsr_score = _normalize(max(0, 50 - stats["bowling_strike_rate"]), 0, 40)  # 10 bsr = 100
    bavg_score = _normalize(max(0, 80 - stats["bowling_average"]), 0, 70)     # 10 avg = 100

    raw_rating = (
        econ_score * 0.35 +
        bsr_score * 0.30 +
        bavg_score * 0.20 +
        form * 0.15
    )

    return round(_bayesian_smooth(raw_rating, stats["matches"]), 2)


def compute_overall_rating(batting: float, bowling: float,
                            batting_innings: int, bowling_matches: int) -> float:
    """Combine batting and bowling into overall rating."""
    is_batter = batting_innings >= 5
    is_bowler = bowling_matches >= 5

    if is_batter and is_bowler:
        return round(batting * 0.5 + bowling * 0.5, 2)
    elif is_batter:
        return batting
    elif is_bowler:
        return bowling
    return 50.0


def _bayesian_smooth(raw: float, n: int) -> float:
    """Bayesian smoothing: blend raw rating with prior of 50."""
    return (raw * n + 50.0 * PRIOR_STRENGTH) / (n + PRIOR_STRENGTH)


def update_all_ratings(match_type: str):
    """Compute and store ratings for all players in the given format."""
    conn = get_connection()

    players = conn.execute("""
        SELECT DISTINCT pms.player_name
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE m.match_type = ?
    """, (match_type,)).fetchall()
    conn.close()

    print(f"[Ratings/{match_type}] Computing for {len(players)} players...")

    conn = get_connection()
    updated = 0
    for row in players:
        name = row["player_name"]
        batting = compute_batting_rating(name, match_type)
        bowling = compute_bowling_rating(name, match_type)

        b_stats = get_batting_stats(name, match_type)
        bw_stats = get_bowling_stats(name, match_type)
        overall = compute_overall_rating(batting, bowling, b_stats["innings"], bw_stats["matches"])
        form = get_recent_form(name, match_type)

        conn.execute("""
            INSERT INTO player_ratings
                (player_name, match_type, batting_rating, bowling_rating, overall_rating,
                 form_score, consistency, games_played, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_name, match_type) DO UPDATE SET
                batting_rating = excluded.batting_rating,
                bowling_rating = excluded.bowling_rating,
                overall_rating = excluded.overall_rating,
                form_score = excluded.form_score,
                games_played = excluded.games_played,
                last_updated = excluded.last_updated
        """, (name, match_type, batting, bowling, overall, form,
              max(0, 100 - get_batting_stats(name, match_type)["std_dev"]),
              b_stats["innings"] + bw_stats["matches"],
              datetime.now().isoformat()))
        updated += 1

    conn.commit()
    conn.close()
    print(f"[Ratings/{match_type}] Updated {updated} player ratings.")


def get_player_rating(player_name: str, match_type: str) -> dict:
    """Fetch stored rating for a player."""
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM player_ratings WHERE player_name = ? AND match_type = ?
    """, (player_name, match_type)).fetchone()
    conn.close()

    if row:
        return dict(row)
    return {
        "player_name": player_name, "match_type": match_type,
        "batting_rating": 50.0, "bowling_rating": 50.0,
        "overall_rating": 50.0, "form_score": 50.0,
        "consistency": 50.0, "games_played": 0,
    }


def get_top_players(match_type: str, n: int = 20, role: str = "overall") -> list:
    """Returns top N players by rating."""
    rating_col = {
        "batting": "batting_rating",
        "bowling": "bowling_rating",
    }.get(role, "overall_rating")

    conn = get_connection()
    rows = conn.execute(f"""
        SELECT player_name, batting_rating, bowling_rating, overall_rating,
               form_score, games_played
        FROM player_ratings
        WHERE match_type = ? AND games_played >= 5
        ORDER BY {rating_col} DESC
        LIMIT ?
    """, (match_type, n)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    for fmt in ["T20", "ODI", "Test"]:
        update_all_ratings(fmt)
