import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "cricketiq.db")

WHITELIST_TEAMS = {
    "india", "australia", "england", "pakistan", "south africa",
    "new zealand", "sri lanka", "bangladesh", "west indies",
    "afghanistan", "ireland", "zimbabwe", "netherlands", "italy", "usa",
    "united states of america",
    "chennai super kings", "delhi capitals", "gujarat titans",
    "kolkata knight riders", "lucknow super giants", "mumbai indians",
    "punjab kings", "rajasthan royals", "royal challengers bengaluru",
    "royal challengers bangalore", "sunrisers hyderabad",
    # Acronyms often found in historical raw data or live feeds
    "csk", "dc", "gt", "kkr", "lsg", "mi", "pbks", "rr", "rcb", "srh",
    "ind", "aus", "eng", "pak", "rsa", "sa", "nz", "sl", "ban", "wi", "afg", "ire", "zim", "ned", "ita"
}

def is_whitelisted(team_str):
    if not team_str: return False
    t = team_str.strip().lower()
    for w in WHITELIST_TEAMS:
        if w == t or w in t: # e.g. 'india women' won't match if we want to exclude women. But 'india' vs 'india a' is risky.
            pass
    return t in WHITELIST_TEAMS

def clean_database():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("Purging database records for non-whitelisted teams...")

    # 1. Matches table
    cur.execute("SELECT id, team1, team2 FROM matches")
    bad_match_ids = []
    for row in cur.fetchall():
        t1, t2 = row["team1"].strip().lower(), row["team2"].strip().lower()
        if t1 not in WHITELIST_TEAMS or t2 not in WHITELIST_TEAMS:
            bad_match_ids.append(row["id"])
    
    # 2. Upcoming matches
    cur.execute("SELECT id, team1, team2 FROM upcoming_matches")
    bad_upcoming_ids = []
    for row in cur.fetchall():
        t1, t2 = row["team1"].strip().lower(), row["team2"].strip().lower()
        if t1 not in WHITELIST_TEAMS or t2 not in WHITELIST_TEAMS:
            bad_upcoming_ids.append(row["id"])

    # 3. Live matches
    cur.execute("SELECT id, team1, team2 FROM live_matches")
    bad_live_ids = []
    for row in cur.fetchall():
        t1, t2 = row["team1"].strip().lower(), row["team2"].strip().lower()
        if t1 not in WHITELIST_TEAMS or t2 not in WHITELIST_TEAMS:
            bad_live_ids.append(row["id"])

    # Exclusions
    print(f"Deleting {len(bad_match_ids)} historical matches")
    print(f"Deleting {len(bad_upcoming_ids)} upcoming matches")
    print(f"Deleting {len(bad_live_ids)} live matches")

    if bad_match_ids:
        placeholders = ",".join("?" for _ in bad_match_ids)
        cur.execute(f"DELETE FROM deliveries WHERE match_id IN ({placeholders})", bad_match_ids)
        cur.execute(f"DELETE FROM innings WHERE match_id IN ({placeholders})", bad_match_ids)
        cur.execute(f"DELETE FROM player_match_stats WHERE match_id IN ({placeholders})", bad_match_ids)
        cur.execute(f"DELETE FROM pvor_match WHERE match_id IN ({placeholders})", bad_match_ids)
        cur.execute(f"DELETE FROM predictions_log WHERE match_id IN ({placeholders})", bad_match_ids)
        cur.execute(f"DELETE FROM matches WHERE id IN ({placeholders})", bad_match_ids)

    if bad_upcoming_ids:
        placeholders = ",".join("?" for _ in bad_upcoming_ids)
        cur.execute(f"DELETE FROM upcoming_matches WHERE id IN ({placeholders})", bad_upcoming_ids)

    if bad_live_ids:
        placeholders = ",".join("?" for _ in bad_live_ids)
        cur.execute(f"DELETE FROM live_matches WHERE id IN ({placeholders})", bad_live_ids)
        
    # Also clean team lists like elo_ratings
    cur.execute("SELECT team_name FROM elo_ratings")
    bad_elo_teams = [r["team_name"] for r in cur.fetchall() if r["team_name"].strip().lower() not in WHITELIST_TEAMS]
    if bad_elo_teams:
        p = ",".join("?" for _ in bad_elo_teams)
        cur.execute(f"DELETE FROM elo_ratings WHERE team_name IN ({p})", bad_elo_teams)
        print(f"Deleted {len(bad_elo_teams)} non-whitelisted teams from elo_ratings")

    conn.commit()
    conn.close()
    print("Database purged successfully!")

if __name__ == "__main__":
    clean_database()
