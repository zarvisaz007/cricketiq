"""
fantasy/expected_points.py
Predict expected Dream11 fantasy points per player based on historical performance.
"""
import sys
import os
import math
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection
from fantasy.dream11_scoring import calculate_total_fantasy_points


def get_expected_fantasy_points(player_name: str, match_type: str = "T20",
                                 last_n: int = 10, venue: str = None) -> dict:
    """
    Calculate expected fantasy points for a player based on recent performances.
    Uses exponential decay weighting on recent matches.
    """
    conn = get_connection()

    # Get recent match stats
    rows = conn.execute("""
        SELECT pms.runs, pms.balls_faced, pms.fours, pms.sixes, pms.dismissed,
               pms.wickets, pms.overs_bowled, pms.runs_conceded, pms.dot_balls,
               pms.catches, pms.stumpings, pms.batting_position,
               m.date, m.venue
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ? AND m.match_type = ? AND m.gender = 'male'
        ORDER BY m.date DESC LIMIT ?
    """, (player_name, match_type, last_n)).fetchall()
    conn.close()

    if not rows:
        return {
            "player": player_name,
            "expected_points": 20.0,  # neutral default
            "batting_points": 10.0,
            "bowling_points": 5.0,
            "fielding_points": 5.0,
            "matches_used": 0,
            "consistency": 0.0,
        }

    total_w = 0.0
    weighted_points = 0.0
    weighted_bat = 0.0
    weighted_bowl = 0.0
    weighted_field = 0.0
    all_points = []

    for i, r in enumerate(rows):
        w = math.exp(-0.1 * i)

        # Venue bonus: weight matches at same venue higher
        if venue and r["venue"] and venue.lower() in r["venue"].lower():
            w *= 1.3

        is_top_order = (r["batting_position"] or 5) <= 4
        fp = calculate_total_fantasy_points(
            runs=r["runs"], balls=r["balls_faced"],
            fours=r["fours"], sixes=r["sixes"],
            dismissed=bool(r["dismissed"]),
            wickets=r["wickets"], overs=r["overs_bowled"],
            runs_conceded=r["runs_conceded"],
            dot_balls=r["dot_balls"],
            catches=r["catches"] or 0,
            stumpings=r["stumpings"] or 0,
            is_batter=is_top_order,
        )
        all_points.append(fp)

        from fantasy.dream11_scoring import (calculate_batting_points,
                                              calculate_bowling_points,
                                              calculate_fielding_points)
        bat_pts = calculate_batting_points(r["runs"], r["balls_faced"],
                                           r["fours"], r["sixes"],
                                           bool(r["dismissed"]), is_top_order)
        bowl_pts = calculate_bowling_points(r["wickets"], r["overs_bowled"],
                                            r["runs_conceded"], r["dot_balls"])
        field_pts = calculate_fielding_points(r["catches"] or 0, r["stumpings"] or 0)

        weighted_points += fp * w
        weighted_bat += bat_pts * w
        weighted_bowl += bowl_pts * w
        weighted_field += field_pts * w
        total_w += w

    expected = weighted_points / total_w if total_w > 0 else 20.0
    exp_bat = weighted_bat / total_w if total_w > 0 else 10.0
    exp_bowl = weighted_bowl / total_w if total_w > 0 else 5.0
    exp_field = weighted_field / total_w if total_w > 0 else 5.0

    # Consistency: lower std = more consistent
    import numpy as np
    consistency = 100 - min(float(np.std(all_points)), 50) * 2 if len(all_points) > 1 else 50.0

    return {
        "player": player_name,
        "expected_points": round(expected, 1),
        "batting_points": round(exp_bat, 1),
        "bowling_points": round(exp_bowl, 1),
        "fielding_points": round(exp_field, 1),
        "matches_used": len(rows),
        "consistency": round(max(0, consistency), 1),
    }
