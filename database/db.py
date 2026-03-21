"""
database/db.py
Manages SQLite connection and schema for CricketIQ.
"""
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "database/cricketiq.db")


def get_connection() -> sqlite3.Connection:
    """Return a database connection with row factory enabled."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""

        -- Players registry
        CREATE TABLE IF NOT EXISTS players (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    UNIQUE NOT NULL,
            role            TEXT,
            batting_style   TEXT,
            bowling_style   TEXT
        );

        -- Matches
        CREATE TABLE IF NOT EXISTS matches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_type      TEXT NOT NULL,
            team1           TEXT NOT NULL,
            team2           TEXT NOT NULL,
            venue           TEXT,
            date            TEXT,
            toss_winner     TEXT,
            toss_decision   TEXT,
            winner          TEXT,
            result_margin   INTEGER,
            result_type     TEXT,
            source_file     TEXT UNIQUE,
            gender          TEXT DEFAULT 'male',
            competition     TEXT
        );

        -- Per-match player stats (raw from Cricsheet)
        CREATE TABLE IF NOT EXISTS player_match_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        INTEGER NOT NULL,
            player_name     TEXT NOT NULL,
            team            TEXT NOT NULL,
            innings         INTEGER DEFAULT 1,
            runs            INTEGER DEFAULT 0,
            balls_faced     INTEGER DEFAULT 0,
            fours           INTEGER DEFAULT 0,
            sixes           INTEGER DEFAULT 0,
            dismissed       INTEGER DEFAULT 0,
            overs_bowled    REAL    DEFAULT 0.0,
            runs_conceded   INTEGER DEFAULT 0,
            wickets         INTEGER DEFAULT 0,
            dot_balls       INTEGER DEFAULT 0,
            FOREIGN KEY (match_id) REFERENCES matches(id)
        );

        -- Elo ratings per team per format
        CREATE TABLE IF NOT EXISTS elo_ratings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name       TEXT NOT NULL,
            match_type      TEXT NOT NULL,
            elo             REAL DEFAULT 1500.0,
            last_updated    TEXT,
            UNIQUE(team_name, match_type)
        );

        -- Computed player ratings (cached)
        CREATE TABLE IF NOT EXISTS player_ratings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name     TEXT NOT NULL,
            match_type      TEXT NOT NULL,
            batting_rating  REAL DEFAULT 50.0,
            bowling_rating  REAL DEFAULT 50.0,
            overall_rating  REAL DEFAULT 50.0,
            form_score      REAL DEFAULT 50.0,
            consistency     REAL DEFAULT 50.0,
            games_played    INTEGER DEFAULT 0,
            last_updated    TEXT,
            UNIQUE(player_name, match_type)
        );

    """)
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


def migrate_db():
    """Run all pending migrations."""
    import importlib
    mod = importlib.import_module("database.migrations.001_schema_v2")
    mod.run_migration()


if __name__ == "__main__":
    init_db()
