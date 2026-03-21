"""
scripts/orchestrator.py
Automated multi-agent pipeline coordinator.

Watches docs/progress.md for completed phases and
automatically triggers the next phase.

Usage:
    python3 scripts/orchestrator.py              # run full pipeline
    python3 scripts/orchestrator.py --from ingest  # resume from ingestion
"""
import subprocess
import sys
import os
import re
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS_FILE = os.path.join(ROOT, "docs", "progress.md")


def read_progress() -> str:
    with open(PROGRESS_FILE) as f:
        return f.read()


def phase_done(phase_marker: str) -> bool:
    """Check if all tasks in a phase section are checked off."""
    content = read_progress()
    in_phase = False
    tasks = []

    for line in content.splitlines():
        if phase_marker in line:
            in_phase = True
            continue
        if in_phase:
            if line.startswith("## Phase") and phase_marker not in line:
                break
            if line.strip().startswith("- ["):
                tasks.append(line)

    if not tasks:
        return False
    return all("- [x]" in t for t in tasks)


def mark_done(task_text: str):
    """Mark a task as done in progress.md."""
    with open(PROGRESS_FILE) as f:
        content = f.read()
    # Find the task and check it off
    updated = content.replace(f"- [ ] {task_text}", f"- [x] {task_text}")
    with open(PROGRESS_FILE, "w") as f:
        f.write(updated)


def run_step(label: str, cmd: list) -> bool:
    """Run a command, print output, return success."""
    print(f"\n{'─'*55}")
    print(f"  [{label}] Starting...")
    print(f"  CMD: {' '.join(cmd)}")
    print(f"{'─'*55}")

    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode == 0:
        print(f"  [{label}] DONE ✓")
        return True
    else:
        print(f"  [{label}] FAILED (exit code {result.returncode})")
        return False


# ── Pipeline Steps ────────────────────────────────────────────

PIPELINE = [
    {
        "id": "install",
        "label": "Install Dependencies",
        "cmd": ["pip3", "install", "-r", "requirements.txt"],
        "phase": None,
    },
    {
        "id": "db",
        "label": "Initialize Database",
        "cmd": ["python3", "scripts/setup_db.py"],
        "phase": None,
    },
    {
        "id": "migrate",
        "label": "Run v2 Schema Migration",
        "cmd": ["python3", "database/migrations/001_schema_v2.py"],
        "phase": None,
        "depends_on": "db",
    },
    {
        "id": "seed_venues",
        "label": "Seed Venue Data",
        "cmd": ["python3", "database/seed_venues.py"],
        "phase": None,
        "depends_on": "migrate",
    },
    {
        "id": "download",
        "label": "Download Cricsheet Data",
        "cmd": ["python3", "scripts/download_data.py"],
        "phase": "Phase 1",
    },
    {
        "id": "ingest",
        "label": "Ingest Match Data",
        "cmd": ["python3", "backend/data/ingestion.py"],
        "phase": "Phase 1",
        "depends_on": "download",
    },
    {
        "id": "ratings",
        "label": "Compute Player Ratings",
        "cmd": ["python3", "backend/ratings/player_ratings.py"],
        "phase": "Phase 2",
        "depends_on": "ingest",
    },
    {
        "id": "train",
        "label": "Train All Models",
        "cmd": ["python3", "backend/models/train_all.py"],
        "phase": "Phase 3",
        "depends_on": "ratings",
    },
    {
        "id": "train_ipl",
        "label": "Train IPL Model",
        "cmd": ["python3", "backend/models/ipl_predictor.py"],
        "phase": "Phase 4",
        "depends_on": "train",
    },
]


def run_pipeline(start_from: str = None):
    print("\n  CricketIQ Orchestrator")
    print("  ═══════════════════════════")

    started = start_from is None
    failed_step = None

    for step in PIPELINE:
        if not started:
            if step["id"] == start_from:
                started = True
            else:
                print(f"  [SKIP] {step['label']}")
                continue

        success = run_step(step["label"], step["cmd"])

        if not success:
            print(f"\n  Pipeline stopped at: {step['label']}")
            print(f"  Fix the issue and resume with:")
            print(f"  python3 scripts/orchestrator.py --from {step['id']}")
            sys.exit(1)

    print("\n  ═══════════════════════════")
    print("  Pipeline complete.")
    print("  Run: python3 frontend/test_cli.py")


if __name__ == "__main__":
    start = None
    if "--from" in sys.argv:
        idx = sys.argv.index("--from")
        if idx + 1 < len(sys.argv):
            start = sys.argv[idx + 1]

    run_pipeline(start_from=start)
