"""
features/venue_features.py
Venue/pitch-based features for prediction models.
Reads from the venues table seeded with pitch characteristics.
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection


def _fuzzy_match_venue(venue_name: str, conn) -> dict:
    """Try to match a venue name to the venues table using substring matching."""
    if not venue_name:
        return None

    # Exact match first
    row = conn.execute("SELECT * FROM venues WHERE name = ?", (venue_name,)).fetchone()
    if row:
        return dict(row)

    # Substring match: check if any seeded venue name is contained in the query or vice versa
    all_venues = conn.execute("SELECT * FROM venues").fetchall()
    venue_lower = venue_name.lower()
    for v in all_venues:
        v_name = v["name"].lower()
        if v_name in venue_lower or venue_lower in v_name:
            return dict(v)
        # Match on city name
        if v["city"] and v["city"].lower() in venue_lower:
            return dict(v)

    return None


def get_venue_factors(venue_name: str) -> dict:
    """
    Returns pitch characteristics for a venue.
    Falls back to neutral (1.0) if venue not found.
    """
    conn = get_connection()
    venue = _fuzzy_match_venue(venue_name, conn)
    conn.close()

    if venue:
        return {
            "venue_id": venue.get("id"),
            "venue_name": venue.get("name"),
            "batting_factor": venue.get("batting_factor", 1.0),
            "spin_factor": venue.get("spin_factor", 1.0),
            "pace_factor": venue.get("pace_factor", 1.0),
            "dew_factor": venue.get("dew_factor", 0.0),
            "avg_first_innings_score": venue.get("avg_first_innings_score", 160.0),
            "avg_second_innings_score": venue.get("avg_second_innings_score", 150.0),
        }

    return {
        "venue_id": None,
        "venue_name": venue_name,
        "batting_factor": 1.0,
        "spin_factor": 1.0,
        "pace_factor": 1.0,
        "dew_factor": 0.0,
        "avg_first_innings_score": 160.0,
        "avg_second_innings_score": 150.0,
    }


def get_home_advantage(team: str, venue_name: str, match_type: str) -> float:
    """
    Returns home advantage score (0-100).
    Based on team's win rate at this venue + country match.
    """
    conn = get_connection()
    venue = _fuzzy_match_venue(venue_name, conn)

    # Win rate at this venue
    rows = conn.execute("""
        SELECT winner FROM matches
        WHERE venue = ? AND match_type = ? AND gender = 'male'
          AND (team1 = ? OR team2 = ?) AND winner IS NOT NULL
    """, (venue_name, match_type, team, team)).fetchall()

    venue_win_rate = 50.0
    if rows:
        wins = sum(1 for r in rows if r["winner"] == team)
        venue_win_rate = wins / len(rows) * 100

    # Country bonus: if team's home country matches venue country
    country_bonus = 0.0
    if venue:
        home_countries = {
            "India": "India", "Australia": "Australia", "England": "England",
            "South Africa": "South Africa", "New Zealand": "New Zealand",
            "Pakistan": "Pakistan", "Sri Lanka": "Sri Lanka",
            "Bangladesh": "Bangladesh", "West Indies": "Barbados",
            "Zimbabwe": "Zimbabwe", "Afghanistan": "Afghanistan",
        }
        venue_country = venue.get("country", "")
        if home_countries.get(team) == venue_country:
            country_bonus = 10.0

    conn.close()
    return round(min(venue_win_rate + country_bonus, 100), 2)


def get_venue_feature_vector(venue_name: str, team1: str, team2: str, match_type: str) -> dict:
    """
    Returns all venue-related features as a dict for the feature registry.
    """
    factors = get_venue_factors(venue_name)
    home1 = get_home_advantage(team1, venue_name, match_type)
    home2 = get_home_advantage(team2, venue_name, match_type)

    return {
        "venue_batting_factor": factors["batting_factor"],
        "venue_spin_factor": factors["spin_factor"],
        "venue_pace_factor": factors["pace_factor"],
        "venue_dew_factor": factors["dew_factor"],
        "venue_avg_first_score": factors["avg_first_innings_score"],
        "home_advantage_diff": home1 - home2,
    }
