"""
features/feature_registry.py
Central feature registry for all ML models.
Defines feature names, defaults, and the master build function.
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

# ── Feature Definitions ────────────────────────────────────────

FEATURE_COLS = [
    # Team strength (4)
    "strength_diff",
    "strength1_norm",
    "strength2_norm",
    "form_diff",

    # Elo (3)
    "elo_prob",
    "elo_diff",
    "elo1_norm",

    # H2H (3)
    "h2h_win_pct",
    "h2h_decay_pct",
    "h2h_win_streak",

    # Venue (6)
    "venue_batting_factor",
    "venue_spin_factor",
    "venue_pace_factor",
    "venue_dew_factor",
    "venue_avg_first_score",
    "home_advantage_diff",

    # Toss (1)
    "toss_advantage",

    # Form (2)
    "form1_norm",
    "form2_norm",

    # Phase analysis — T20 only (9)
    "powerplay_run_rate_diff",
    "powerplay_economy_diff",
    "powerplay_wicket_rate_diff",
    "middle_run_rate_diff",
    "middle_economy_diff",
    "middle_wicket_rate_diff",
    "death_run_rate_diff",
    "death_economy_diff",
    "death_wicket_rate_diff",
]

# Default values when data is unavailable
FEATURE_DEFAULTS = {
    "strength_diff": 0.0,
    "strength1_norm": 0.5,
    "strength2_norm": 0.5,
    "form_diff": 0.0,
    "elo_prob": 0.5,
    "elo_diff": 0.0,
    "elo1_norm": 0.5,
    "h2h_win_pct": 0.5,
    "h2h_decay_pct": 0.5,
    "h2h_win_streak": 0.0,
    "venue_batting_factor": 1.0,
    "venue_spin_factor": 1.0,
    "venue_pace_factor": 1.0,
    "venue_dew_factor": 0.0,
    "venue_avg_first_score": 160.0,
    "home_advantage_diff": 0.0,
    "toss_advantage": 0.5,
    "form1_norm": 0.5,
    "form2_norm": 0.5,
    "powerplay_run_rate_diff": 0.0,
    "powerplay_economy_diff": 0.0,
    "powerplay_wicket_rate_diff": 0.0,
    "middle_run_rate_diff": 0.0,
    "middle_economy_diff": 0.0,
    "middle_wicket_rate_diff": 0.0,
    "death_run_rate_diff": 0.0,
    "death_economy_diff": 0.0,
    "death_wicket_rate_diff": 0.0,
}


def build_feature_vector(team1: str, team2: str, venue: str, match_type: str,
                         toss_winner: str = None, include_phases: bool = True) -> dict:
    """
    Build the full feature vector for a match prediction.
    Returns dict with all features from FEATURE_COLS.
    Falls back to defaults for any feature that errors.
    """
    features = dict(FEATURE_DEFAULTS)

    # Team strength
    try:
        from features.team_features import get_team_strength, get_team_recent_form, get_head_to_head
        s1 = get_team_strength(team1, match_type, venue)
        s2 = get_team_strength(team2, match_type, venue)
        f1 = get_team_recent_form(team1, match_type)
        f2 = get_team_recent_form(team2, match_type)
        h2h = get_head_to_head(team1, team2, match_type)

        features["strength_diff"] = s1 - s2
        features["strength1_norm"] = s1 / 100.0
        features["strength2_norm"] = s2 / 100.0
        features["form_diff"] = f1 - f2
        features["form1_norm"] = f1 / 100.0
        features["form2_norm"] = f2 / 100.0
        features["h2h_win_pct"] = h2h["team1_win_pct"] / 100.0
        features["h2h_decay_pct"] = h2h.get("h2h_decay_pct", h2h["team1_win_pct"]) / 100.0
        features["h2h_win_streak"] = float(h2h.get("team1_win_streak", 0))
    except Exception:
        pass

    # Elo
    try:
        from models.elo import get_elo, _elo_prob
        elo1 = get_elo(team1, match_type)
        elo2 = get_elo(team2, match_type)
        features["elo_prob"] = _elo_prob(elo1, elo2)
        features["elo_diff"] = elo1 - elo2
        features["elo1_norm"] = elo1 / 3000.0  # normalize to ~0-1
    except Exception:
        pass

    # Venue
    try:
        from features.venue_features import get_venue_feature_vector
        if venue:
            vf = get_venue_feature_vector(venue, team1, team2, match_type)
            for k, v in vf.items():
                if k in features:
                    features[k] = v
    except Exception:
        pass

    # Toss
    if toss_winner == team1:
        features["toss_advantage"] = 1.0
    elif toss_winner == team2:
        features["toss_advantage"] = 0.0
    else:
        features["toss_advantage"] = 0.5

    # Phase analysis (T20 only, skip if no deliveries data)
    if include_phases and match_type == "T20":
        try:
            from features.phase_features import get_phase_feature_vector
            pf = get_phase_feature_vector(team1, team2, match_type)
            for k, v in pf.items():
                if k in features:
                    features[k] = v
        except Exception:
            pass

    return features


def feature_vector_to_list(features: dict) -> list:
    """Convert feature dict to ordered list matching FEATURE_COLS."""
    return [features.get(col, FEATURE_DEFAULTS.get(col, 0.0)) for col in FEATURE_COLS]


def get_feature_count() -> int:
    """Returns total number of features."""
    return len(FEATURE_COLS)
