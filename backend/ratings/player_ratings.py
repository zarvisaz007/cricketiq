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
                            batting_innings: int, bowling_matches: int,
                            total_wickets: int = 0) -> float:
    """Combine batting and bowling into overall rating."""
    is_batter = batting_innings >= 5
    # Require meaningful wickets to avoid dragging specialist batters down
    is_bowler = bowling_matches >= 10 and total_wickets >= 10

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


def _batting_from_rows(rows: list) -> dict:
    """Compute batting stats from pre-fetched row dicts."""
    import numpy as np
    bat = [r for r in rows if r["balls_faced"] > 0]
    if not bat:
        return {"innings": 0, "total_runs": 0, "average": 0, "strike_rate": 0,
                "dismissals": 0, "std_dev": 0, "highest": 0}
    total_runs = sum(r["runs"] for r in bat)
    total_balls = sum(r["balls_faced"] for r in bat)
    dismissals = sum(r["dismissed"] for r in bat)
    scores = [r["runs"] for r in bat]
    return {
        "innings": len(bat),
        "total_runs": total_runs,
        "average": round(total_runs / dismissals if dismissals > 0 else total_runs, 2),
        "strike_rate": round(total_runs / total_balls * 100 if total_balls > 0 else 0, 2),
        "dismissals": dismissals,
        "std_dev": round(float(np.std(scores)) if len(scores) > 1 else 0, 2),
        "highest": max(scores),
    }


def _bowling_from_rows(rows: list) -> dict:
    """Compute bowling stats from pre-fetched row dicts."""
    bowl = [r for r in rows if r["overs_bowled"] > 0]
    if not bowl:
        return {"matches": 0, "total_wickets": 0, "total_overs": 0,
                "economy": 0, "bowling_average": 0, "bowling_strike_rate": 0}
    total_overs = sum(r["overs_bowled"] for r in bowl)
    total_runs = sum(r["runs_conceded"] for r in bowl)
    total_wickets = sum(r["wickets"] for r in bowl)
    total_balls = total_overs * 6
    return {
        "matches": len(bowl),
        "total_wickets": total_wickets,
        "total_overs": round(total_overs, 1),
        "economy": round(total_runs / total_overs if total_overs > 0 else 0, 2),
        "bowling_average": round(total_runs / total_wickets if total_wickets > 0 else 999, 2),
        "bowling_strike_rate": round(total_balls / total_wickets if total_wickets > 0 else 999, 2),
    }


def _form_from_rows(bat_rows: list, bowl_rows: list) -> float:
    """Compute form score from last-N rows."""
    bat = _batting_from_rows(bat_rows)
    bowl = _bowling_from_rows(bowl_rows)
    score = 50.0
    if bat["innings"] > 0:
        avg_score = min(bat["average"] / 50 * 70, 100)
        sr_score = min(bat["strike_rate"] / 150 * 70, 100)
        score = avg_score * 0.5 + sr_score * 0.5
    elif bowl["matches"] > 0:
        econ_score = max(0, 100 - bowl["economy"] * 8)
        wick_score = min(bowl["total_wickets"] / bowl["matches"] * 40, 100)
        score = econ_score * 0.5 + wick_score * 0.5
    return round(min(max(score, 0), 100), 2)


def _batting_rating_from_stats(b_stats: dict, form: float) -> float:
    if b_stats["innings"] < 3:
        return _bayesian_smooth(50.0, b_stats["innings"])
    avg_score = _normalize(b_stats["average"], 0, 60)
    sr_score = _normalize(b_stats["strike_rate"], 60, 200)
    consistency = _normalize(max(0, 100 - b_stats["std_dev"]), 0, 100)
    raw = avg_score * 0.40 + sr_score * 0.30 + form * 0.20 + consistency * 0.10
    return round(_bayesian_smooth(raw, b_stats["innings"]), 2)


def _bowling_rating_from_stats(bw_stats: dict, form: float) -> float:
    if bw_stats["matches"] < 3 or bw_stats["total_wickets"] < 2:
        return _bayesian_smooth(50.0, bw_stats["matches"])
    econ_score = _normalize(max(0, 15 - bw_stats["economy"]), 0, 10)
    bsr_score = _normalize(max(0, 50 - bw_stats["bowling_strike_rate"]), 0, 40)
    bavg_score = _normalize(max(0, 80 - bw_stats["bowling_average"]), 0, 70)
    raw = econ_score * 0.35 + bsr_score * 0.30 + bavg_score * 0.20 + form * 0.15
    return round(_bayesian_smooth(raw, bw_stats["matches"]), 2)


def update_all_ratings(match_type: str):
    """Compute and store ratings for all players in the given format.
    Batch version: loads all data in one query to avoid N+1 DB round-trips.
    """
    from collections import defaultdict

    conn = get_connection()
    rows = conn.execute("""
        SELECT pms.player_name,
               pms.runs, pms.balls_faced, pms.dismissed,
               pms.overs_bowled, pms.runs_conceded, pms.wickets, pms.dot_balls,
               m.date
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE m.match_type = ?
          AND m.gender = 'male'
        ORDER BY pms.player_name, m.date DESC
    """, (match_type,)).fetchall()
    conn.close()

    # Group rows by player (already ordered by date DESC per player)
    player_rows = defaultdict(list)
    for r in rows:
        player_rows[r["player_name"]].append(dict(r))

    print(f"[Ratings/{match_type}] Computing for {len(player_rows)} players...")

    records = []
    now = datetime.now().isoformat()
    for name, prows in player_rows.items():
        b_stats = _batting_from_rows(prows)
        bw_stats = _bowling_from_rows(prows)
        form = _form_from_rows(prows[:10], prows[:10])
        batting = _batting_rating_from_stats(b_stats, form)
        bowling = _bowling_rating_from_stats(bw_stats, form)
        overall = compute_overall_rating(batting, bowling, b_stats["innings"], bw_stats["matches"],
                                          total_wickets=bw_stats["total_wickets"])
        consistency = max(0, 100 - b_stats["std_dev"])
        games_played = b_stats["innings"] + bw_stats["matches"]
        records.append((name, match_type, batting, bowling, overall, form,
                        consistency, games_played, now))

    conn = get_connection()
    conn.executemany("""
        INSERT INTO player_ratings
            (player_name, match_type, batting_rating, bowling_rating, overall_rating,
             form_score, consistency, games_played, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_name, match_type) DO UPDATE SET
            batting_rating = excluded.batting_rating,
            bowling_rating = excluded.bowling_rating,
            overall_rating = excluded.overall_rating,
            form_score = excluded.form_score,
            consistency = excluded.consistency,
            games_played = excluded.games_played,
            last_updated = excluded.last_updated
    """, records)
    conn.commit()
    conn.close()
    print(f"[Ratings/{match_type}] Updated {len(records)} player ratings.")


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
