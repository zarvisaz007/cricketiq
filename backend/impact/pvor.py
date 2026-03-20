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
from features.team_features import get_team_squad

N_WITH = 1000    # simulations for "with player" scenario


def _resolve_player_name(player_name: str, team: str, match_type: str) -> str:
    """
    Resolve player name to the exact Cricsheet format by matching against
    the team's recent squad. Falls back to original input if no match found.
    Handles cases like 'Jasprit Bumrah' → 'JJ Bumrah'.
    """
    squad = get_team_squad(team, match_type, last_n_matches=20)
    name_lower = player_name.lower()

    # Exact match first
    if player_name in squad:
        return player_name

    # Try last name match
    last_name = player_name.split()[-1].lower()
    candidates = [p for p in squad if last_name in p.lower()]
    if len(candidates) == 1:
        return candidates[0]

    # Try first name / initials match
    first_word = player_name.split()[0].lower()
    candidates = [p for p in squad if first_word in p.lower()]
    if len(candidates) == 1:
        return candidates[0]

    # Try full substring match
    candidates = [p for p in squad if name_lower in p.lower() or p.lower() in name_lower]
    if len(candidates) == 1:
        return candidates[0]

    return player_name  # fallback to original
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
    # Resolve player name to Cricsheet format
    resolved_name = _resolve_player_name(player_name, team, match_type)
    if resolved_name != player_name:
        print(f"  [PVOR] Resolved '{player_name}' → '{resolved_name}'")

    # P(win with player) — normal simulation
    with_result = simulate_match(team, opponent, match_type, n_simulations=N_WITH)
    win_with = with_result["team1_win_pct"]

    # P(win without player) — squad minus this player
    win_without = simulate_without_player(resolved_name, team, opponent, match_type, n=N_WITHOUT)

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
        "player": resolved_name,
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
