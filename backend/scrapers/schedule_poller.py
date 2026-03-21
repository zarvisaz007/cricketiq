"""
scrapers/schedule_poller.py
Background pollers for upcoming match schedules and playing XI.
Mirrors live_poller.py architecture.
"""
import sys
import os
import threading
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCHEDULE_INTERVAL = 6 * 3600   # 6 hours
XI_INTERVAL = 30 * 60          # 30 minutes

_schedule_thread = None
_xi_thread = None
_stop_event = threading.Event()


def _schedule_loop():
    """Poll upcoming matches every 6 hours."""
    from scrapers.cricbuzz_schedule import scrape_upcoming_matches, store_upcoming_matches

    print("[SchedulePoller] Started schedule polling...")
    while not _stop_event.is_set():
        try:
            matches = scrape_upcoming_matches()
            if matches:
                store_upcoming_matches(matches)
                print(f"[SchedulePoller] Updated {len(matches)} matches at "
                      f"{datetime.now().strftime('%H:%M:%S')}")
            else:
                print(f"[SchedulePoller] No matches found at "
                      f"{datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[SchedulePoller] Error: {e}")

        _stop_event.wait(timeout=SCHEDULE_INTERVAL)

    print("[SchedulePoller] Stopped.")


def _xi_loop():
    """Poll playing XI for matches starting within 2 hours, every 30 minutes."""
    from scrapers.cricbuzz_schedule import (
        get_upcoming_matches, scrape_playing_xi, store_upcoming_matches
    )

    print("[XIPoller] Started playing XI polling...")
    while not _stop_event.is_set():
        try:
            matches = get_upcoming_matches(days=1)
            now = datetime.now()
            soon = []

            for m in matches:
                start = m.get("start_time")
                if not start:
                    soon.append(m)  # Unknown time — try anyway
                    continue
                try:
                    st = datetime.fromisoformat(start.replace("Z", "+00:00").replace("+00:00", ""))
                except (ValueError, TypeError):
                    continue
                if st - now <= timedelta(hours=2):
                    soon.append(m)

            updated = []
            for m in soon:
                if m.get("playing_xi_team1") and len(m["playing_xi_team1"]) >= 11:
                    continue  # Already have XI

                xi = scrape_playing_xi(m["cricbuzz_match_id"], m.get("slug", ""))
                if xi["team1_xi"]:
                    m["playing_xi_team1"] = xi["team1_xi"]
                if xi["team2_xi"]:
                    m["playing_xi_team2"] = xi["team2_xi"]
                if xi["team1_xi"] or xi["team2_xi"]:
                    updated.append(m)

            if updated:
                store_upcoming_matches(updated)
                print(f"[XIPoller] Updated XI for {len(updated)} matches at "
                      f"{datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            print(f"[XIPoller] Error: {e}")

        _stop_event.wait(timeout=XI_INTERVAL)

    print("[XIPoller] Stopped.")


def start_schedule_poller():
    """Start the schedule polling thread."""
    global _schedule_thread
    if _schedule_thread and _schedule_thread.is_alive():
        print("[SchedulePoller] Already running.")
        return

    _stop_event.clear()
    _schedule_thread = threading.Thread(target=_schedule_loop, daemon=True)
    _schedule_thread.start()


def start_xi_poller():
    """Start the playing XI polling thread."""
    global _xi_thread
    if _xi_thread and _xi_thread.is_alive():
        print("[XIPoller] Already running.")
        return

    _stop_event.clear()
    _xi_thread = threading.Thread(target=_xi_loop, daemon=True)
    _xi_thread.start()


def stop_all_pollers():
    """Stop all background polling threads."""
    _stop_event.set()
    if _schedule_thread:
        _schedule_thread.join(timeout=5)
    if _xi_thread:
        _xi_thread.join(timeout=5)


if __name__ == "__main__":
    import time
    start_schedule_poller()
    start_xi_poller()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_all_pollers()
