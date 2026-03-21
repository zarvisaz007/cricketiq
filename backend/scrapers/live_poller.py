"""
scrapers/live_poller.py
Background daemon that polls Cricbuzz for live match updates.
Runs in a separate thread, polls every 30-60 seconds.
"""
import sys
import os
import time
import threading
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection
from scrapers.cricbuzz_live import get_live_matches, fetch_live_scorecard, store_live_scorecard

POLL_INTERVAL = 45  # seconds
_poller_thread = None
_stop_event = threading.Event()


def _poll_loop():
    """Main polling loop — runs in background thread."""
    print("[LivePoller] Started background polling...")

    while not _stop_event.is_set():
        try:
            matches = get_live_matches()
            if matches:
                conn = get_connection()
                for m in matches:
                    try:
                        scorecard = fetch_live_scorecard(m["cricbuzz_id"])
                        if scorecard:
                            scorecard["team_a"] = m.get("team_a", scorecard.get("team_a", ""))
                            scorecard["team_b"] = m.get("team_b", scorecard.get("team_b", ""))
                            scorecard["match_type"] = m.get("match_type", "T20")
                            store_live_scorecard(scorecard, conn)
                    except Exception as e:
                        print(f"[LivePoller] Error updating {m.get('cricbuzz_id')}: {e}")
                conn.close()
                print(f"[LivePoller] Updated {len(matches)} matches at {datetime.now().strftime('%H:%M:%S')}")
            else:
                print(f"[LivePoller] No live matches at {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            print(f"[LivePoller] Poll error: {e}")

        _stop_event.wait(timeout=POLL_INTERVAL)

    print("[LivePoller] Stopped.")


def start_poller():
    """Start the background polling thread."""
    global _poller_thread
    if _poller_thread and _poller_thread.is_alive():
        print("[LivePoller] Already running.")
        return

    _stop_event.clear()
    _poller_thread = threading.Thread(target=_poll_loop, daemon=True)
    _poller_thread.start()


def stop_poller():
    """Stop the background polling thread."""
    _stop_event.set()
    if _poller_thread:
        _poller_thread.join(timeout=5)


def get_cached_live_matches() -> list:
    """Get live matches from the database cache (from last poll)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM live_matches
        WHERE status = 'live'
        ORDER BY last_polled DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_live_match_detail(cricbuzz_id: str) -> dict:
    """Fetch fresh scorecard for a specific match."""
    return fetch_live_scorecard(cricbuzz_id)


if __name__ == "__main__":
    start_poller()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_poller()
