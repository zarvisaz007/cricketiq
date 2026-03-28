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
from scrapers.cricbuzz_live import _parse_teams_from_slug
from database.db import get_connection


# Map slug keywords to user-friendly series labels
SERIES_LABELS = {
    "ipl": "IPL",
    "indian-premier-league": "IPL",
    "pakistan-super-league": "PSL",
    "psl": "PSL",
    "big-bash": "BBL",
    "bbl": "BBL",
    "cpl": "CPL",
    "caribbean-premier-league": "CPL",
    "sa20": "SA20",
    "the-hundred": "The 100",
    "legends-league": "LLC",
    "plunket-shield": "Test",
    "sheffield-shield": "Test",
    "ranji": "Test",
    "test": "Test",
    "odi": "ODI",
    "one-day": "ODI",
    "t20i": "T20I",
    "t20-world-cup": "T20 WC",
    "world-cup": "WC",
    "asia-cup": "Asia Cup",
    "champions-trophy": "CT",
}


def _detect_series_label(slug: str) -> str:
    """Detect a user-friendly series/format label from the URL slug."""
    slug_lower = slug.lower()
    for keyword, label in SERIES_LABELS.items():
        if keyword in slug_lower:
            return label
    # Fallback: generic T20
    return "T20"

SCHEDULE_URLS = [
    "https://www.cricbuzz.com/cricket-schedule/upcoming-series/international",
    "https://www.cricbuzz.com/cricket-schedule/upcoming-series/domestic",
]

# Alias mapping for team name normalization
TEAM_ALIASES = {
    # IPL
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
    # International
    "Rsa": "South Africa",
    "Nz": "New Zealand",
    "Aus": "Australia",
    "Ind": "India",
    "Eng": "England",
    "Pak": "Pakistan",
    "Sl": "Sri Lanka",
    "Ban": "Bangladesh",
    "Wi": "West Indies",
    "Afg": "Afghanistan",
    "Ire": "Ireland",
    "Zim": "Zimbabwe",
    "Sco": "Scotland",
    "Npl": "Nepal",
    "Oman": "Oman",
    "Usa": "USA",
    "Ned": "Netherlands",
    "Uae": "UAE",
    "Nam": "Namibia",
    # International Women
    "Rsaw": "SA Women",
    "Nzw": "NZ Women",
    "Ausw": "AUS Women",
    "Indw": "IND Women",
    "Engw": "ENG Women",
    "Wiw": "WI Women",
    # PSL
    "Lhq": "Lahore Qalandars",
    "Hydk": "Hyderabad Kings",
    "Islu": "Islamabad United",
    "Kk": "Karachi Kings",
    "Ms": "Multan Sultans",
    "Pz": "Peshawar Zalmi",
    "Qg": "Quetta Gladiators",
    # NZ domestic
    "Akl": "Auckland",
    "Cntbry": "Canterbury",
    "Cd": "Central Districts",
    "Nd": "Northern Districts",
    "Otg": "Otago",
    "Wel": "Wellington",
    # SA domestic
    "Tit": "Titans",
    "Lions": "Lions",
    "Dol": "Dolphins",
    "Kng": "Knights",
    "War": "Warriors",
    "Cri": "Cape Cobras",
    "Bor": "Boland",
    "Kznin": "KZN Inland",
    "Nwest": "North West",
    "Sla": "SWD",
    "Wpr": "Western Province",
    "Ngaw": "Northerns",
    # AU domestic
    "Saus": "South Australia",
    "Vic": "Victoria",
    "Nza": "NZ A",
    # Legends / Other
    "Indt": "India Legends",
    "Knso": "Kings",
    "Rrp": "Rajputs",
    "Snss": "Senses",
    # African teams
    "Gh": "Ghana",
    "Shn": "St Helena",
    "Sey": "Seychelles",
    "Tan": "Tanzania",
    "Mwi": "Malawi",
    "Swt": "Eswatini",
    "Rwaw": "Rwanda Women",
    "Ghw": "Ghana Women",
    "Rsawu19": "SA Women U19",
    "Zimwu19": "ZIM Women U19",
}


def _normalize_team(name: str) -> str:
    """Normalize team name using alias mapping. Strip match descriptors."""
    name = name.strip()
    # Remove common suffixes that leak from slugs (e.g. "Vic Final Sheffield Shield")
    for suffix in [
        " Semi Final", " Final ", " Qualifier ", " Division ",
        " Provincial ", " Sheffield ", " Plunket ", " Ranji ",
    ]:
        idx = name.find(suffix)
        if idx > 0:
            name = name[:idx].strip()
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
            match_type = _detect_series_label(slug)

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
            match_type = _detect_series_label(slug)

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


# ── Main-event filter ─────────────────────────────────────────

WHITELIST_TEAMS = {
    "india", "australia", "england", "pakistan", "south africa",
    "new zealand", "sri lanka", "bangladesh", "west indies",
    "afghanistan", "ireland", "zimbabwe", "netherlands", "italy", "usa",
    "united states of america",
    "chennai super kings", "delhi capitals", "gujarat titans",
    "kolkata knight riders", "lucknow super giants", "mumbai indians",
    "punjab kings", "rajasthan royals", "royal challengers bengaluru",
    "royal challengers bangalore", "sunrisers hyderabad",
    # Common abbreviations/acronyms
    "csk", "dc", "gt", "kkr", "lsg", "mi", "pbks", "rr", "rcb", "srh",
    "ind", "aus", "eng", "pak", "rsa", "sa", "nz", "sl", "ban", "wi", "afg", "ire", "zim", "ned", "ita"
}

def is_main_event(match: dict) -> bool:
    """Strict filter: only extremely specific whitelisted teams are permitted."""
    t1 = (match.get("team1") or match.get("team_a") or "").lower()
    t2 = (match.get("team2") or match.get("team_b") or "").lower()

    # Exclude women's and U19 matches
    if "women" in t1 or "u19" in t1 or "women" in t2 or "u19" in t2:
        return False

    return t1 in WHITELIST_TEAMS and t2 in WHITELIST_TEAMS


def get_upcoming_matches(days: int = 7, match_type: str = None,
                         main_only: bool = True) -> list:
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

    if main_only:
        result = [m for m in result if is_main_event(m)]

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
