"""
features/player_features.py
Computes raw player statistics from the database.
These are used by the ratings module and ML models.
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection


def get_batting_stats(player_name: str, match_type: str, last_n: int = None) -> dict:
    """
    Returns batting statistics for a player.
    last_n: only use last N innings (None = all time)
    """
    conn = get_connection()

    base_query = """
        SELECT pms.runs, pms.balls_faced, pms.dismissed, pms.fours, pms.sixes,
               m.date
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ?
          AND m.match_type = ?
          AND m.gender = 'male'
          AND pms.balls_faced > 0
        ORDER BY m.date DESC
    """
    params = [player_name, match_type]
    if last_n:
        base_query += f" LIMIT {last_n}"

    rows = conn.execute(base_query, params).fetchall()
    conn.close()

    if not rows:
        return _empty_batting_stats()

    total_runs = sum(r["runs"] for r in rows)
    total_balls = sum(r["balls_faced"] for r in rows)
    dismissals = sum(r["dismissed"] for r in rows)
    innings = len(rows)

    average = total_runs / dismissals if dismissals > 0 else total_runs
    strike_rate = (total_runs / total_balls * 100) if total_balls > 0 else 0

    # Individual innings scores for consistency
    scores = [r["runs"] for r in rows]
    import numpy as np
    std_dev = float(np.std(scores)) if len(scores) > 1 else 0

    return {
        "innings": innings,
        "total_runs": total_runs,
        "average": round(average, 2),
        "strike_rate": round(strike_rate, 2),
        "dismissals": dismissals,
        "std_dev": round(std_dev, 2),
        "highest": max(scores),
        "fifties": sum(1 for s in scores if 50 <= s < 100),
        "hundreds": sum(1 for s in scores if s >= 100),
    }


def get_bowling_stats(player_name: str, match_type: str, last_n: int = None) -> dict:
    """Returns bowling statistics for a player."""
    conn = get_connection()

    query = """
        SELECT pms.overs_bowled, pms.runs_conceded, pms.wickets, pms.dot_balls,
               m.date
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ?
          AND m.match_type = ?
          AND m.gender = 'male'
          AND pms.overs_bowled > 0
        ORDER BY m.date DESC
    """
    if last_n:
        query += f" LIMIT {last_n}"

    rows = conn.execute(query, [player_name, match_type]).fetchall()
    conn.close()

    if not rows:
        return _empty_bowling_stats()

    total_overs = sum(r["overs_bowled"] for r in rows)
    total_runs = sum(r["runs_conceded"] for r in rows)
    total_wickets = sum(r["wickets"] for r in rows)
    total_dots = sum(r["dot_balls"] for r in rows)
    total_balls = total_overs * 6

    economy = (total_runs / total_overs) if total_overs > 0 else 0
    bowling_avg = (total_runs / total_wickets) if total_wickets > 0 else 999
    bowling_sr = (total_balls / total_wickets) if total_wickets > 0 else 999
    dot_pct = (total_dots / total_balls * 100) if total_balls > 0 else 0

    return {
        "matches": len(rows),
        "total_wickets": total_wickets,
        "total_overs": round(total_overs, 1),
        "economy": round(economy, 2),
        "bowling_average": round(bowling_avg, 2),
        "bowling_strike_rate": round(bowling_sr, 2),
        "dot_pct": round(dot_pct, 2),
        "five_wickets": sum(1 for r in rows if r["wickets"] >= 5),
    }


def get_recent_form(player_name: str, match_type: str, n: int = 10) -> float:
    """
    Returns a form score (0-100) based on last N performances.
    Weighted: more recent = more weight.
    """
    batting = get_batting_stats(player_name, match_type, last_n=n)
    bowling = get_bowling_stats(player_name, match_type, last_n=n)

    score = 50.0  # default neutral

    if batting["innings"] > 0:
        # Normalize: avg 35 = score 60, sr 130 = score 60 (T20 context)
        avg_score = min(batting["average"] / 50 * 70, 100)
        sr_score = min(batting["strike_rate"] / 150 * 70, 100)
        score = avg_score * 0.5 + sr_score * 0.5

    elif bowling["matches"] > 0:
        # Economy: lower is better. 7.0 econ = score 60
        econ_score = max(0, 100 - bowling["economy"] * 8)
        wick_score = min(bowling["total_wickets"] / bowling["matches"] * 40, 100)
        score = econ_score * 0.5 + wick_score * 0.5

    return round(min(max(score, 0), 100), 2)


def get_player_role(player_name: str, match_type: str) -> str:
    """Infers player role from their stats."""
    batting = get_batting_stats(player_name, match_type)
    bowling = get_bowling_stats(player_name, match_type)

    is_batter = batting["innings"] >= 5
    is_bowler = bowling["matches"] >= 5 and bowling["total_wickets"] >= 5

    if is_batter and is_bowler:
        return "allrounder"
    elif is_batter:
        return "batsman"
    elif is_bowler:
        return "bowler"
    return "unknown"


def _empty_batting_stats() -> dict:
    return {"innings": 0, "total_runs": 0, "average": 0, "strike_rate": 0,
            "dismissals": 0, "std_dev": 0, "highest": 0, "fifties": 0, "hundreds": 0}


def _empty_bowling_stats() -> dict:
    return {"matches": 0, "total_wickets": 0, "total_overs": 0, "economy": 0,
            "bowling_average": 0, "bowling_strike_rate": 0, "dot_pct": 0, "five_wickets": 0}
