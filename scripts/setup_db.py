"""
scripts/setup_db.py
Run once to initialize the CricketIQ database.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db

if __name__ == "__main__":
    print("Setting up CricketIQ database...")
    init_db()
    print("Done. Run: python scripts/download_data.py")
