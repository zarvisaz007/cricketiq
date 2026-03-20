"""
models/train_all.py
Trains all models (Elo, Logistic, XGBoost) for all match formats.

Run after ingesting data:
    python models/train_all.py
"""
import sys
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from models.elo import build_elo_from_history
from models.logistic import train as train_logistic
from models.xgboost_model import train as train_xgb
from ratings.player_ratings import update_all_ratings

FORMATS = ["T20", "ODI", "Test"]

if __name__ == "__main__":
    print("=" * 50)
    print("CricketIQ — Training All Models")
    print("=" * 50)

    print("\n[1/4] Computing player ratings...")
    for fmt in FORMATS:
        update_all_ratings(fmt)

    print("\n[2/4] Building Elo ratings...")
    for fmt in FORMATS:
        build_elo_from_history(fmt)

    print("\n[3/4] Training Logistic Regression...")
    for fmt in ["T20", "ODI"]:
        train_logistic(fmt)

    print("\n[4/4] Training XGBoost...")
    for fmt in ["T20", "ODI"]:
        train_xgb(fmt)

    print("\nAll models trained. Run: python test_cli.py")
