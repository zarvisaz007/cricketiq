"""
features/team_features.py
Computes team-level features for prediction models.
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection


def get_head_to_head(team1: str, team2: str, match_type: str, gender: str = "male") -> dict:
    """
    Returns head-to-head record between two teams.
    Includes decay-weighted recent H2H, venue-specific H2H, and win streak.
    """
    import math
    conn = get_connection()
    rows = conn.execute("""
        SELECT winner, venue, date FROM matches
        WHERE match_type = ?
          AND gender = ?
          AND ((team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?))
          AND winner IS NOT NULL
        ORDER BY date DESC
    """, (match_type, gender, team1, team2, team2, team1)).fetchall()
    conn.close()

    total = len(rows)
    team1_wins = sum(1 for r in rows if r["winner"] == team1)
    team2_wins = sum(1 for r in rows if r["winner"] == team2)

    # Decay-weighted H2H (last 5 matches, more recent = more weight)
    recent = rows[:5]
    h2h_decay_pct = 50.0
    if recent:
        w_wins = 0.0
        w_total = 0.0
        for i, r in enumerate(recent):
            w = math.exp(-0.15 * i)
            w_total += w
            if r["winner"] == team1:
                w_wins += w
        h2h_decay_pct = round(w_wins / w_total * 100, 1) if w_total > 0 else 50.0

    # Win streak: consecutive wins for team1 from most recent
    win_streak = 0
    for r in rows:
        if r["winner"] == team1:
            win_streak += 1
        else:
            break

    return {
        "total": total,
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "team1_win_pct": round(team1_wins / total * 100, 1) if total > 0 else 50.0,
        "h2h_decay_pct": h2h_decay_pct,
        "team1_win_streak": win_streak,
    }


def get_team_recent_form(team: str, match_type: str, n: int = 10, gender: str = "male") -> float:
    """
    Returns team form score (0-100) based on last N matches.
    Uses exponential decay: recent matches weigh more.
    weight_i = exp(-0.1 * i) where i=0 is most recent.
    """
    import math
    conn = get_connection()
    rows = conn.execute("""
        SELECT winner FROM matches
        WHERE match_type = ?
          AND gender = ?
          AND (team1 = ? OR team2 = ?)
          AND winner IS NOT NULL
        ORDER BY date DESC
        LIMIT ?
    """, (match_type, gender, team, team, n)).fetchall()
    conn.close()

    if not rows:
        return 50.0

    weighted_wins = 0.0
    total_weight = 0.0
    for i, r in enumerate(rows):
        w = math.exp(-0.1 * i)
        total_weight += w
        if r["winner"] == team:
            weighted_wins += w

    return round(weighted_wins / total_weight * 100, 1) if total_weight > 0 else 50.0


def get_venue_win_rate(team: str, venue: str, match_type: str, gender: str = "male") -> float:
    """Returns win rate for a team at a specific venue."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT winner FROM matches
        WHERE match_type = ?
          AND gender = ?
          AND venue = ?
          AND (team1 = ? OR team2 = ?)
          AND winner IS NOT NULL
    """, (match_type, gender, venue, team, team)).fetchall()
    conn.close()

    if not rows:
        return 50.0

    wins = sum(1 for r in rows if r["winner"] == team)
    return round(wins / len(rows) * 100, 1)


def get_toss_win_rate(team: str, match_type: str, gender: str = "male") -> float:
    """Returns win rate when team wins toss."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT winner FROM matches
        WHERE match_type = ?
          AND gender = ?
          AND toss_winner = ?
          AND winner IS NOT NULL
    """, (match_type, gender, team)).fetchall()
    conn.close()

    if not rows:
        return 50.0

    wins = sum(1 for r in rows if r["winner"] == team)
    return round(wins / len(rows) * 100, 1)


def get_team_strength(team: str, match_type: str, venue: str = None) -> float:
    """
    Composite team strength score (0-100).

    TeamStrength =
        avg(player_ratings) * 0.40
        + team_form * 10 * 0.30
        + venue_advantage * 0.20
        + head_to_head (applied at prediction time) * 0.10
    """
    conn = get_connection()

    # Get top 11 player ratings for this team
    rows = conn.execute("""
        SELECT overall_rating FROM player_ratings pr
        WHERE pr.match_type = ?
          AND pr.player_name IN (
              SELECT DISTINCT player_name FROM player_match_stats pms
              JOIN matches m ON pms.match_id = m.id
              WHERE m.match_type = ? AND m.gender = 'male' AND pms.team = ?
              ORDER BY m.date DESC LIMIT 200
          )
        ORDER BY overall_rating DESC
        LIMIT 11
    """, (match_type, match_type, team)).fetchall()
    conn.close()

    avg_player_rating = (sum(r["overall_rating"] for r in rows) / len(rows)) if rows else 50.0
    team_form = get_team_recent_form(team, match_type)
    venue_adv = get_venue_win_rate(team, venue, match_type) if venue else 50.0

    strength = (avg_player_rating * 0.40) + (team_form * 0.30) + (venue_adv * 0.30)
    return round(min(max(strength, 0), 100), 2)


def get_team_squad(team: str, match_type: str, last_n_matches: int = 5, gender: str = "male") -> list:
    """Returns the most recent playing XI for a team."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT pms.player_name
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE m.match_type = ? AND m.gender = ? AND pms.team = ?
        ORDER BY m.date DESC
        LIMIT ?
    """, (match_type, gender, team, last_n_matches * 11)).fetchall()
    conn.close()
    return [r["player_name"] for r in rows]
