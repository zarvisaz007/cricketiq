"""
scripts/nightly_retrain.py
Nightly retrain pipeline: download new data, ingest, retrain models, log metrics.

Usage:
    python3 scripts/nightly_retrain.py
    python3 scripts/nightly_retrain.py --skip-download
"""
import sys
import os
import subprocess
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def run_step(label, cmd):
    """Run a command and return success status."""
    print(f"\n  [{label}] Starting at {datetime.now().strftime('%H:%M:%S')}...")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  [{label}] Done.")
        return True
    else:
        print(f"  [{label}] FAILED: {result.stderr[:200]}")
        return False


def main():
    skip_download = "--skip-download" in sys.argv

    print("=" * 55)
    print(f"  CricketIQ Nightly Retrain — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    steps = []

    if not skip_download:
        steps.append(("Download Data", ["python3", "scripts/download_data.py"]))

    steps.extend([
        ("Ingest Data", ["python3", "backend/data/ingestion.py"]),
        ("Compute Ratings", ["python3", "backend/ratings/player_ratings.py"]),
        ("Train Models", ["python3", "backend/models/train_all.py"]),
        ("Train IPL Model", ["python3", "backend/models/ipl_predictor.py"]),
        ("Seed Venues", ["python3", "database/seed_venues.py"]),
    ])

    failed = []
    for label, cmd in steps:
        if not run_step(label, cmd):
            failed.append(label)

    print("\n" + "=" * 55)
    if failed:
        print(f"  Retrain completed with {len(failed)} failure(s): {', '.join(failed)}")
    else:
        print("  Retrain completed successfully.")

    # Backfill prediction outcomes
    try:
        from models.prediction_tracker import backfill_outcomes
        backfill_outcomes()
    except Exception:
        pass

    print("=" * 55)


if __name__ == "__main__":
    main()
