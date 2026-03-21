"""
impact/pvor_analytical.py
Analytical PVOR — sub-second player value over replacement.

Formula:
  batting_pvor = (player_runs - replacement_avg) / max(replacement_std, 1)
  bowling_pvor = (replacement_wpm - player_wpm) / max(replacement_std, 0.1)
  fielding_pvor = (catches + stumpings) * 3

Replacement level = 25th percentile at same batting_position / bowling_slot.
"""
import sys
import os
import numpy as np
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection

# Role weights for total PVOR
ROLE_WEIGHTS = {
    "batsman":      {"bat": 0.80, "bowl": 0.10, "field": 0.10},
    "bowler":       {"bat": 0.10, "bowl": 0.80, "field": 0.10},
    "allrounder":   {"bat": 0.45, "bowl": 0.45, "field": 0.10},
    "wicketkeeper": {"bat": 0.70, "bowl": 0.00, "field": 0.30},
    "unknown":      {"bat": 0.40, "bowl": 0.40, "field": 0.20},
}

# Cache for replacement levels
_replacement_cache = {}


def _get_replacement_levels(match_type: str, conn) -> dict:
    """
    Compute replacement level stats (25th percentile) per batting position
    and bowling slot. Cached per match_type.
    """
    if match_type in _replacement_cache:
        return _replacement_cache[match_type]

    levels = {"batting": {}, "bowling": {}}

    # Batting replacement by position (1-11)
    for pos in range(1, 12):
        rows = conn.execute("""
            SELECT pms.runs FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.id
            WHERE m.match_type = ? AND m.gender = 'male'
              AND pms.batting_position = ? AND pms.balls_faced > 0
        """, (match_type, pos)).fetchall()

        if rows:
            runs = [r["runs"] for r in rows]
            levels["batting"][pos] = {
                "avg": float(np.percentile(runs, 25)),
                "std": max(float(np.std(runs)), 1.0),
            }
        else:
            levels["batting"][pos] = {"avg": 15.0, "std": 12.0}

    # Bowling replacement by slot (1-6)
    for slot in range(1, 7):
        rows = conn.execute("""
            SELECT pms.wickets, pms.overs_bowled FROM player_match_stats pms
            JOIN matches m ON pms.match_id = m.id
            WHERE m.match_type = ? AND m.gender = 'male'
              AND pms.bowling_slot = ? AND pms.overs_bowled > 0
        """, (match_type, slot)).fetchall()

        if rows:
            wpm = [r["wickets"] / max(r["overs_bowled"], 0.1) for r in rows]
            levels["bowling"][slot] = {
                "avg": float(np.percentile(wpm, 25)),
                "std": max(float(np.std(wpm)), 0.1),
            }
        else:
            levels["bowling"][slot] = {"avg": 0.3, "std": 0.2}

    _replacement_cache[match_type] = levels
    return levels


def compute_analytical_pvor(player_name: str, match_type: str,
                            last_n: int = 10) -> dict:
    """
    Compute analytical PVOR for a player. Sub-second computation.

    Returns:
        {
            "player": str,
            "batting_pvor": float,
            "bowling_pvor": float,
            "fielding_pvor": float,
            "total_pvor": float,
            "role": str,
            "impact_label": str,
        }
    """
    conn = get_connection()
    replacement = _get_replacement_levels(match_type, conn)

    # Get player's recent stats
    bat_rows = conn.execute("""
        SELECT pms.runs, pms.balls_faced, pms.batting_position,
               pms.catches, pms.stumpings
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ? AND m.match_type = ? AND m.gender = 'male'
          AND pms.balls_faced > 0
        ORDER BY m.date DESC LIMIT ?
    """, (player_name, match_type, last_n)).fetchall()

    bowl_rows = conn.execute("""
        SELECT pms.wickets, pms.overs_bowled, pms.bowling_slot
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.player_name = ? AND m.match_type = ? AND m.gender = 'male'
          AND pms.overs_bowled > 0
        ORDER BY m.date DESC LIMIT ?
    """, (player_name, match_type, last_n)).fetchall()
    conn.close()

    # Batting PVOR
    batting_pvor = 0.0
    if bat_rows:
        for r in bat_rows:
            pos = r["batting_position"] or 5  # default mid-order
            rep = replacement["batting"].get(pos, {"avg": 15.0, "std": 12.0})
            batting_pvor += (r["runs"] - rep["avg"]) / rep["std"]
        batting_pvor /= len(bat_rows)

    # Bowling PVOR
    bowling_pvor = 0.0
    if bowl_rows:
        for r in bowl_rows:
            slot = r["bowling_slot"] or 3
            rep = replacement["bowling"].get(slot, {"avg": 0.3, "std": 0.2})
            player_wpm = r["wickets"] / max(r["overs_bowled"], 0.1)
            bowling_pvor += (player_wpm - rep["avg"]) / rep["std"]
        bowling_pvor /= len(bowl_rows)

    # Fielding PVOR
    fielding_pvor = 0.0
    if bat_rows:
        total_catches = sum(r["catches"] or 0 for r in bat_rows)
        total_stumpings = sum(r["stumpings"] or 0 for r in bat_rows)
        fielding_pvor = (total_catches + total_stumpings) * 3 / len(bat_rows)

    # Determine role
    is_batter = len(bat_rows) >= 3
    is_bowler = len(bowl_rows) >= 3
    has_stumpings = any(r["stumpings"] and r["stumpings"] > 0 for r in bat_rows) if bat_rows else False

    if has_stumpings:
        role = "wicketkeeper"
    elif is_batter and is_bowler:
        role = "allrounder"
    elif is_batter:
        role = "batsman"
    elif is_bowler:
        role = "bowler"
    else:
        role = "unknown"

    # Weighted total
    weights = ROLE_WEIGHTS[role]
    total_pvor = (batting_pvor * weights["bat"] +
                  bowling_pvor * weights["bowl"] +
                  fielding_pvor * weights["field"])

    # Impact label
    if total_pvor >= 1.5:
        impact_label = "Elite"
    elif total_pvor >= 0.8:
        impact_label = "High"
    elif total_pvor >= 0.3:
        impact_label = "Medium"
    elif total_pvor >= -0.3:
        impact_label = "Low"
    else:
        impact_label = "Negative"

    return {
        "player": player_name,
        "batting_pvor": round(batting_pvor, 3),
        "bowling_pvor": round(bowling_pvor, 3),
        "fielding_pvor": round(fielding_pvor, 3),
        "total_pvor": round(total_pvor, 3),
        "role": role,
        "impact_label": impact_label,
    }


def compute_match_pvor_batch(match_id: int, match_type: str):
    """
    Compute and store analytical PVOR for all players in a match.
    Stores results in pvor_match table.
    """
    conn = get_connection()
    players = conn.execute("""
        SELECT DISTINCT player_name, team FROM player_match_stats
        WHERE match_id = ?
    """, (match_id,)).fetchall()

    now = datetime.now().isoformat()
    for p in players:
        pvor = compute_analytical_pvor(p["player_name"], match_type)
        conn.execute("""
            INSERT OR REPLACE INTO pvor_match
                (match_id, player_name, team, match_type,
                 batting_pvor, bowling_pvor, fielding_pvor, total_pvor, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (match_id, p["player_name"], p["team"], match_type,
              pvor["batting_pvor"], pvor["bowling_pvor"],
              pvor["fielding_pvor"], pvor["total_pvor"], now))

    conn.commit()
    conn.close()
    return len(players)


def update_player_agg_pvor(player_name: str, match_type: str):
    """
    Update rolling PVOR aggregations (30d, 90d, career) in pvor_player_agg table.
    """
    conn = get_connection()
    now = datetime.now()

    def _avg_pvor(days=None):
        if days:
            cutoff = (now - timedelta(days=days)).isoformat()
            rows = conn.execute("""
                SELECT total_pvor FROM pvor_match pm
                JOIN matches m ON pm.match_id = m.id
                WHERE pm.player_name = ? AND pm.match_type = ? AND m.date >= ?
            """, (player_name, match_type, cutoff)).fetchall()
        else:
            rows = conn.execute("""
                SELECT total_pvor FROM pvor_match
                WHERE player_name = ? AND match_type = ?
            """, (player_name, match_type)).fetchall()

        if rows:
            return round(float(np.mean([r["total_pvor"] for r in rows])), 3), len(rows)
        return 0.0, 0

    pvor_30d, n_30d = _avg_pvor(30)
    pvor_90d, n_90d = _avg_pvor(90)
    pvor_career, n_career = _avg_pvor()

    conn.execute("""
        INSERT INTO pvor_player_agg
            (player_name, match_type, pvor_last_30d, pvor_last_90d, pvor_career,
             matches_30d, matches_90d, matches_career, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_name, match_type) DO UPDATE SET
            pvor_last_30d=excluded.pvor_last_30d, pvor_last_90d=excluded.pvor_last_90d,
            pvor_career=excluded.pvor_career, matches_30d=excluded.matches_30d,
            matches_90d=excluded.matches_90d, matches_career=excluded.matches_career,
            last_updated=excluded.last_updated
    """, (player_name, match_type, pvor_30d, pvor_90d, pvor_career,
          n_30d, n_90d, n_career, now.isoformat()))

    conn.commit()
    conn.close()
