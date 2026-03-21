"""
models/logistic.py
Logistic Regression match prediction model v2.
Uses feature registry, TimeSeriesSplit, logs model records.
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
from features.feature_registry import (build_feature_vector, feature_vector_to_list,
                                        FEATURE_COLS)

MODEL_PATH = Path("models/logistic_{match_type}.pkl")


def _build_features(team1: str, team2: str, venue: str, match_type: str,
                    toss_winner: str = None) -> list:
    """Build feature vector using the feature registry."""
    fv = build_feature_vector(team1, team2, venue, match_type, toss_winner,
                              include_phases=(match_type == "T20"))
    return feature_vector_to_list(fv)


def train(match_type: str):
    """Train logistic regression on historical match data with TimeSeriesSplit."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import TimeSeriesSplit

    conn = get_connection()
    matches = conn.execute("""
        SELECT team1, team2, venue, toss_winner, winner FROM matches
        WHERE match_type = ? AND gender = 'male' AND winner IS NOT NULL
        ORDER BY date ASC
    """, (match_type,)).fetchall()
    conn.close()

    if len(matches) < 50:
        print(f"[Logistic/{match_type}] Not enough data ({len(matches)} matches). Need 50+.")
        return None

    print(f"[Logistic/{match_type}] Building {len(FEATURE_COLS)} features for {len(matches)} matches...")

    X, y = [], []
    for m in matches:
        try:
            features = _build_features(m["team1"], m["team2"], m["venue"],
                                        match_type, m["toss_winner"])
            label = 1 if m["winner"] == m["team1"] else 0
            X.append(features)
            y.append(label)
        except Exception:
            continue

    X = np.array(X)
    y = np.array(y)

    # TimeSeriesSplit cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    val_accuracies = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        fold_model = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=1000, C=1.0))
        ])
        fold_model.fit(X_train, y_train)
        val_acc = (fold_model.predict(X_val) == y_val).mean()
        val_accuracies.append(val_acc)

    # Final model on all data
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, C=1.0))
    ])
    model.fit(X, y)

    path = str(MODEL_PATH).format(match_type=match_type)
    joblib.dump(model, path)

    avg_acc = np.mean(val_accuracies)
    print(f"[Logistic/{match_type}] CV accuracy: {avg_acc:.2%} | Saved to {path}")

    try:
        from models.prediction_tracker import log_model_record
        log_model_record("logistic", match_type, avg_acc, len(X),
                         feature_count=len(FEATURE_COLS), model_path=path)
    except Exception:
        pass

    return model


def predict(team1: str, team2: str, venue: str, match_type: str,
            toss_winner: str = None) -> float:
    """
    Returns P(team1 wins) using logistic regression.
    Falls back to Elo if model not trained.
    """
    path = str(MODEL_PATH).format(match_type=match_type)
    if not Path(path).exists():
        from models.elo import win_probability
        return win_probability(team1, team2, match_type)

    model = joblib.load(path)
    features = _build_features(team1, team2, venue, match_type, toss_winner)
    prob = model.predict_proba([features])[0][1]
    return round(float(prob), 4)


if __name__ == "__main__":
    for fmt in ["T20", "ODI"]:
        train(fmt)
