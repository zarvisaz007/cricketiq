"""
fantasy/credit_values.py
Estimate Dream11 credit values for players based on their ratings and form.
Credits range from 7.0 (budget) to 12.0 (premium).
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection


def estimate_credit_value(player_name: str, match_type: str = "T20") -> float:
    """
    Estimate a player's Dream11 credit value (7.0 - 12.0).
    Based on overall rating, form, and games played.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT overall_rating, form_score, games_played
        FROM player_ratings
        WHERE player_name = ? AND match_type = ?
    """, (player_name, match_type)).fetchone()
    conn.close()

    if not row:
        return 8.0  # default mid-range

    rating = row["overall_rating"]
    form = row["form_score"]
    games = row["games_played"]

    # Weighted score: rating 60%, form 30%, experience 10%
    experience_factor = min(games / 50, 1.0) * 100  # caps at 100
    composite = rating * 0.60 + form * 0.30 + experience_factor * 0.10

    # Map composite (0-100) to credits (7.0-12.0)
    credit = 7.0 + (composite / 100) * 5.0
    return round(min(max(credit, 7.0), 12.0), 1)


def get_team_credit_values(team: str, match_type: str = "T20",
                           last_n_matches: int = 5) -> list:
    """
    Get credit values for all players in a team's recent squad.
    Returns sorted by credit value (highest first).
    """
    conn = get_connection()
    players = conn.execute("""
        SELECT DISTINCT pms.player_name
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.team = ? AND m.match_type = ? AND m.gender = 'male'
        ORDER BY m.date DESC
        LIMIT ?
    """, (team, match_type, last_n_matches * 15)).fetchall()
    conn.close()

    seen = set()
    results = []
    for p in players:
        name = p["player_name"]
        if name in seen:
            continue
        seen.add(name)
        credit = estimate_credit_value(name, match_type)
        results.append({"player": name, "credit": credit})

    results.sort(key=lambda x: -x["credit"])
    return results[:15]  # top 15
