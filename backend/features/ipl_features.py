"""
features/ipl_features.py
IPL-specific feature engineering.
Franchise strength, home ground advantage, foreign player impact, IPL form.
"""
import sys
import os
import math
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection

# IPL franchise home grounds
IPL_HOME_GROUNDS = {
    "Chennai Super Kings": "MA Chidambaram Stadium",
    "Mumbai Indians": "Wankhede Stadium",
    "Royal Challengers Bengaluru": "M Chinnaswamy Stadium",
    "Royal Challengers Bangalore": "M Chinnaswamy Stadium",
    "Kolkata Knight Riders": "Eden Gardens",
    "Delhi Capitals": "Arun Jaitley Stadium",
    "Sunrisers Hyderabad": "Rajiv Gandhi International Stadium",
    "Rajasthan Royals": "Sawai Mansingh Stadium",
    "Punjab Kings": "Punjab Cricket Association IS Bindra Stadium",
    "Kings XI Punjab": "Punjab Cricket Association IS Bindra Stadium",
    "Lucknow Super Giants": "Ekana Cricket Stadium",
    "Gujarat Titans": "Narendra Modi Stadium",
}


def get_ipl_team_form(team: str, season: str = None, n: int = 10) -> float:
    """
    IPL-specific form: win% in recent IPL matches.
    If season provided, filters to that season's matches.
    Uses exponential decay weighting.
    """
    conn = get_connection()

    query = """
        SELECT winner, date FROM matches
        WHERE competition = 'IPL' AND gender = 'male'
          AND (team1 = ? OR team2 = ?) AND winner IS NOT NULL
    """
    params = [team, team]

    if season:
        query += " AND date LIKE ?"
        params.append(f"{season}%")

    query += " ORDER BY date DESC LIMIT ?"
    params.append(n)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return 50.0

    w_wins = 0.0
    w_total = 0.0
    for i, r in enumerate(rows):
        w = math.exp(-0.1 * i)
        w_total += w
        if r["winner"] == team:
            w_wins += w

    return round(w_wins / w_total * 100, 1) if w_total > 0 else 50.0


def get_ipl_h2h(team1: str, team2: str, n: int = 10) -> dict:
    """IPL-specific head-to-head record."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT winner FROM matches
        WHERE competition = 'IPL' AND gender = 'male'
          AND ((team1 = ? AND team2 = ?) OR (team1 = ? AND team2 = ?))
          AND winner IS NOT NULL
        ORDER BY date DESC LIMIT ?
    """, (team1, team2, team2, team1, n)).fetchall()
    conn.close()

    total = len(rows)
    t1_wins = sum(1 for r in rows if r["winner"] == team1)
    return {
        "total": total,
        "team1_wins": t1_wins,
        "team2_wins": total - t1_wins,
        "team1_win_pct": round(t1_wins / total * 100, 1) if total > 0 else 50.0,
    }


def is_home_match(team: str, venue: str) -> bool:
    """Check if venue is team's home ground."""
    home = IPL_HOME_GROUNDS.get(team, "")
    if not home or not venue:
        return False
    return home.lower() in venue.lower() or venue.lower() in home.lower()


def get_franchise_strength(team: str, season: str = None) -> float:
    """
    Composite franchise strength for IPL.
    Based on: average player rating + recent form + squad depth.
    """
    conn = get_connection()

    # Get top 15 players for this IPL team
    season_filter = f" AND m.date LIKE '{season}%'" if season else ""
    rows = conn.execute(f"""
        SELECT pr.overall_rating, pr.batting_rating, pr.bowling_rating, pr.form_score
        FROM player_ratings pr
        WHERE pr.match_type = 'T20'
          AND pr.player_name IN (
              SELECT DISTINCT pms.player_name FROM player_match_stats pms
              JOIN matches m ON pms.match_id = m.id
              WHERE m.competition = 'IPL' AND pms.team = ? {season_filter}
              ORDER BY m.date DESC LIMIT 150
          )
        ORDER BY pr.overall_rating DESC LIMIT 15
    """, (team,)).fetchall()
    conn.close()

    if not rows:
        return 50.0

    avg_rating = sum(r["overall_rating"] for r in rows) / len(rows)
    top3_avg = sum(r["overall_rating"] for r in rows[:3]) / min(3, len(rows))
    squad_depth = min(len(rows) / 11 * 100, 100)  # how close to full XI

    # Weighted composite
    strength = avg_rating * 0.50 + top3_avg * 0.30 + squad_depth * 0.20
    return round(min(max(strength, 0), 100), 2)


def get_foreign_player_impact(team: str, match_type: str = "T20") -> dict:
    """
    Estimate foreign player impact. IPL rule: max 4 overseas players.
    Returns avg rating of likely foreign players and their contribution.
    """
    conn = get_connection()

    # Get top rated players for this team in IPL
    rows = conn.execute("""
        SELECT DISTINCT pms.player_name, pr.overall_rating
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        LEFT JOIN player_ratings pr ON pr.player_name = pms.player_name AND pr.match_type = 'T20'
        WHERE m.competition = 'IPL' AND pms.team = ? AND m.gender = 'male'
        ORDER BY m.date DESC LIMIT 55
    """, (team,)).fetchall()
    conn.close()

    # We can't easily determine nationality from Cricsheet data alone,
    # so return aggregate stats
    if not rows:
        return {"avg_rating": 50.0, "top_player_count": 0}

    seen = {}
    for r in rows:
        if r["player_name"] not in seen:
            seen[r["player_name"]] = r["overall_rating"] or 50.0

    ratings = sorted(seen.values(), reverse=True)
    return {
        "avg_rating": round(sum(ratings[:11]) / min(11, len(ratings)), 2),
        "top_player_count": len(ratings),
    }


def get_ipl_feature_vector(team1: str, team2: str, venue: str = None,
                           season: str = None) -> dict:
    """Build IPL-specific feature vector."""
    form1 = get_ipl_team_form(team1, season)
    form2 = get_ipl_team_form(team2, season)
    h2h = get_ipl_h2h(team1, team2)
    str1 = get_franchise_strength(team1, season)
    str2 = get_franchise_strength(team2, season)
    home1 = 1.0 if venue and is_home_match(team1, venue) else 0.0
    home2 = 1.0 if venue and is_home_match(team2, venue) else 0.0

    return {
        "ipl_form_diff": form1 - form2,
        "ipl_h2h_pct": h2h["team1_win_pct"] / 100.0,
        "ipl_strength_diff": str1 - str2,
        "ipl_home_advantage": home1 - home2,
        "ipl_form1": form1 / 100.0,
        "ipl_form2": form2 / 100.0,
    }
