"""
models/elo.py
Elo rating system for teams.

P(win) = 1 / (1 + 10^(-(ELO_diff)/400))

Elo updates after each match:
  new_elo = old_elo + K * (actual - expected)
  K = 32 for T20/ODI, 24 for Tests
"""
import sys
import os
from datetime import datetime
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection

K_FACTORS = {"T20": 32, "ODI": 32, "Test": 24}
DEFAULT_ELO = 1500.0


def get_elo(team: str, match_type: str) -> float:
    """Get current Elo rating for a team."""
    conn = get_connection()
    row = conn.execute(
        "SELECT elo FROM elo_ratings WHERE team_name = ? AND match_type = ?",
        (team, match_type)
    ).fetchone()
    conn.close()
    return row["elo"] if row else DEFAULT_ELO


def set_elo(team: str, match_type: str, elo: float, conn=None):
    """Update Elo rating in the database."""
    close_after = conn is None
    if conn is None:
        conn = get_connection()

    conn.execute("""
        INSERT INTO elo_ratings (team_name, match_type, elo, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(team_name, match_type) DO UPDATE SET elo = excluded.elo, last_updated = excluded.last_updated
    """, (team, match_type, round(elo, 2), datetime.now().isoformat()))

    if close_after:
        conn.commit()
        conn.close()


def win_probability(team1: str, team2: str, match_type: str) -> float:
    """
    Returns P(team1 wins) using Elo ratings.
    Range: 0.0 to 1.0
    """
    elo1 = get_elo(team1, match_type)
    elo2 = get_elo(team2, match_type)
    return _elo_prob(elo1, elo2)


def _elo_prob(elo1: float, elo2: float) -> float:
    """Pure Elo probability formula."""
    return 1.0 / (1.0 + 10 ** (-(elo1 - elo2) / 400))


def update_after_match(winner: str, loser: str, match_type: str):
    """Update Elo ratings after a match result."""
    k = K_FACTORS.get(match_type, 32)
    winner_elo = get_elo(winner, match_type)
    loser_elo = get_elo(loser, match_type)

    expected_winner = _elo_prob(winner_elo, loser_elo)
    expected_loser = 1.0 - expected_winner

    new_winner_elo = winner_elo + k * (1 - expected_winner)
    new_loser_elo = loser_elo + k * (0 - expected_loser)

    conn = get_connection()
    set_elo(winner, match_type, new_winner_elo, conn)
    set_elo(loser, match_type, new_loser_elo, conn)
    conn.commit()
    conn.close()

    return new_winner_elo, new_loser_elo


def build_elo_from_history(match_type: str):
    """
    Replay all historical matches to build Elo ratings from scratch.
    Ordered by date — oldest first.
    Uses a single connection and in-memory cache to avoid DB lock contention.
    Only uses T20I/ODI international matches (excludes IPL and women's matches).
    """
    # Map match_type to competition code so IPL T20s are excluded
    competition = "T20I" if match_type == "T20" else match_type
    conn = get_connection()

    # Clear existing Elo for this format before rebuilding to remove stale rows
    conn.execute("DELETE FROM elo_ratings WHERE match_type = ?", (match_type,))
    conn.commit()

    matches = conn.execute("""
        SELECT team1, team2, winner FROM matches
        WHERE match_type = ? AND competition = ? AND gender = 'male' AND winner IS NOT NULL
        ORDER BY date ASC
    """, (match_type, competition)).fetchall()

    # In-memory Elo cache to avoid per-match DB reads
    elo_cache = {}
    k = K_FACTORS.get(match_type, 32)

    def cached_elo(team):
        return elo_cache.get(team, DEFAULT_ELO)

    print(f"[Elo] Building from {len(matches)} {match_type} matches...")
    for m in matches:
        winner = m["winner"]
        loser = m["team2"] if winner == m["team1"] else m["team1"]

        w_elo = cached_elo(winner)
        l_elo = cached_elo(loser)
        exp_w = _elo_prob(w_elo, l_elo)

        elo_cache[winner] = w_elo + k * (1 - exp_w)
        elo_cache[loser]  = l_elo + k * (0 - (1 - exp_w))

    # Bulk write final ratings
    now = datetime.now().isoformat()
    for team, elo in elo_cache.items():
        conn.execute("""
            INSERT INTO elo_ratings (team_name, match_type, elo, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(team_name, match_type) DO UPDATE SET elo = excluded.elo, last_updated = excluded.last_updated
        """, (team, match_type, round(elo, 2), now))

    conn.commit()
    conn.close()
    print(f"[Elo] Done.")


def get_top_elo_rankings(match_type: str, n: int = 20) -> list:
    """Returns top N teams by Elo rating."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT team_name, elo FROM elo_ratings
        WHERE match_type = ?
        ORDER BY elo DESC
        LIMIT ?
    """, (match_type, n)).fetchall()
    conn.close()
    return [{"team": r["team_name"], "elo": round(r["elo"], 1)} for r in rows]


if __name__ == "__main__":
    for fmt in ["T20", "ODI", "Test"]:
        build_elo_from_history(fmt)
        rankings = get_top_elo_rankings(fmt, 10)
        print(f"\nTop 10 {fmt} Elo Rankings:")
        for i, r in enumerate(rankings, 1):
            print(f"  {i:2}. {r['team']:<30} {r['elo']}")
