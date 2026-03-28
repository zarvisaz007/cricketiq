#!/usr/bin/env python3
"""
start_bot.py — CricketIQ Telegram Bot launcher.

Usage:
    python start_bot.py          # start the bot
    python start_bot.py --kill   # kill any running bot instance
    python start_bot.py --check  # check if bot is running

Press Ctrl+C to stop.
"""
import os
import sys
import signal
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

BANNER = """
╔══════════════════════════════════════════════╗
║   🏏  CricketIQ Bot — starting up...        ║
╚══════════════════════════════════════════════╝
"""


def _kill_old_instances():
    """Kill any previously running CricketIQ bot processes."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "bot.main"],
            capture_output=True, text=True
        )
        my_pid = os.getpid()
        pids = [int(p) for p in result.stdout.split() if p.strip() and int(p) != my_pid]
        if pids:
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"  Stopped old bot instance (PID {pid})")
                except ProcessLookupError:
                    pass
            import time
            time.sleep(2)
        return len(pids)
    except Exception:
        return 0


def _check_env():
    """Verify .env exists and TELEGRAM_BOT_TOKEN is set."""
    env_file = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_file):
        print("ERROR: .env file not found. Copy .env.example to .env and set TELEGRAM_BOT_TOKEN.")
        sys.exit(1)

    # Load .env manually to check
    token = None
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if not token or token in ("your_bot_token_here", ""):
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("  1. Open .env")
        print("  2. Set TELEGRAM_BOT_TOKEN=your_token_from_botfather")
        sys.exit(1)

    return token


def _is_running():
    """Check if bot is already running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "bot.main"],
            capture_output=True, text=True
        )
        pids = [p.strip() for p in result.stdout.split() if p.strip()]
        return pids
    except Exception:
        return []


def main():
    if "--kill" in sys.argv:
        killed = _kill_old_instances()
        if killed:
            print(f"Stopped {killed} bot instance(s).")
        else:
            print("No running bot instances found.")
        return

    if "--check" in sys.argv:
        pids = _is_running()
        if pids:
            print(f"Bot is running (PID: {', '.join(pids)})")
        else:
            print("Bot is not running.")
        return

    print(BANNER)

    # Kill any stale instances
    killed = _kill_old_instances()
    if killed:
        print(f"  Stopped {killed} old instance(s) first.\n")

    # Check environment
    token = _check_env()
    print("  Token: set")
    print(f"  DB: database/cricketiq.db")
    print(f"  Logs: bot.log\n")

    # Start the bot
    print("  Starting bot... (Ctrl+C to stop)\n")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bot.main"],
            cwd=PROJECT_ROOT
        )
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\nBot stopped. Goodbye!")


if __name__ == "__main__":
    main()
