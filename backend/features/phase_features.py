"""
features/phase_features.py
T20 phase analysis: powerplay (1-6), middle (7-15), death (16-20).
Computes phase-specific run rates, economy, wicket rates from deliveries table.
"""
import sys
import os
from functools import lru_cache
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection

# T20 phase boundaries (over numbers are 0-indexed in deliveries)
PHASES = {
    "powerplay": (0, 5),   # overs 1-6
    "middle":    (6, 14),  # overs 7-15
    "death":     (15, 19), # overs 16-20
}


@lru_cache(maxsize=2048)
def _get_team_phase_stats(team: str, match_type: str, phase: str,
                          last_n_matches: int = 10) -> dict:
    """
    Get aggregated stats for a team in a specific T20 phase.
    Returns runs, balls, wickets in that phase across recent matches.
    """
    start_over, end_over = PHASES[phase]
    conn = get_connection()

    # Get recent match IDs for this team
    match_ids = conn.execute("""
        SELECT DISTINCT m.id FROM matches m
        JOIN deliveries d ON d.match_id = m.id
        WHERE m.match_type = ? AND m.gender = 'male'
          AND d.batting_team = ?
        ORDER BY m.date DESC
        LIMIT ?
    """, (match_type, team, last_n_matches)).fetchall()

    if not match_ids:
        conn.close()
        return {"runs": 0, "balls": 0, "wickets": 0}

    ids = [r["id"] for r in match_ids]
    placeholders = ",".join("?" for _ in ids)

    row = conn.execute(f"""
        SELECT COALESCE(SUM(total_runs), 0) as runs,
               COUNT(*) as balls,
               COUNT(wicket_kind) as wickets
        FROM deliveries
        WHERE match_id IN ({placeholders})
          AND batting_team = ?
          AND over_number BETWEEN ? AND ?
          AND extra_type IS NULL OR extra_type NOT IN ('wides', 'noballs')
    """, ids + [team, start_over, end_over]).fetchone()
    conn.close()

    return {
        "runs": row["runs"] if row else 0,
        "balls": row["balls"] if row else 0,
        "wickets": row["wickets"] if row else 0,
    }


def get_phase_run_rate(team: str, match_type: str, phase: str,
                       last_n: int = 10) -> float:
    """Returns run rate (runs per over) for a team in a phase."""
    stats = _get_team_phase_stats(team, match_type, phase, last_n)
    overs = stats["balls"] / 6 if stats["balls"] > 0 else 0
    return round(stats["runs"] / overs, 2) if overs > 0 else 0.0


def get_phase_wicket_rate(team: str, match_type: str, phase: str,
                          last_n: int = 10) -> float:
    """Returns wickets lost per over for a team in a phase."""
    stats = _get_team_phase_stats(team, match_type, phase, last_n)
    overs = stats["balls"] / 6 if stats["balls"] > 0 else 0
    return round(stats["wickets"] / overs, 2) if overs > 0 else 0.0


@lru_cache(maxsize=2048)
def _get_bowling_phase_stats(team: str, match_type: str, phase: str,
                             last_n_matches: int = 10) -> dict:
    """Get bowling stats for a team (when they bowl) in a phase."""
    start_over, end_over = PHASES[phase]
    conn = get_connection()

    match_ids = conn.execute("""
        SELECT DISTINCT m.id FROM matches m
        JOIN deliveries d ON d.match_id = m.id
        WHERE m.match_type = ? AND m.gender = 'male'
          AND d.bowling_team = ?
        ORDER BY m.date DESC
        LIMIT ?
    """, (match_type, team, last_n_matches)).fetchall()

    if not match_ids:
        conn.close()
        return {"runs_conceded": 0, "balls": 0, "wickets_taken": 0}

    ids = [r["id"] for r in match_ids]
    placeholders = ",".join("?" for _ in ids)

    row = conn.execute(f"""
        SELECT COALESCE(SUM(total_runs), 0) as runs_conceded,
               COUNT(*) as balls,
               COUNT(wicket_kind) as wickets_taken
        FROM deliveries
        WHERE match_id IN ({placeholders})
          AND bowling_team = ?
          AND over_number BETWEEN ? AND ?
    """, ids + [team, start_over, end_over]).fetchone()
    conn.close()

    return {
        "runs_conceded": row["runs_conceded"] if row else 0,
        "balls": row["balls"] if row else 0,
        "wickets_taken": row["wickets_taken"] if row else 0,
    }


def get_phase_economy(team: str, match_type: str, phase: str,
                      last_n: int = 10) -> float:
    """Returns bowling economy in a phase (when team bowls)."""
    stats = _get_bowling_phase_stats(team, match_type, phase, last_n)
    overs = stats["balls"] / 6 if stats["balls"] > 0 else 0
    return round(stats["runs_conceded"] / overs, 2) if overs > 0 else 0.0


def get_phase_feature_vector(team1: str, team2: str, match_type: str) -> dict:
    """
    Returns all phase-related features as diffs between teams.
    Positive = team1 advantage.
    """
    features = {}
    for phase in ["powerplay", "middle", "death"]:
        rr1 = get_phase_run_rate(team1, match_type, phase)
        rr2 = get_phase_run_rate(team2, match_type, phase)
        econ1 = get_phase_economy(team1, match_type, phase)
        econ2 = get_phase_economy(team2, match_type, phase)
        wr1 = get_phase_wicket_rate(team1, match_type, phase)
        wr2 = get_phase_wicket_rate(team2, match_type, phase)

        features[f"{phase}_run_rate_diff"] = round(rr1 - rr2, 2)
        features[f"{phase}_economy_diff"] = round(econ2 - econ1, 2)  # inverted: lower econ is better
        features[f"{phase}_wicket_rate_diff"] = round(wr2 - wr1, 2)  # inverted: fewer wickets lost is better

    return features
