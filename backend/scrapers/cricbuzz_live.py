"""
scrapers/cricbuzz_live.py
Live match data from Cricbuzz. Dual strategy: JSON API first, HTML fallback.
Ported from Claude-cricket, adapted for CricketIQ's raw sqlite3 DB.
"""
import sys
import os
import re
import json

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from scrapers.http_client import get_page, get_json

CRICBUZZ_LIVE_URL = "https://www.cricbuzz.com/cricket-match/live-scores"
CRICBUZZ_SCORECARD_API = "https://www.cricbuzz.com/api/html/cricket-scorecard/{match_id}"
CRICBUZZ_COMMENTARY_API = "https://www.cricbuzz.com/api/cricket-match/{match_id}/full-commentary/1"


def get_live_matches() -> list:
    """
    Scrape Cricbuzz live scores page for active match IDs.
    Returns list of dicts: {cricbuzz_id, team_a, team_b, match_type, status}
    """
    try:
        resp = get_page(CRICBUZZ_LIVE_URL)
        html = resp.text
    except Exception as e:
        print(f"[Cricbuzz] Failed to fetch live page: {e}")
        return []

    matches = []

    # Extract match IDs from href patterns like /live-cricket-scores/12345/
    pattern = r'href="/live-cricket-scores/(\d+)/([^"]*)"'
    found_ids = set()

    for match in re.finditer(pattern, html):
        match_id = match.group(1)
        slug = match.group(2)

        if match_id in found_ids:
            continue
        found_ids.add(match_id)

        # Parse team names from slug: "team-a-vs-team-b-..."
        teams = _parse_teams_from_slug(slug)
        match_type = _detect_match_type(slug)

        matches.append({
            "cricbuzz_id": match_id,
            "team_a": teams[0] if teams else "Unknown",
            "team_b": teams[1] if len(teams) > 1 else "Unknown",
            "match_type": match_type,
            "status": "live",
            "slug": slug,
        })

    return matches


def fetch_live_scorecard(cricbuzz_match_id: str) -> dict:
    """
    Fetch live scorecard for a match.
    Tries JSON commentary API first, falls back to HTML parsing.
    Returns dict with innings data or None.
    """
    # Try commentary API
    try:
        url = CRICBUZZ_COMMENTARY_API.format(match_id=cricbuzz_match_id)
        data = get_json(url)
        if data and isinstance(data, dict):
            return _parse_commentary_api(data, cricbuzz_match_id)
    except Exception:
        pass

    # Fallback: HTML scorecard
    try:
        url = CRICBUZZ_SCORECARD_API.format(match_id=cricbuzz_match_id)
        resp = get_page(url)
        return _parse_html_scorecard(resp.text, cricbuzz_match_id)
    except Exception as e:
        print(f"[Cricbuzz] Failed to fetch scorecard for {cricbuzz_match_id}: {e}")
        return None


def _parse_commentary_api(data: dict, match_id: str) -> dict:
    """Parse the Cricbuzz commentary JSON API response."""
    result = {
        "cricbuzz_id": match_id,
        "innings": [],
    }

    match_header = data.get("matchHeader", {})
    result["team_a"] = match_header.get("team1", {}).get("name", "")
    result["team_b"] = match_header.get("team2", {}).get("name", "")
    result["status"] = match_header.get("status", "")
    result["match_type"] = match_header.get("matchFormat", "T20")

    # Parse mini-scorecard
    mini = data.get("miniscore", {})
    if mini:
        batter_striker = mini.get("batsmanStriker", {})
        batter_non = mini.get("batsmanNonStriker", {})
        bowler = mini.get("bowlerStriker", {})

        current_innings = {
            "batting_team": mini.get("matchScoreDetails", {}).get("inningsScoreList", [{}])[0].get("batTeamName", ""),
            "total_runs": mini.get("matchScoreDetails", {}).get("inningsScoreList", [{}])[0].get("score", 0),
            "total_wickets": mini.get("matchScoreDetails", {}).get("inningsScoreList", [{}])[0].get("wickets", 0),
            "total_overs": mini.get("matchScoreDetails", {}).get("inningsScoreList", [{}])[0].get("overs", 0),
            "current_batsmen": [
                {"name": batter_striker.get("batName", ""), "runs": batter_striker.get("batRuns", 0),
                 "balls": batter_striker.get("batBalls", 0)},
                {"name": batter_non.get("batName", ""), "runs": batter_non.get("batRuns", 0),
                 "balls": batter_non.get("batBalls", 0)},
            ],
            "current_bowler": {
                "name": bowler.get("bowlName", ""),
                "overs": bowler.get("bowlOvs", 0),
                "wickets": bowler.get("bowlWkts", 0),
                "runs": bowler.get("bowlRuns", 0),
            },
        }
        result["innings"].append(current_innings)

    # All innings from score list
    score_list = mini.get("matchScoreDetails", {}).get("inningsScoreList", [])
    for i, inn in enumerate(score_list):
        if i == 0:
            continue  # already added above
        result["innings"].append({
            "batting_team": inn.get("batTeamName", ""),
            "total_runs": inn.get("score", 0),
            "total_wickets": inn.get("wickets", 0),
            "total_overs": inn.get("overs", 0),
        })

    return result


def _parse_html_scorecard(html: str, match_id: str) -> dict:
    """Parse HTML scorecard as fallback."""
    result = {
        "cricbuzz_id": match_id,
        "innings": [],
        "status": "live",
    }

    # Simple regex extraction of scores from HTML
    score_pattern = r'(\d+)/(\d+)\s*\((\d+\.?\d*)\s*ov\)'
    for match in re.finditer(score_pattern, html):
        result["innings"].append({
            "total_runs": int(match.group(1)),
            "total_wickets": int(match.group(2)),
            "total_overs": float(match.group(3)),
        })

    return result if result["innings"] else None


def _parse_teams_from_slug(slug: str) -> list:
    """Extract team names from URL slug like 'india-vs-australia-1st-t20i'."""
    vs_match = re.search(r'^(.+?)-vs-(.+?)(?:-\d|$)', slug)
    if vs_match:
        team_a = vs_match.group(1).replace("-", " ").title()
        team_b = vs_match.group(2).replace("-", " ").title()
        return [team_a, team_b]
    return []


def _detect_match_type(slug: str) -> str:
    """Detect match type from URL slug."""
    slug_lower = slug.lower()
    if "t20" in slug_lower or "ipl" in slug_lower:
        return "T20"
    elif "odi" in slug_lower:
        return "ODI"
    elif "test" in slug_lower:
        return "Test"
    return "T20"  # default


def store_live_scorecard(scorecard: dict, conn):
    """
    Store or update live match data in live_matches and innings tables.
    """
    if not scorecard:
        return

    cricbuzz_id = scorecard.get("cricbuzz_id")
    from datetime import datetime
    now = datetime.now().isoformat()

    # Upsert live_matches
    existing = conn.execute("SELECT id, match_id FROM live_matches WHERE cricbuzz_match_id = ?",
                            (cricbuzz_id,)).fetchone()

    score_summary = ""
    for i, inn in enumerate(scorecard.get("innings", []), 1):
        team = inn.get("batting_team", f"Team {i}")
        runs = inn.get("total_runs", 0)
        wkts = inn.get("total_wickets", 0)
        overs = inn.get("total_overs", 0)
        score_summary += f"{team}: {runs}/{wkts} ({overs} ov) | "
    score_summary = score_summary.rstrip(" | ")

    if existing:
        conn.execute("""
            UPDATE live_matches SET status=?, score_summary=?, last_polled=?,
                current_innings=?
            WHERE cricbuzz_match_id=?
        """, (scorecard.get("status", "live"), score_summary, now,
              len(scorecard.get("innings", [])), cricbuzz_id))
    else:
        conn.execute("""
            INSERT INTO live_matches
                (cricbuzz_match_id, team1, team2, match_type, status,
                 score_summary, last_polled, started_at, current_innings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cricbuzz_id, scorecard.get("team_a", ""),
              scorecard.get("team_b", ""), scorecard.get("match_type", "T20"),
              "live", score_summary, now, now,
              len(scorecard.get("innings", []))))

    conn.commit()
