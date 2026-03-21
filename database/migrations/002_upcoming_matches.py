"""
database/migrations/002_upcoming_matches.py
Adds upcoming_matches table for schedule tracking.

Safe to run multiple times (CREATE IF NOT EXISTS).

Usage:
    python database/migrations/002_upcoming_matches.py
"""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from database.db import get_connection


def run_migration():
    """Run the upcoming_matches migration."""
    conn = get_connection()
    print("[Migration 002] Adding upcoming_matches table...")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS upcoming_matches (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            cricbuzz_match_id   TEXT UNIQUE NOT NULL,
            team1               TEXT NOT NULL,
            team2               TEXT NOT NULL,
            venue               TEXT,
            match_type          TEXT DEFAULT 'T20',
            series_name         TEXT,
            start_time          TEXT,
            status              TEXT DEFAULT 'upcoming',
            playing_xi_team1    TEXT,
            playing_xi_team2    TEXT,
            slug                TEXT,
            last_updated        TEXT,
            created_at          TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_upcoming_status ON upcoming_matches(status);
        CREATE INDEX IF NOT EXISTS idx_upcoming_start ON upcoming_matches(start_time);
    """)

    conn.commit()
    conn.close()
    print("[Migration 002] upcoming_matches table created.")


if __name__ == "__main__":
    run_migration()
