"""
database/migrations/001_schema_v2.py
CricketIQ v2 schema migration.

Adds 9 new tables + columns to existing tables + performance indices.
Safe to run multiple times (all CREATE/ALTER are IF NOT EXISTS or wrapped in try/except).

Usage:
    python database/migrations/001_schema_v2.py
"""
import sys
import os
import sqlite3

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from database.db import get_connection


def _add_column(conn, table, column, col_type, default=None):
    """Add a column if it doesn't already exist."""
    try:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}")
        print(f"  [+] {table}.{column}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            pass  # already exists
        else:
            raise


def run_migration():
    """Run the v2 schema migration."""
    conn = get_connection()
    print("[Migration 001] Starting schema v2 upgrade...")

    # ── 1. New tables ──────────────────────────────────────────

    conn.executescript("""

        -- Venues: pitch characteristics and ground metadata
        CREATE TABLE IF NOT EXISTS venues (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE NOT NULL,
            city            TEXT,
            country         TEXT,
            batting_factor  REAL DEFAULT 1.0,
            spin_factor     REAL DEFAULT 1.0,
            pace_factor     REAL DEFAULT 1.0,
            dew_factor      REAL DEFAULT 0.0,
            avg_first_innings_score REAL DEFAULT 160.0,
            avg_second_innings_score REAL DEFAULT 150.0,
            matches_played  INTEGER DEFAULT 0
        );

        -- Tournaments: IPL seasons, ICC events, bilateral series
        CREATE TABLE IF NOT EXISTS tournaments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            season          TEXT,
            format          TEXT,
            importance      REAL DEFAULT 1.0,
            start_date      TEXT,
            end_date        TEXT,
            UNIQUE(name, season)
        );

        -- Innings: per-innings summary (for live scores + phase analysis)
        CREATE TABLE IF NOT EXISTS innings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        INTEGER NOT NULL,
            innings_number  INTEGER NOT NULL,
            batting_team    TEXT NOT NULL,
            bowling_team    TEXT NOT NULL,
            total_runs      INTEGER DEFAULT 0,
            total_wickets   INTEGER DEFAULT 0,
            total_overs     REAL DEFAULT 0.0,
            extras          INTEGER DEFAULT 0,
            target          INTEGER,
            is_complete     INTEGER DEFAULT 0,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            UNIQUE(match_id, innings_number)
        );

        -- Deliveries: ball-by-ball data (for matchups + phase stats)
        CREATE TABLE IF NOT EXISTS deliveries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        INTEGER NOT NULL,
            innings_number  INTEGER NOT NULL,
            over_number     INTEGER NOT NULL,
            ball_number     INTEGER NOT NULL,
            batter          TEXT NOT NULL,
            bowler          TEXT NOT NULL,
            non_striker     TEXT,
            batter_runs     INTEGER DEFAULT 0,
            extra_runs      INTEGER DEFAULT 0,
            total_runs      INTEGER DEFAULT 0,
            extra_type      TEXT,
            wicket_kind     TEXT,
            wicket_player   TEXT,
            batting_team    TEXT,
            bowling_team    TEXT,
            FOREIGN KEY (match_id) REFERENCES matches(id)
        );

        -- Predictions log: track every prediction + actual outcome
        CREATE TABLE IF NOT EXISTS predictions_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        INTEGER,
            match_type      TEXT,
            team1           TEXT NOT NULL,
            team2           TEXT NOT NULL,
            venue           TEXT,
            predicted_at    TEXT NOT NULL,
            model_name      TEXT,
            team1_win_prob  REAL NOT NULL,
            ensemble_prob   REAL,
            confidence      TEXT,
            actual_winner   TEXT,
            was_correct     INTEGER,
            FOREIGN KEY (match_id) REFERENCES matches(id)
        );

        -- Model records: ML model versions + accuracy metrics
        CREATE TABLE IF NOT EXISTS model_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name      TEXT NOT NULL,
            model_version   TEXT,
            match_type      TEXT,
            trained_at      TEXT NOT NULL,
            train_samples   INTEGER,
            val_accuracy    REAL,
            brier_score     REAL,
            log_loss        REAL,
            feature_count   INTEGER,
            hyperparams     TEXT,
            model_path      TEXT,
            notes           TEXT
        );

        -- PVOR per match: per-player per-match PVOR values
        CREATE TABLE IF NOT EXISTS pvor_match (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        INTEGER NOT NULL,
            player_name     TEXT NOT NULL,
            team            TEXT NOT NULL,
            match_type      TEXT,
            batting_pvor    REAL DEFAULT 0.0,
            bowling_pvor    REAL DEFAULT 0.0,
            fielding_pvor   REAL DEFAULT 0.0,
            total_pvor      REAL DEFAULT 0.0,
            computed_at     TEXT,
            FOREIGN KEY (match_id) REFERENCES matches(id),
            UNIQUE(match_id, player_name)
        );

        -- PVOR aggregated: rolling player PVOR stats
        CREATE TABLE IF NOT EXISTS pvor_player_agg (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name     TEXT NOT NULL,
            match_type      TEXT NOT NULL,
            pvor_last_30d   REAL DEFAULT 0.0,
            pvor_last_90d   REAL DEFAULT 0.0,
            pvor_career     REAL DEFAULT 0.0,
            matches_30d     INTEGER DEFAULT 0,
            matches_90d     INTEGER DEFAULT 0,
            matches_career  INTEGER DEFAULT 0,
            last_updated    TEXT,
            UNIQUE(player_name, match_type)
        );

        -- Live matches: active live match tracking
        CREATE TABLE IF NOT EXISTS live_matches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id        INTEGER,
            cricbuzz_match_id TEXT UNIQUE,
            team1           TEXT,
            team2           TEXT,
            match_type      TEXT,
            status          TEXT DEFAULT 'live',
            current_innings INTEGER DEFAULT 1,
            score_summary   TEXT,
            last_polled     TEXT,
            started_at      TEXT,
            FOREIGN KEY (match_id) REFERENCES matches(id)
        );
    """)
    print("  [+] 9 new tables created")

    # ── 2. Add columns to existing tables ──────────────────────

    print("\n  Adding columns to matches...")
    _add_column(conn, "matches", "venue_id", "INTEGER", "NULL")
    _add_column(conn, "matches", "tournament_id", "INTEGER", "NULL")
    _add_column(conn, "matches", "cricbuzz_match_id", "TEXT", "NULL")

    print("  Adding columns to player_match_stats...")
    _add_column(conn, "player_match_stats", "batting_position", "INTEGER", "NULL")
    _add_column(conn, "player_match_stats", "bowling_slot", "INTEGER", "NULL")
    _add_column(conn, "player_match_stats", "catches", "INTEGER", 0)
    _add_column(conn, "player_match_stats", "stumpings", "INTEGER", 0)

    conn.commit()

    # ── 3. Performance indices ─────────────────────────────────

    print("\n  Creating indices...")
    indices = [
        ("idx_matches_date", "matches(date)"),
        ("idx_matches_type_date", "matches(match_type, date)"),
        ("idx_matches_venue_id", "matches(venue_id)"),
        ("idx_matches_tournament_id", "matches(tournament_id)"),
        ("idx_matches_cricbuzz_id", "matches(cricbuzz_match_id)"),
        ("idx_matches_competition", "matches(competition)"),
        ("idx_pms_player_match", "player_match_stats(player_name, match_id)"),
        ("idx_pms_team", "player_match_stats(team)"),
        ("idx_pms_match_id", "player_match_stats(match_id)"),
        ("idx_deliveries_match_innings", "deliveries(match_id, innings_number)"),
        ("idx_deliveries_batter", "deliveries(batter)"),
        ("idx_deliveries_bowler", "deliveries(bowler)"),
        ("idx_deliveries_over", "deliveries(match_id, innings_number, over_number)"),
        ("idx_innings_match", "innings(match_id)"),
        ("idx_predictions_match", "predictions_log(match_id)"),
        ("idx_predictions_date", "predictions_log(predicted_at)"),
        ("idx_pvor_match_player", "pvor_match(match_id, player_name)"),
        ("idx_pvor_agg_player", "pvor_player_agg(player_name, match_type)"),
        ("idx_live_matches_status", "live_matches(status)"),
        ("idx_elo_team_type", "elo_ratings(team_name, match_type)"),
        ("idx_player_ratings_name_type", "player_ratings(player_name, match_type)"),
    ]

    for idx_name, idx_def in indices:
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
            print(f"  [+] {idx_name}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()
    print("\n[Migration 001] Schema v2 upgrade complete.")


if __name__ == "__main__":
    run_migration()
