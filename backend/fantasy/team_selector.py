"""
fantasy/team_selector.py
Dream11 fantasy team optimizer using integer linear programming (PuLP).
Selects optimal 11 players subject to Dream11 constraints.

Constraints:
  - Exactly 11 players from both teams
  - Min 1, max 8 from each team
  - Min 1 WK, min 3 BAT, min 3 BOWL, min 1 AR
  - 100 credit budget
  - Captain (2x) + Vice-Captain (1.5x) selection
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection
from fantasy.expected_points import get_expected_fantasy_points
from fantasy.credit_values import estimate_credit_value
from features.player_features import get_player_role


def _get_squad(team: str, match_type: str = "T20") -> list:
    """Get recent squad with roles and stats."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT DISTINCT pms.player_name, COUNT(DISTINCT m.id) as games
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.id
        WHERE pms.team = ? AND m.match_type = ? AND m.gender = 'male'
        GROUP BY pms.player_name
        ORDER BY MAX(m.date) DESC
        LIMIT 15
    """, (team, match_type)).fetchall()
    conn.close()
    return [{"player": r["player_name"], "team": team, "games": r["games"]} for r in rows]


def _classify_role(role: str) -> str:
    """Map player role to Dream11 category."""
    role_lower = role.lower()
    if "keeper" in role_lower or role_lower == "wicketkeeper":
        return "WK"
    elif role_lower in ("batsman", "batter"):
        return "BAT"
    elif role_lower == "bowler":
        return "BOWL"
    elif role_lower in ("allrounder", "all-rounder"):
        return "AR"
    return "BAT"  # default


def select_dream11_team(team1: str, team2: str, match_type: str = "T20",
                         venue: str = None, budget: float = 100.0) -> dict:
    """
    Select optimal Dream11 fantasy XI using linear programming.

    Returns:
        {
            "team": [list of player dicts],
            "captain": player_name,
            "vice_captain": player_name,
            "total_credits": float,
            "total_expected_points": float,
            "constraints_met": bool,
        }
    """
    # Gather candidate pool
    squad1 = _get_squad(team1, match_type)
    squad2 = _get_squad(team2, match_type)

    candidates = []
    for p in squad1 + squad2:
        name = p["player"]
        team = p["team"]
        role_raw = get_player_role(name, match_type)
        role = _classify_role(role_raw)
        expected = get_expected_fantasy_points(name, match_type, venue=venue)
        credit = estimate_credit_value(name, match_type)

        candidates.append({
            "player": name,
            "team": team,
            "role": role,
            "d11_role": role,
            "credit": credit,
            "expected_points": expected["expected_points"],
            "batting_points": expected["batting_points"],
            "bowling_points": expected["bowling_points"],
            "fielding_points": expected["fielding_points"],
            "consistency": expected["consistency"],
        })

    # Try PuLP optimization
    try:
        return _optimize_with_pulp(candidates, team1, team2, budget)
    except ImportError:
        # Fallback: greedy selection
        return _greedy_selection(candidates, team1, team2, budget)


def _optimize_with_pulp(candidates, team1, team2, budget):
    """Use PuLP integer linear programming for optimal selection."""
    import pulp

    n = len(candidates)
    prob = pulp.LpProblem("Dream11", pulp.LpMaximize)

    # Binary decision variables: 1 if player selected
    x = [pulp.LpVariable(f"x_{i}", cat="Binary") for i in range(n)]

    # Objective: maximize expected fantasy points
    prob += pulp.lpSum(x[i] * candidates[i]["expected_points"] for i in range(n))

    # Constraint: exactly 11 players
    prob += pulp.lpSum(x) == 11

    # Budget constraint
    prob += pulp.lpSum(x[i] * candidates[i]["credit"] for i in range(n)) <= budget

    # Team balance: 1-8 from each team
    team1_idx = [i for i in range(n) if candidates[i]["team"] == team1]
    team2_idx = [i for i in range(n) if candidates[i]["team"] == team2]

    prob += pulp.lpSum(x[i] for i in team1_idx) >= 1
    prob += pulp.lpSum(x[i] for i in team1_idx) <= 8
    prob += pulp.lpSum(x[i] for i in team2_idx) >= 1
    prob += pulp.lpSum(x[i] for i in team2_idx) <= 8

    # Role constraints
    wk_idx = [i for i in range(n) if candidates[i]["d11_role"] == "WK"]
    bat_idx = [i for i in range(n) if candidates[i]["d11_role"] == "BAT"]
    bowl_idx = [i for i in range(n) if candidates[i]["d11_role"] == "BOWL"]
    ar_idx = [i for i in range(n) if candidates[i]["d11_role"] == "AR"]

    if wk_idx:
        prob += pulp.lpSum(x[i] for i in wk_idx) >= 1
        prob += pulp.lpSum(x[i] for i in wk_idx) <= 4
    if bat_idx:
        prob += pulp.lpSum(x[i] for i in bat_idx) >= 3
        prob += pulp.lpSum(x[i] for i in bat_idx) <= 6
    if bowl_idx:
        prob += pulp.lpSum(x[i] for i in bowl_idx) >= 3
        prob += pulp.lpSum(x[i] for i in bowl_idx) <= 6
    if ar_idx:
        prob += pulp.lpSum(x[i] for i in ar_idx) >= 1
        prob += pulp.lpSum(x[i] for i in ar_idx) <= 4

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if prob.status != 1:
        # Fallback if optimization fails
        return _greedy_selection(candidates, team1, team2, budget)

    # Extract selected team
    selected = [candidates[i] for i in range(n) if x[i].value() == 1]
    selected.sort(key=lambda p: -p["expected_points"])

    # Captain = highest expected, VC = second highest
    captain = selected[0]["player"] if selected else None
    vice_captain = selected[1]["player"] if len(selected) > 1 else None

    total_credits = sum(p["credit"] for p in selected)
    total_points = sum(p["expected_points"] for p in selected)

    # Apply captain/VC multipliers to total
    if captain:
        cap_pts = next((p["expected_points"] for p in selected if p["player"] == captain), 0)
        total_points += cap_pts  # 2x - 1x already counted = +1x
    if vice_captain:
        vc_pts = next((p["expected_points"] for p in selected if p["player"] == vice_captain), 0)
        total_points += vc_pts * 0.5  # 1.5x - 1x already counted = +0.5x

    return {
        "team": selected,
        "captain": captain,
        "vice_captain": vice_captain,
        "total_credits": round(total_credits, 1),
        "total_expected_points": round(total_points, 1),
        "constraints_met": True,
        "method": "pulp_optimization",
    }


def _greedy_selection(candidates, team1, team2, budget):
    """Greedy fallback: sort by value (points/credit) and select best valid team."""
    # Sort by value ratio
    for c in candidates:
        c["value"] = c["expected_points"] / max(c["credit"], 1)

    candidates.sort(key=lambda x: -x["value"])

    selected = []
    credits_used = 0
    team_counts = {team1: 0, team2: 0}
    role_counts = {"WK": 0, "BAT": 0, "BOWL": 0, "AR": 0}

    # First pass: ensure minimums
    for role, min_count in [("WK", 1), ("BAT", 3), ("BOWL", 3), ("AR", 1)]:
        role_candidates = [c for c in candidates if c["d11_role"] == role
                          and c not in selected]
        for c in role_candidates[:min_count]:
            if credits_used + c["credit"] <= budget and team_counts.get(c["team"], 0) < 8:
                selected.append(c)
                credits_used += c["credit"]
                team_counts[c["team"]] = team_counts.get(c["team"], 0) + 1
                role_counts[role] += 1

    # Fill remaining slots
    remaining = [c for c in candidates if c not in selected]
    for c in remaining:
        if len(selected) >= 11:
            break
        if credits_used + c["credit"] <= budget and team_counts.get(c["team"], 0) < 8:
            selected.append(c)
            credits_used += c["credit"]
            team_counts[c["team"]] = team_counts.get(c["team"], 0) + 1

    selected.sort(key=lambda p: -p["expected_points"])
    captain = selected[0]["player"] if selected else None
    vice_captain = selected[1]["player"] if len(selected) > 1 else None

    total_points = sum(p["expected_points"] for p in selected)
    if captain:
        total_points += next((p["expected_points"] for p in selected if p["player"] == captain), 0)
    if vice_captain:
        total_points += next((p["expected_points"] for p in selected if p["player"] == vice_captain), 0) * 0.5

    return {
        "team": selected,
        "captain": captain,
        "vice_captain": vice_captain,
        "total_credits": round(credits_used, 1),
        "total_expected_points": round(total_points, 1),
        "constraints_met": len(selected) == 11,
        "method": "greedy",
    }
