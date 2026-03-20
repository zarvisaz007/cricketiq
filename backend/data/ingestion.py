"""
data/ingestion.py
Parses Cricsheet JSON files and loads them into SQLite.

Usage:
    python data/ingestion.py              # ingest all datasets
    python data/ingestion.py ipl          # ingest IPL only
    python data/ingestion.py t20s odis
"""
import json
import sys
import os
import sqlite3
from pathlib import Path
from typing import Optional

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection
from data.normalization import normalize_team, normalize_player, normalize_venue

RAW_DATA_PATH = Path("data/raw")

_FOLDER_TO_COMPETITION = {"ipl": "IPL", "t20s": "T20I", "odis": "ODI"}

def _folder_to_competition(folder_name: str) -> str:
    return _FOLDER_TO_COMPETITION.get(folder_name.lower(), folder_name.upper())


# ─── Parser ────────────────────────────────────────────────────────────────────

def parse_match(file_path: Path) -> Optional[dict]:
    """Parse a single Cricsheet JSON match file into structured data."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [SKIP] {file_path.name}: {e}")
        return None

    info = data.get("info", {})
    teams_raw = info.get("teams", [])
    teams = [normalize_team(t) for t in teams_raw]

    if len(teams) < 2:
        return None

    # Outcome
    outcome = info.get("outcome", {})
    winner_raw = outcome.get("winner")
    winner = normalize_team(winner_raw) if winner_raw else None
    result_by = outcome.get("by", {})
    result_margin = result_by.get("runs") or result_by.get("wickets")
    result_type = "runs" if "runs" in result_by else ("wickets" if "wickets" in result_by else None)

    toss = info.get("toss", {})
    dates = info.get("dates", [])

    match = {
        "match_type": info.get("match_type", "T20"),
        "team1": teams[0],
        "team2": teams[1],
        "venue": normalize_venue(info.get("venue", "")),
        "date": dates[0] if dates else None,
        "toss_winner": normalize_team(toss.get("winner", "")),
        "toss_decision": toss.get("decision"),
        "winner": winner,
        "result_margin": result_margin,
        "result_type": result_type,
        "source_file": file_path.name,
        "gender": info.get("gender", "male"),
        "competition": _folder_to_competition(file_path.parent.name),
    }

    # Parse innings → player stats
    player_stats = {}  # key: (player_name, team, innings_num)

    for innings_idx, innings in enumerate(data.get("innings", []), 1):
        batting_team = normalize_team(innings.get("team", ""))
        bowling_team = teams[1] if batting_team == teams[0] else teams[0]

        for over_data in innings.get("overs", []):
            for delivery in over_data.get("deliveries", []):
                batter = normalize_player(delivery.get("batter", ""))
                bowler = normalize_player(delivery.get("bowler", ""))
                runs_data = delivery.get("runs", {})
                batter_runs = runs_data.get("batter", 0)
                total_runs = runs_data.get("total", 0)
                extras = delivery.get("extras", {})

                # Batter stats
                b_key = (batter, batting_team, innings_idx)
                if b_key not in player_stats:
                    player_stats[b_key] = _empty_stats(batter, batting_team, innings_idx)
                s = player_stats[b_key]
                s["runs"] += batter_runs
                s["balls_faced"] += 1
                if batter_runs == 4:
                    s["fours"] += 1
                if batter_runs == 6:
                    s["sixes"] += 1

                # Bowler stats (only legal deliveries count for overs)
                bw_key = (bowler, bowling_team, innings_idx)
                if bw_key not in player_stats:
                    player_stats[bw_key] = _empty_stats(bowler, bowling_team, innings_idx)
                bw = player_stats[bw_key]
                bw["runs_conceded"] += total_runs
                # Count ball as legal if no wides/no-balls
                if "wides" not in extras and "noballs" not in extras:
                    bw["overs_bowled"] += 1 / 6
                    if total_runs == 0:
                        bw["dot_balls"] += 1

                # Wickets
                for wicket in delivery.get("wickets", []):
                    out_player = normalize_player(wicket.get("player_out", ""))
                    dm_key = (out_player, batting_team, innings_idx)
                    if dm_key not in player_stats:
                        player_stats[dm_key] = _empty_stats(out_player, batting_team, innings_idx)
                    player_stats[dm_key]["dismissed"] = 1

                    # Credit bowler (not run-outs or retired)
                    if wicket.get("kind") not in ("run out", "obstructing the field", "retired hurt", "retired out"):
                        bw["wickets"] += 1

    return {"match": match, "player_stats": list(player_stats.values())}


def _empty_stats(player_name: str, team: str, innings: int) -> dict:
    return {
        "player_name": player_name, "team": team, "innings": innings,
        "runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0, "dismissed": 0,
        "overs_bowled": 0.0, "runs_conceded": 0, "wickets": 0, "dot_balls": 0,
    }


# ─── Ingestor ──────────────────────────────────────────────────────────────────

def ingest_dataset(dataset_name: str):
    dataset_path = RAW_DATA_PATH / dataset_name
    if not dataset_path.exists():
        print(f"[{dataset_name}] Not found. Run: python scripts/download_data.py {dataset_name}")
        return

    json_files = [f for f in dataset_path.glob("*.json") if not f.name.endswith("_info.json")]
    print(f"[{dataset_name}] Ingesting {len(json_files)} files...")

    conn = get_connection()
    inserted = skipped = errors = 0

    for i, file_path in enumerate(json_files):
        if i % 500 == 0 and i > 0:
            print(f"  ... {i}/{len(json_files)} processed")

        result = parse_match(file_path)
        if not result:
            errors += 1
            continue

        match = result["match"]

        # Skip if already ingested
        if conn.execute("SELECT id FROM matches WHERE source_file = ?", (match["source_file"],)).fetchone():
            skipped += 1
            continue

        try:
            cursor = conn.execute(
                """INSERT INTO matches
                   (match_type, team1, team2, venue, date, toss_winner, toss_decision,
                    winner, result_margin, result_type, source_file, gender, competition)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (match["match_type"], match["team1"], match["team2"], match["venue"],
                 match["date"], match["toss_winner"], match["toss_decision"],
                 match["winner"], match["result_margin"], match["result_type"],
                 match["source_file"], match["gender"], match["competition"])
            )
            match_id = cursor.lastrowid

            conn.executemany(
                """INSERT INTO player_match_stats
                   (match_id, player_name, team, innings, runs, balls_faced, fours, sixes,
                    dismissed, overs_bowled, runs_conceded, wickets, dot_balls)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(match_id, s["player_name"], s["team"], s["innings"],
                  s["runs"], s["balls_faced"], s["fours"], s["sixes"],
                  s["dismissed"], s["overs_bowled"], s["runs_conceded"],
                  s["wickets"], s["dot_balls"])
                 for s in result["player_stats"]]
            )

            inserted += 1
            if inserted % 200 == 0:
                conn.commit()

        except sqlite3.Error as e:
            errors += 1
            conn.rollback()

    conn.commit()
    conn.close()
    print(f"[{dataset_name}] Inserted: {inserted} | Skipped: {skipped} | Errors: {errors}")


if __name__ == "__main__":
    datasets = sys.argv[1:] if len(sys.argv) > 1 else ["ipl", "t20s", "odis"]
    for ds in datasets:
        ingest_dataset(ds)
    print("\nIngestion complete. Run: python ratings/player_ratings.py")
