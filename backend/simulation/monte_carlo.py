"""
simulation/monte_carlo.py
Monte Carlo match simulation engine.

Simulates N matches between two teams by sampling from
each player's performance distribution. Returns win probabilities.

Method:
- For each simulation, sample batting and bowling performance
  using Gamma distribution (models cricket scores well)
- Team score = sum of sampled player contributions
- Winner = team with higher net performance
"""
import sys
import os
import numpy as np
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from features.team_features import get_team_squad, get_team_strength
from ratings.player_ratings import get_player_rating

DEFAULT_SIMULATIONS = 2000


def _sample_team_performance(team: str, match_type: str) -> float:
    """
    Sample a team's match performance score from player rating distributions.
    Uses Gamma distribution to model natural skewness of cricket scores.
    """
    squad = get_team_squad(team, match_type, last_n_matches=5)[:11]
    if not squad:
        # Fallback: use team strength directly
        return get_team_strength(team, match_type) + np.random.normal(0, 10)

    performance = 0.0
    for player in squad:
        rating = get_player_rating(player, match_type)
        overall = rating["overall_rating"]
        form = rating["form_score"]

        # Blend rating and form for the "expected" performance
        expected = overall * 0.7 + form * 0.3

        # Sample from Gamma distribution
        # shape=2 gives right-skewed distribution (like cricket scores)
        # scale = expected/2 normalizes it
        scale = max(expected / 2, 1.0)
        sampled = np.random.gamma(shape=2.0, scale=scale)
        performance += sampled

    return performance


def simulate_match(team1: str, team2: str, match_type: str,
                   n_simulations: int = DEFAULT_SIMULATIONS) -> dict:
    """
    Run N Monte Carlo simulations and return win probabilities.

    Returns:
        {
            "team1": team1,
            "team2": team2,
            "team1_win_pct": 63.5,
            "team2_win_pct": 36.5,
            "confidence": "High",
            "simulations": 2000,
        }
    """
    team1_wins = 0

    for _ in range(n_simulations):
        score1 = _sample_team_performance(team1, match_type)
        score2 = _sample_team_performance(team2, match_type)
        if score1 > score2:
            team1_wins += 1

    team1_pct = round(team1_wins / n_simulations * 100, 1)
    team2_pct = round(100 - team1_pct, 1)

    # Confidence based on how decisive the result is
    margin = abs(team1_pct - 50)
    if margin >= 20:
        confidence = "High"
    elif margin >= 10:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "team1": team1,
        "team2": team2,
        "team1_win_pct": team1_pct,
        "team2_win_pct": team2_pct,
        "confidence": confidence,
        "simulations": n_simulations,
    }


def simulate_without_player(player_name: str, team: str, opponent: str,
                              match_type: str, n: int = 1000) -> float:
    """
    Simulate team win % WITHOUT a specific player.
    Used by PVOR engine to compute player impact.
    Returns P(team wins without player).
    """
    # Temporarily exclude this player from squad simulation
    squad = get_team_squad(team, match_type)[:12]
    squad_without = [p for p in squad if p != player_name][:11]

    team_wins = 0
    for _ in range(n):
        # Team WITHOUT player
        performance = 0.0
        for player in squad_without:
            rating = get_player_rating(player, match_type)
            overall = rating["overall_rating"]
            form = rating["form_score"]
            expected = overall * 0.7 + form * 0.3
            scale = max(expected / 2, 1.0)
            performance += np.random.gamma(shape=2.0, scale=scale)

        # Opponent normal performance
        opp_perf = _sample_team_performance(opponent, match_type)

        if performance > opp_perf:
            team_wins += 1

    return round(team_wins / n * 100, 1)
