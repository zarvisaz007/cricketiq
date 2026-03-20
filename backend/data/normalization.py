"""
data/normalization.py
Normalizes team names across datasets.
IPL teams have changed names over years — this maps historical names to current.
"""

# Map historical/alternate team names → canonical name
TEAM_NAME_MAP = {
    # IPL name changes
    "Delhi Daredevils":             "Delhi Capitals",
    "Deccan Chargers":              "Sunrisers Hyderabad",
    "Pune Warriors":                "Rising Pune Supergiant",
    "Rising Pune Supergiants":      "Rising Pune Supergiant",
    "Kings XI Punjab":              "Punjab Kings",

    # International alternate spellings
    "United Arab Emirates":         "UAE",
    "Papua New Guinea":             "PNG",
    "U.S.A.":                       "USA",
    "United States of America":     "USA",
}


def normalize_team(name: str) -> str:
    """Return canonical team name."""
    return TEAM_NAME_MAP.get(name, name)


def normalize_player(name: str) -> str:
    """Basic player name normalization. Extend as needed."""
    return name.strip()


def normalize_venue(venue: str) -> str:
    """Normalize venue names."""
    if not venue:
        return "Unknown"
    return venue.strip()
