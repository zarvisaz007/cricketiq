"""
impact/pvor.py
PVOR — Player Value Over Replacement

Measures how much a player increases their team's win probability.

PVOR = P(win WITH player) - P(win WITHOUT player)

A positive PVOR means the player meaningfully contributes to winning.
Higher = more impactful.
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from simulation.monte_carlo import simulate_match, simulate_without_player

N_WITH = 1000    # simulations for "with player" scenario
N_WITHOUT = 1000  # simulations for "without player" scenario


def compute_pvor(player_name: str, team: str, opponent: str, match_type: str) -> dict:
    """
    Compute PVOR for a player in a specific matchup.

    Returns:
        {
            "player": "Virat Kohli",
            "team": "India",
            "opponent": "Australia",
            "win_with": 64.2,
            "win_without": 59.7,
            "pvor": +4.5,
            "impact_label": "High"
        }
    """
    # P(win with player) — normal simulation
    with_result = simulate_match(team, opponent, match_type, n_simulations=N_WITH)
    win_with = with_result["team1_win_pct"]

    # P(win without player) — squad minus this player
    win_without = simulate_without_player(player_name, team, opponent, match_type, n=N_WITHOUT)

    pvor = round(win_with - win_without, 2)

    if pvor >= 5:
        impact_label = "Elite"
    elif pvor >= 3:
        impact_label = "High"
    elif pvor >= 1:
        impact_label = "Medium"
    elif pvor >= -1:
        impact_label = "Low"
    else:
        impact_label = "Negative"

    return {
        "player": player_name,
        "team": team,
        "opponent": opponent,
        "win_with": win_with,
        "win_without": win_without,
        "pvor": pvor,
        "impact_label": impact_label,
    }


def compute_team_pvor(team: str, opponent: str, match_type: str,
                       top_n: int = 11) -> list:
    """
    Compute PVOR for all players in a team's recent squad.
    Returns sorted list by PVOR (highest impact first).
    """
    from features.team_features import get_team_squad
    squad = get_team_squad(team, match_type)[:top_n]

    results = []
    for player in squad:
        result = compute_pvor(player, team, opponent, match_type)
        results.append(result)

    results.sort(key=lambda x: x["pvor"], reverse=True)
    return results
