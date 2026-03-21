"""
database/seed_venues.py
Seeds the venues table with ~30 major cricket grounds and their pitch characteristics.

Factors are on a 0.0-2.0 scale where 1.0 is neutral:
  batting_factor > 1.0 = batting-friendly
  spin_factor > 1.0 = spin-friendly
  pace_factor > 1.0 = pace-friendly
  dew_factor 0.0-1.0 = likelihood of dew affecting second innings

Usage:
    python database/seed_venues.py
"""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from database.db import get_connection

VENUES = [
    # IPL Venues — India
    {"name": "M Chinnaswamy Stadium", "city": "Bengaluru", "country": "India",
     "batting_factor": 1.4, "spin_factor": 0.8, "pace_factor": 1.0, "dew_factor": 0.5,
     "avg_first_innings_score": 175, "avg_second_innings_score": 165},

    {"name": "Wankhede Stadium", "city": "Mumbai", "country": "India",
     "batting_factor": 1.3, "spin_factor": 0.9, "pace_factor": 1.1, "dew_factor": 0.7,
     "avg_first_innings_score": 170, "avg_second_innings_score": 162},

    {"name": "Eden Gardens", "city": "Kolkata", "country": "India",
     "batting_factor": 1.1, "spin_factor": 1.3, "pace_factor": 0.8, "dew_factor": 0.8,
     "avg_first_innings_score": 165, "avg_second_innings_score": 158},

    {"name": "MA Chidambaram Stadium", "city": "Chennai", "country": "India",
     "batting_factor": 0.9, "spin_factor": 1.5, "pace_factor": 0.7, "dew_factor": 0.6,
     "avg_first_innings_score": 155, "avg_second_innings_score": 148},

    {"name": "Arun Jaitley Stadium", "city": "Delhi", "country": "India",
     "batting_factor": 1.2, "spin_factor": 1.1, "pace_factor": 0.9, "dew_factor": 0.7,
     "avg_first_innings_score": 168, "avg_second_innings_score": 160},

    {"name": "Rajiv Gandhi International Stadium", "city": "Hyderabad", "country": "India",
     "batting_factor": 1.2, "spin_factor": 1.0, "pace_factor": 1.0, "dew_factor": 0.6,
     "avg_first_innings_score": 167, "avg_second_innings_score": 158},

    {"name": "Narendra Modi Stadium", "city": "Ahmedabad", "country": "India",
     "batting_factor": 1.1, "spin_factor": 1.2, "pace_factor": 0.9, "dew_factor": 0.5,
     "avg_first_innings_score": 162, "avg_second_innings_score": 155},

    {"name": "Sawai Mansingh Stadium", "city": "Jaipur", "country": "India",
     "batting_factor": 1.3, "spin_factor": 1.0, "pace_factor": 0.9, "dew_factor": 0.4,
     "avg_first_innings_score": 170, "avg_second_innings_score": 160},

    {"name": "Punjab Cricket Association IS Bindra Stadium", "city": "Mohali", "country": "India",
     "batting_factor": 1.1, "spin_factor": 0.9, "pace_factor": 1.1, "dew_factor": 0.6,
     "avg_first_innings_score": 165, "avg_second_innings_score": 157},

    {"name": "Ekana Cricket Stadium", "city": "Lucknow", "country": "India",
     "batting_factor": 1.0, "spin_factor": 1.1, "pace_factor": 0.9, "dew_factor": 0.6,
     "avg_first_innings_score": 160, "avg_second_innings_score": 152},

    {"name": "Dr DY Patil Sports Academy", "city": "Navi Mumbai", "country": "India",
     "batting_factor": 1.1, "spin_factor": 0.9, "pace_factor": 1.0, "dew_factor": 0.7,
     "avg_first_innings_score": 165, "avg_second_innings_score": 157},

    {"name": "Himachal Pradesh Cricket Association Stadium", "city": "Dharamsala", "country": "India",
     "batting_factor": 1.2, "spin_factor": 0.7, "pace_factor": 1.3, "dew_factor": 0.3,
     "avg_first_innings_score": 168, "avg_second_innings_score": 160},

    # International Venues — Australia
    {"name": "Melbourne Cricket Ground", "city": "Melbourne", "country": "Australia",
     "batting_factor": 1.1, "spin_factor": 0.8, "pace_factor": 1.2, "dew_factor": 0.3,
     "avg_first_innings_score": 165, "avg_second_innings_score": 158},

    {"name": "Sydney Cricket Ground", "city": "Sydney", "country": "Australia",
     "batting_factor": 1.0, "spin_factor": 1.1, "pace_factor": 1.0, "dew_factor": 0.3,
     "avg_first_innings_score": 162, "avg_second_innings_score": 155},

    {"name": "The Gabba", "city": "Brisbane", "country": "Australia",
     "batting_factor": 1.1, "spin_factor": 0.7, "pace_factor": 1.4, "dew_factor": 0.2,
     "avg_first_innings_score": 163, "avg_second_innings_score": 155},

    # International Venues — England
    {"name": "Lord's", "city": "London", "country": "England",
     "batting_factor": 0.9, "spin_factor": 0.8, "pace_factor": 1.3, "dew_factor": 0.4,
     "avg_first_innings_score": 155, "avg_second_innings_score": 148},

    {"name": "The Oval", "city": "London", "country": "England",
     "batting_factor": 1.1, "spin_factor": 0.9, "pace_factor": 1.1, "dew_factor": 0.4,
     "avg_first_innings_score": 165, "avg_second_innings_score": 158},

    {"name": "Edgbaston", "city": "Birmingham", "country": "England",
     "batting_factor": 1.0, "spin_factor": 0.8, "pace_factor": 1.2, "dew_factor": 0.4,
     "avg_first_innings_score": 160, "avg_second_innings_score": 153},

    # International Venues — South Africa
    {"name": "Newlands", "city": "Cape Town", "country": "South Africa",
     "batting_factor": 1.0, "spin_factor": 0.7, "pace_factor": 1.4, "dew_factor": 0.2,
     "avg_first_innings_score": 158, "avg_second_innings_score": 150},

    {"name": "The Wanderers Stadium", "city": "Johannesburg", "country": "South Africa",
     "batting_factor": 1.3, "spin_factor": 0.7, "pace_factor": 1.3, "dew_factor": 0.2,
     "avg_first_innings_score": 172, "avg_second_innings_score": 165},

    # International Venues — UAE / Middle East
    {"name": "Dubai International Cricket Stadium", "city": "Dubai", "country": "UAE",
     "batting_factor": 1.0, "spin_factor": 1.3, "pace_factor": 0.8, "dew_factor": 0.8,
     "avg_first_innings_score": 155, "avg_second_innings_score": 148},

    {"name": "Sheikh Zayed Stadium", "city": "Abu Dhabi", "country": "UAE",
     "batting_factor": 0.9, "spin_factor": 1.4, "pace_factor": 0.8, "dew_factor": 0.7,
     "avg_first_innings_score": 150, "avg_second_innings_score": 143},

    # International Venues — West Indies
    {"name": "Kensington Oval", "city": "Bridgetown", "country": "Barbados",
     "batting_factor": 1.0, "spin_factor": 0.9, "pace_factor": 1.2, "dew_factor": 0.3,
     "avg_first_innings_score": 160, "avg_second_innings_score": 153},

    # International Venues — New Zealand
    {"name": "Hagley Oval", "city": "Christchurch", "country": "New Zealand",
     "batting_factor": 1.0, "spin_factor": 0.7, "pace_factor": 1.3, "dew_factor": 0.3,
     "avg_first_innings_score": 158, "avg_second_innings_score": 150},

    # International Venues — Sri Lanka
    {"name": "R Premadasa Stadium", "city": "Colombo", "country": "Sri Lanka",
     "batting_factor": 1.0, "spin_factor": 1.4, "pace_factor": 0.7, "dew_factor": 0.6,
     "avg_first_innings_score": 155, "avg_second_innings_score": 148},

    {"name": "Pallekele International Cricket Stadium", "city": "Kandy", "country": "Sri Lanka",
     "batting_factor": 1.1, "spin_factor": 1.2, "pace_factor": 0.8, "dew_factor": 0.4,
     "avg_first_innings_score": 160, "avg_second_innings_score": 153},

    # International Venues — Pakistan
    {"name": "National Stadium", "city": "Karachi", "country": "Pakistan",
     "batting_factor": 1.0, "spin_factor": 1.2, "pace_factor": 0.9, "dew_factor": 0.6,
     "avg_first_innings_score": 158, "avg_second_innings_score": 150},

    {"name": "Gaddafi Stadium", "city": "Lahore", "country": "Pakistan",
     "batting_factor": 1.1, "spin_factor": 1.1, "pace_factor": 0.9, "dew_factor": 0.7,
     "avg_first_innings_score": 165, "avg_second_innings_score": 158},

    # International Venues — Bangladesh
    {"name": "Shere Bangla National Stadium", "city": "Dhaka", "country": "Bangladesh",
     "batting_factor": 0.9, "spin_factor": 1.5, "pace_factor": 0.7, "dew_factor": 0.7,
     "avg_first_innings_score": 150, "avg_second_innings_score": 143},

    # International Venues — Zimbabwe
    {"name": "Harare Sports Club", "city": "Harare", "country": "Zimbabwe",
     "batting_factor": 1.0, "spin_factor": 0.9, "pace_factor": 1.1, "dew_factor": 0.3,
     "avg_first_innings_score": 155, "avg_second_innings_score": 148},
]


def seed_venues():
    """Insert or update venue data."""
    conn = get_connection()
    inserted = updated = 0

    for v in VENUES:
        existing = conn.execute("SELECT id FROM venues WHERE name = ?", (v["name"],)).fetchone()
        if existing:
            conn.execute("""
                UPDATE venues SET city=?, country=?, batting_factor=?, spin_factor=?,
                    pace_factor=?, dew_factor=?, avg_first_innings_score=?, avg_second_innings_score=?
                WHERE name=?
            """, (v["city"], v["country"], v["batting_factor"], v["spin_factor"],
                  v["pace_factor"], v["dew_factor"], v["avg_first_innings_score"],
                  v["avg_second_innings_score"], v["name"]))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO venues (name, city, country, batting_factor, spin_factor,
                    pace_factor, dew_factor, avg_first_innings_score, avg_second_innings_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (v["name"], v["city"], v["country"], v["batting_factor"], v["spin_factor"],
                  v["pace_factor"], v["dew_factor"], v["avg_first_innings_score"],
                  v["avg_second_innings_score"]))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"[Venues] Seeded {inserted} new, updated {updated} existing ({len(VENUES)} total)")


if __name__ == "__main__":
    seed_venues()
