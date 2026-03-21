"""
models/ipl_predictor.py
IPL-specific XGBoost model trained only on IPL data.
IPL dynamics differ from T20I (franchise vs national teams).
"""
import sys
import os
import joblib
import numpy as np
from pathlib import Path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection
from features.feature_registry import build_feature_vector, feature_vector_to_list, FEATURE_COLS
from features.ipl_features import get_ipl_feature_vector

MODEL_PATH = Path("models/xgb_IPL.pkl")

# IPL-specific features appended to base features
IPL_EXTRA_COLS = [
    "ipl_form_diff", "ipl_h2h_pct", "ipl_strength_diff",
    "ipl_home_advantage", "ipl_form1", "ipl_form2",
]


def _build_ipl_features(team1: str, team2: str, venue: str,
                         toss_winner: str = None, season: str = None) -> list:
    """Build feature vector with base + IPL-specific features."""
    base = build_feature_vector(team1, team2, venue, "T20", toss_winner, include_phases=True)
    base_list = feature_vector_to_list(base)

    ipl = get_ipl_feature_vector(team1, team2, venue, season)
    ipl_list = [ipl.get(c, 0.0) for c in IPL_EXTRA_COLS]

    return base_list + ipl_list


def train():
    """Train IPL-specific XGBoost model."""
    try:
        import xgboost as xgb
    except ImportError:
        print("[IPL] xgboost not installed.")
        return None

    from sklearn.model_selection import TimeSeriesSplit

    conn = get_connection()
    matches = conn.execute("""
        SELECT team1, team2, venue, toss_winner, winner, date FROM matches
        WHERE competition = 'IPL' AND gender = 'male' AND winner IS NOT NULL
        ORDER BY date ASC
    """).fetchall()
    conn.close()

    if len(matches) < 50:
        print(f"[IPL] Not enough data ({len(matches)} matches). Need 50+.")
        return None

    print(f"[IPL] Building features for {len(matches)} IPL matches...")

    X, y = [], []
    for m in matches:
        try:
            season = m["date"][:4] if m["date"] else None
            features = _build_ipl_features(m["team1"], m["team2"], m["venue"],
                                           m["toss_winner"], season)
            label = 1 if m["winner"] == m["team1"] else 0
            X.append(features)
            y.append(label)
        except Exception:
            continue

    X = np.array(X)
    y = np.array(y)

    # TimeSeriesSplit
    tscv = TimeSeriesSplit(n_splits=5)
    val_accs = []

    for train_idx, val_idx in tscv.split(X):
        model = xgb.XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
            eval_metric="logloss", random_state=42, verbosity=0,
        )
        model.fit(X[train_idx], y[train_idx],
                  eval_set=[(X[val_idx], y[val_idx])], verbose=False)
        val_accs.append((model.predict(X[val_idx]) == y[val_idx]).mean())

    # Final model on all data
    final = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        eval_metric="logloss", random_state=42, verbosity=0,
    )
    final.fit(X, y, verbose=False)

    path = str(MODEL_PATH)
    joblib.dump(final, path)

    avg_acc = np.mean(val_accs)
    print(f"[IPL] CV accuracy: {avg_acc:.2%} | Saved to {path}")

    try:
        from models.prediction_tracker import log_model_record
        log_model_record("xgboost_ipl", "T20", avg_acc, len(X),
                         feature_count=len(FEATURE_COLS) + len(IPL_EXTRA_COLS),
                         model_path=path)
    except Exception:
        pass

    return final


def predict(team1: str, team2: str, venue: str = None,
            toss_winner: str = None, season: str = None) -> float:
    """
    Returns P(team1 wins) using IPL-specific model.
    Falls back to generic T20 XGBoost if IPL model not trained.
    """
    if not MODEL_PATH.exists():
        from models.xgboost_model import predict as xgb_predict
        return xgb_predict(team1, team2, venue, "T20", toss_winner)

    model = joblib.load(str(MODEL_PATH))
    features = _build_ipl_features(team1, team2, venue, toss_winner, season)
    prob = model.predict_proba([features])[0][1]
    return round(float(prob), 4)


if __name__ == "__main__":
    train()
