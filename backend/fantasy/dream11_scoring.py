"""
fantasy/dream11_scoring.py
Dream11 fantasy cricket scoring system.
Full scoring model for T20 matches.
"""

# ── Batting Points ──────────────────────────────────────────
BATTING_POINTS = {
    "run": 1,
    "boundary_bonus": 1,       # per 4
    "six_bonus": 2,            # per 6
    "half_century": 8,         # 50-99 runs
    "century": 16,             # 100+ runs
    "duck": -2,                # 0 runs (out), batters only
    "strike_rate_below_60": -6,    # SR < 60 (min 10 balls)
    "strike_rate_60_70": -4,       # SR 60-70
    "strike_rate_70_80": -2,       # SR 70-80
    "strike_rate_170_plus": 4,     # SR >= 170
    "strike_rate_150_170": 2,      # SR 150-170
}

# ── Bowling Points ──────────────────────────────────────────
BOWLING_POINTS = {
    "wicket": 25,
    "bonus_3_wickets": 8,
    "bonus_4_wickets": 16,
    "bonus_5_wickets": 24,
    "maiden_over": 12,
    "economy_below_5": 6,     # min 2 overs
    "economy_5_6": 4,
    "economy_6_7": 2,
    "economy_10_11": -2,
    "economy_11_12": -4,
    "economy_above_12": -6,
}

# ── Fielding Points ─────────────────────────────────────────
FIELDING_POINTS = {
    "catch": 8,
    "stumping": 12,
    "direct_runout": 12,
    "indirect_runout": 6,
    "catch_bonus_3": 4,     # 3+ catches bonus
}

# ── Multipliers ─────────────────────────────────────────────
CAPTAIN_MULTIPLIER = 2.0
VICE_CAPTAIN_MULTIPLIER = 1.5


def calculate_batting_points(runs: int, balls: int, fours: int, sixes: int,
                              dismissed: bool, is_batter: bool = True) -> float:
    """Calculate fantasy batting points for an innings."""
    pts = 0.0

    # Base runs
    pts += runs * BATTING_POINTS["run"]

    # Boundary bonuses
    pts += fours * BATTING_POINTS["boundary_bonus"]
    pts += sixes * BATTING_POINTS["six_bonus"]

    # Milestone bonuses
    if runs >= 100:
        pts += BATTING_POINTS["century"]
    elif runs >= 50:
        pts += BATTING_POINTS["half_century"]

    # Duck penalty (batters/WK/AR only, not tailenders)
    if runs == 0 and dismissed and is_batter:
        pts += BATTING_POINTS["duck"]

    # Strike rate bonus/penalty (min 10 balls)
    if balls >= 10:
        sr = runs / balls * 100
        if sr >= 170:
            pts += BATTING_POINTS["strike_rate_170_plus"]
        elif sr >= 150:
            pts += BATTING_POINTS["strike_rate_150_170"]
        elif sr < 60:
            pts += BATTING_POINTS["strike_rate_below_60"]
        elif sr < 70:
            pts += BATTING_POINTS["strike_rate_60_70"]
        elif sr < 80:
            pts += BATTING_POINTS["strike_rate_70_80"]

    return pts


def calculate_bowling_points(wickets: int, overs: float, runs_conceded: int,
                              dot_balls: int = 0) -> float:
    """Calculate fantasy bowling points for a spell."""
    pts = 0.0

    # Wickets
    pts += wickets * BOWLING_POINTS["wicket"]

    # Wicket milestones
    if wickets >= 5:
        pts += BOWLING_POINTS["bonus_5_wickets"]
    elif wickets >= 4:
        pts += BOWLING_POINTS["bonus_4_wickets"]
    elif wickets >= 3:
        pts += BOWLING_POINTS["bonus_3_wickets"]

    # Economy (min 2 overs)
    if overs >= 2:
        econ = runs_conceded / overs
        if econ < 5:
            pts += BOWLING_POINTS["economy_below_5"]
        elif econ < 6:
            pts += BOWLING_POINTS["economy_5_6"]
        elif econ < 7:
            pts += BOWLING_POINTS["economy_6_7"]
        elif econ >= 12:
            pts += BOWLING_POINTS["economy_above_12"]
        elif econ >= 11:
            pts += BOWLING_POINTS["economy_11_12"]
        elif econ >= 10:
            pts += BOWLING_POINTS["economy_10_11"]

    # Maiden overs (approximate: 6 dots in a row)
    if overs >= 1 and dot_balls >= 6:
        maidens = dot_balls // 6  # rough estimate
        # Only count maidens if economy is very low
        if overs > 0 and runs_conceded / overs < 4:
            pts += min(maidens, int(overs)) * BOWLING_POINTS["maiden_over"]

    return pts


def calculate_fielding_points(catches: int, stumpings: int) -> float:
    """Calculate fantasy fielding points."""
    pts = 0.0
    pts += catches * FIELDING_POINTS["catch"]
    pts += stumpings * FIELDING_POINTS["stumping"]

    if catches >= 3:
        pts += FIELDING_POINTS["catch_bonus_3"]

    return pts


def calculate_total_fantasy_points(runs: int, balls: int, fours: int, sixes: int,
                                    dismissed: bool, wickets: int, overs: float,
                                    runs_conceded: int, dot_balls: int,
                                    catches: int, stumpings: int,
                                    is_batter: bool = True) -> float:
    """Calculate total Dream11 fantasy points for a player in a match."""
    bat = calculate_batting_points(runs, balls, fours, sixes, dismissed, is_batter)
    bowl = calculate_bowling_points(wickets, overs, runs_conceded, dot_balls)
    field = calculate_fielding_points(catches, stumpings)
    return round(bat + bowl + field, 1)
