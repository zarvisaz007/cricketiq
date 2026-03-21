"""
features/ipl_season.py
IPL season tracker: points table, NRR, playoff probability simulator.
"""
import sys
import os
import numpy as np
from collections import defaultdict

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection


def get_points_table(season: str = None) -> list:
    """
    Get IPL points table for a season.
    Returns sorted list of teams with W/L/NR/Points/NRR.
    """
    conn = get_connection()

    if season is None:
        # Get most recent IPL season
        row = conn.execute("""
            SELECT MAX(SUBSTR(date, 1, 4)) as season FROM matches
            WHERE competition = 'IPL'
        """).fetchone()
        season = row["season"] if row and row["season"] else "2024"

    matches = conn.execute("""
        SELECT team1, team2, winner, result_margin, result_type, date
        FROM matches
        WHERE competition = 'IPL' AND date LIKE ? AND gender = 'male'
        ORDER BY date ASC
    """, (f"{season}%",)).fetchall()
    conn.close()

    teams = defaultdict(lambda: {
        "played": 0, "won": 0, "lost": 0, "no_result": 0,
        "points": 0, "nrr": 0.0
    })

    for m in matches:
        t1, t2, winner = m["team1"], m["team2"], m["winner"]
        teams[t1]["played"] += 1
        teams[t2]["played"] += 1

        if winner is None:
            teams[t1]["no_result"] += 1
            teams[t2]["no_result"] += 1
            teams[t1]["points"] += 1
            teams[t2]["points"] += 1
        elif winner == t1:
            teams[t1]["won"] += 1
            teams[t1]["points"] += 2
            teams[t2]["lost"] += 1
        elif winner == t2:
            teams[t2]["won"] += 1
            teams[t2]["points"] += 2
            teams[t1]["lost"] += 1

    # Sort by points desc, then NRR
    table = []
    for team, stats in teams.items():
        win_pct = stats["won"] / stats["played"] * 100 if stats["played"] > 0 else 0
        table.append({
            "team": team,
            "played": stats["played"],
            "won": stats["won"],
            "lost": stats["lost"],
            "no_result": stats["no_result"],
            "points": stats["points"],
            "win_pct": round(win_pct, 1),
        })

    table.sort(key=lambda x: (-x["points"], -x["win_pct"]))

    # Add position
    for i, t in enumerate(table, 1):
        t["position"] = i

    return table


def get_ipl_teams(season: str = None) -> list:
    """Get all IPL teams for a season."""
    conn = get_connection()
    if season is None:
        row = conn.execute("""
            SELECT MAX(SUBSTR(date, 1, 4)) as season FROM matches
            WHERE competition = 'IPL'
        """).fetchone()
        season = row["season"] if row and row["season"] else "2024"

    rows = conn.execute("""
        SELECT DISTINCT team1 AS team FROM matches
        WHERE competition = 'IPL' AND date LIKE ?
        UNION
        SELECT DISTINCT team2 AS team FROM matches
        WHERE competition = 'IPL' AND date LIKE ?
        ORDER BY team
    """, (f"{season}%", f"{season}%")).fetchall()
    conn.close()
    return [r["team"] for r in rows]


def simulate_playoff_probabilities(season: str = None,
                                    n_simulations: int = 5000) -> list:
    """
    Monte Carlo simulation of remaining IPL matches to estimate
    playoff qualification probability for each team.
    """
    table = get_points_table(season)
    if not table:
        return []

    conn = get_connection()
    if season is None:
        row = conn.execute("""
            SELECT MAX(SUBSTR(date, 1, 4)) as season FROM matches
            WHERE competition = 'IPL'
        """).fetchone()
        season = row["season"] if row and row["season"] else "2024"

    # Get completed match results for win probability estimation
    completed = conn.execute("""
        SELECT team1, team2, winner FROM matches
        WHERE competition = 'IPL' AND date LIKE ? AND winner IS NOT NULL
    """, (f"{season}%",)).fetchall()
    conn.close()

    # Build win probability matrix from completed matches
    win_counts = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # [wins, total]
    for m in completed:
        pair = tuple(sorted([m["team1"], m["team2"]]))
        win_counts[pair[0]][pair[1]][1] += 1
        win_counts[pair[1]][pair[0]][1] += 1
        if m["winner"] == pair[0]:
            win_counts[pair[0]][pair[1]][0] += 1
        else:
            win_counts[pair[1]][pair[0]][0] += 1

    teams = [t["team"] for t in table]
    current_points = {t["team"]: t["points"] for t in table}

    # For each team, count how many times they finish top 4
    playoff_counts = defaultdict(int)

    for _ in range(n_simulations):
        sim_points = dict(current_points)

        # Simulate remaining matches (simplified: each team plays ~14 total)
        for t in table:
            remaining = 14 - t["played"]
            if remaining <= 0:
                continue
            # Estimate wins based on current win%
            win_rate = t["won"] / t["played"] if t["played"] > 0 else 0.5
            sim_wins = np.random.binomial(remaining, win_rate)
            sim_points[t["team"]] += sim_wins * 2

        # Sort by simulated points
        ranked = sorted(teams, key=lambda x: sim_points[x], reverse=True)
        for team in ranked[:4]:
            playoff_counts[team] += 1

    # Convert to percentages
    results = []
    for t in table:
        prob = round(playoff_counts.get(t["team"], 0) / n_simulations * 100, 1)
        results.append({
            "team": t["team"],
            "current_points": t["points"],
            "played": t["played"],
            "won": t["won"],
            "lost": t["lost"],
            "playoff_prob": prob,
        })

    results.sort(key=lambda x: -x["playoff_prob"])
    return results
