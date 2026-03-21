"""
scrapers/cricbuzz_schedule.py
Scrape upcoming match schedules and playing XI from Cricbuzz.
"""
import sys
import os
import re
import json
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scrapers.http_client import get_page
from scrapers.cricbuzz_live import _parse_teams_from_slug, _detect_match_type
from database.db import get_connection

SCHEDULE_URLS = [
    "https://www.cricbuzz.com/cricket-schedule/upcoming-series/international",
    "https://www.cricbuzz.com/cricket-schedule/upcoming-series/domestic",
]

# Alias mapping for team name normalization
TEAM_ALIASES = {
    "Royal Challengers Bengaluru": "Royal Challengers Bangalore",
    "Kings Xi Punjab": "Punjab Kings",
    "Delhi Daredevils": "Delhi Capitals",
    "Deccan Chargers": "Sunrisers Hyderabad",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
    "Rcb": "Royal Challengers Bangalore",
    "Csk": "Chennai Super Kings",
    "Mi": "Mumbai Indians",
    "Kkr": "Kolkata Knight Riders",
    "Dc": "Delhi Capitals",
    "Srh": "Sunrisers Hyderabad",
    "Rr": "Rajasthan Royals",
    "Pbks": "Punjab Kings",
    "Lsg": "Lucknow Super Giants",
    "Gt": "Gujarat Titans",
}


def _normalize_team(name: str) -> str:
    """Normalize team name using alias mapping."""
    name = name.strip()
    return TEAM_ALIASES.get(name, name)


def scrape_upcoming_matches() -> list:
    """
    Scrape Cricbuzz schedule pages for upcoming matches.
    Returns list of match dicts.
    """
    matches = []
    seen_ids = set()

    for url in SCHEDULE_URLS:
        try:
            resp = get_page(url)
            html = resp.text
        except Exception as e:
            print(f"[Schedule] Failed to fetch {url}: {e}")
            continue

        # Extract match links: /live-cricket-scores/{id}/{slug}
        pattern = r'href="/live-cricket-scores/(\d+)/([^"]*)"'
        for m in re.finditer(pattern, html):
            match_id = m.group(1)
            slug = m.group(2)

            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)

            teams = _parse_teams_from_slug(slug)
            if len(teams) < 2:
                continue

            team1 = _normalize_team(teams[0])
            team2 = _normalize_team(teams[1])
            match_type = _detect_match_type(slug)

            matches.append({
                "cricbuzz_match_id": match_id,
                "team1": team1,
                "team2": team2,
                "match_type": match_type,
                "slug": slug,
                "status": "upcoming",
            })

        # Also try /cricket-match/ pattern for scheduled matches
        pattern2 = r'href="/cricket-match/(\d+)/([^"]*)"'
        for m in re.finditer(pattern2, html):
            match_id = m.group(1)
            slug = m.group(2)

            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)

            teams = _parse_teams_from_slug(slug)
            if len(teams) < 2:
                continue

            team1 = _normalize_team(teams[0])
            team2 = _normalize_team(teams[1])
            match_type = _detect_match_type(slug)

            matches.append({
                "cricbuzz_match_id": match_id,
                "team1": team1,
                "team2": team2,
                "match_type": match_type,
                "slug": slug,
                "status": "upcoming",
            })

    # Extract date/time and series info from match detail pages
    for match in matches[:20]:  # Limit to first 20 to avoid rate limiting
        try:
            _enrich_match_detail(match)
        except Exception as e:
            print(f"[Schedule] Error enriching {match['cricbuzz_match_id']}: {e}")

    return matches


def _enrich_match_detail(match: dict):
    """Enrich match with venue, date, and series info from detail page."""
    slug = match.get("slug", "")
    match_id = match["cricbuzz_match_id"]
    url = f"https://www.cricbuzz.com/live-cricket-scores/{match_id}/{slug}"

    try:
        resp = get_page(url)
        html = resp.text
    except Exception:
        return

    # Extract venue
    venue_match = re.search(r'(?:Venue|Stadium)[:\s]*([^<]+)', html, re.IGNORECASE)
    if venue_match:
        match["venue"] = venue_match.group(1).strip()

    # Extract series name
    series_match = re.search(r'(?:Series|Tournament)[:\s]*([^<]+)', html, re.IGNORECASE)
    if series_match:
        match["series_name"] = series_match.group(1).strip()

    # Extract date/time — look for ISO format or common patterns
    time_match = re.search(r'"startDate"\s*:\s*"([^"]+)"', html)
    if time_match:
        match["start_time"] = time_match.group(1)
    else:
        # Try timestamp pattern
        ts_match = re.search(r'data-timestamp="(\d{13})"', html)
        if ts_match:
            ts = int(ts_match.group(1)) / 1000
            match["start_time"] = datetime.fromtimestamp(ts).isoformat()


def scrape_playing_xi(cricbuzz_match_id: str, slug: str = "") -> dict:
    """
    Scrape playing XI from a match detail page.
    Returns {team1_xi: [...], team2_xi: [...]}.
    """
    url = f"https://www.cricbuzz.com/live-cricket-scores/{cricbuzz_match_id}/{slug}"
    result = {"team1_xi": [], "team2_xi": []}

    try:
        resp = get_page(url)
        html = resp.text
    except Exception as e:
        print(f"[Schedule] Failed to fetch XI for {cricbuzz_match_id}: {e}")
        return result

    # Look for playing XI section — common patterns in Cricbuzz HTML
    xi_pattern = r'(?:Playing\s*XI|Squad)[^<]*</[^>]+>(.*?)(?:Playing\s*XI|Squad|Bench|$)'
    sections = re.findall(xi_pattern, html, re.DOTALL | re.IGNORECASE)

    # Fallback: extract player names from known patterns
    player_pattern = r'href="/profiles/\d+/([^"]+)"[^>]*>([^<]+)</a>'
    players_found = re.findall(player_pattern, html)

    # Split players into two teams (first 11 and next 11)
    if len(players_found) >= 22:
        result["team1_xi"] = [p[1].strip() for p in players_found[:11]]
        result["team2_xi"] = [p[1].strip() for p in players_found[11:22]]
    elif len(players_found) >= 11:
        result["team1_xi"] = [p[1].strip() for p in players_found[:11]]

    return result


def store_upcoming_matches(matches: list):
    """Upsert matches into the upcoming_matches table."""
    conn = get_connection()
    now = datetime.now().isoformat()

    for m in matches:
        playing_xi_1 = json.dumps(m.get("playing_xi_team1", [])) if m.get("playing_xi_team1") else None
        playing_xi_2 = json.dumps(m.get("playing_xi_team2", [])) if m.get("playing_xi_team2") else None

        conn.execute("""
            INSERT INTO upcoming_matches
                (cricbuzz_match_id, team1, team2, venue, match_type, series_name,
                 start_time, status, playing_xi_team1, playing_xi_team2, slug,
                 last_updated, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cricbuzz_match_id) DO UPDATE SET
                team1 = excluded.team1,
                team2 = excluded.team2,
                venue = COALESCE(excluded.venue, upcoming_matches.venue),
                match_type = excluded.match_type,
                series_name = COALESCE(excluded.series_name, upcoming_matches.series_name),
                start_time = COALESCE(excluded.start_time, upcoming_matches.start_time),
                status = excluded.status,
                playing_xi_team1 = COALESCE(excluded.playing_xi_team1, upcoming_matches.playing_xi_team1),
                playing_xi_team2 = COALESCE(excluded.playing_xi_team2, upcoming_matches.playing_xi_team2),
                last_updated = excluded.last_updated
        """, (
            m["cricbuzz_match_id"], m["team1"], m["team2"],
            m.get("venue"), m.get("match_type", "T20"), m.get("series_name"),
            m.get("start_time"), m.get("status", "upcoming"),
            playing_xi_1, playing_xi_2, m.get("slug"),
            now, now,
        ))

    conn.commit()
    conn.close()
    print(f"[Schedule] Stored/updated {len(matches)} upcoming matches")


def get_upcoming_matches(days: int = 7, match_type: str = None) -> list:
    """Query DB for upcoming matches."""
    conn = get_connection()
    query = "SELECT * FROM upcoming_matches WHERE status = 'upcoming'"
    params = []

    if match_type:
        query += " AND match_type = ?"
        params.append(match_type)

    query += " ORDER BY start_time ASC, created_at ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        # Parse playing XI JSON
        if d.get("playing_xi_team1"):
            try:
                d["playing_xi_team1"] = json.loads(d["playing_xi_team1"])
            except (json.JSONDecodeError, TypeError):
                d["playing_xi_team1"] = []
        if d.get("playing_xi_team2"):
            try:
                d["playing_xi_team2"] = json.loads(d["playing_xi_team2"])
            except (json.JSONDecodeError, TypeError):
                d["playing_xi_team2"] = []
        result.append(d)

    return result


def get_match_detail(cricbuzz_match_id: str) -> dict:
    """Get a single match from DB by cricbuzz ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM upcoming_matches WHERE cricbuzz_match_id = ?",
        (cricbuzz_match_id,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    d = dict(row)
    if d.get("playing_xi_team1"):
        try:
            d["playing_xi_team1"] = json.loads(d["playing_xi_team1"])
        except (json.JSONDecodeError, TypeError):
            d["playing_xi_team1"] = []
    if d.get("playing_xi_team2"):
        try:
            d["playing_xi_team2"] = json.loads(d["playing_xi_team2"])
        except (json.JSONDecodeError, TypeError):
            d["playing_xi_team2"] = []
    return d


if __name__ == "__main__":
    print("[Schedule] Scraping upcoming matches...")
    matches = scrape_upcoming_matches()
    print(f"[Schedule] Found {len(matches)} matches")
    if matches:
        store_upcoming_matches(matches)
    for m in matches[:5]:
        print(f"  {m['team1']} vs {m['team2']} ({m['match_type']}) — {m.get('start_time', 'TBD')}")
