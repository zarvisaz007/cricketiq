"""
models/xgboost_model.py
XGBoost match prediction model v2.
Uses feature registry (28 features), TimeSeriesSplit, logs model records.
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
                                        FEATURE_COLS, FEATURE_DEFAULTS)

MODEL_PATH = Path("models/xgb_{match_type}.pkl")


def _build_features(team1: str, team2: str, venue: str, match_type: str,
                    toss_winner: str = None) -> list:
    """Build feature vector using the feature registry."""
    fv = build_feature_vector(team1, team2, venue, match_type, toss_winner,
                              include_phases=(match_type == "T20"))
    return feature_vector_to_list(fv)


def train(match_type: str):
    """Train XGBoost on historical data with TimeSeriesSplit."""
    try:
        import xgboost as xgb
    except ImportError:
        print("[XGB] xgboost not installed. Run: pip install xgboost")
        return None

    from sklearn.model_selection import TimeSeriesSplit

    conn = get_connection()
    matches = conn.execute("""
        SELECT team1, team2, venue, toss_winner, winner FROM matches
        WHERE match_type = ? AND gender = 'male' AND winner IS NOT NULL
        ORDER BY date ASC
    """, (match_type,)).fetchall()
    conn.close()

    if len(matches) < 100:
        print(f"[XGB/{match_type}] Not enough data ({len(matches)} matches). Need 100+.")
        return None

    print(f"[XGB/{match_type}] Building {len(FEATURE_COLS)} features for {len(matches)} matches...")

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

    # TimeSeriesSplit — prevents lookahead bias
    tscv = TimeSeriesSplit(n_splits=5)
    val_accuracies = []
    brier_scores = []

    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X_train, y_train,
                  eval_set=[(X_val, y_val)],
                  verbose=False)

        val_pred = model.predict(X_val)
        val_prob = model.predict_proba(X_val)[:, 1]
        val_acc = (val_pred == y_val).mean()
        brier = float(np.mean((val_prob - y_val) ** 2))
        val_accuracies.append(val_acc)
        brier_scores.append(brier)

    # Train final model on all data
    final_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    final_model.fit(X, y, verbose=False)

    path = str(MODEL_PATH).format(match_type=match_type)
    joblib.dump(final_model, path)

    avg_acc = np.mean(val_accuracies)
    avg_brier = np.mean(brier_scores)
    print(f"[XGB/{match_type}] CV accuracy: {avg_acc:.2%} (Brier: {avg_brier:.4f}) | Saved to {path}")

    # Log model record
    try:
        from models.prediction_tracker import log_model_record
        log_model_record("xgboost", match_type, avg_acc, len(X),
                         feature_count=len(FEATURE_COLS), brier_score=avg_brier,
                         model_path=path)
    except Exception:
        pass

    return final_model


def predict(team1: str, team2: str, venue: str, match_type: str,
            toss_winner: str = None) -> float:
    """
    Returns P(team1 wins) using XGBoost.
    Falls back to logistic if model not trained.
    """
    path = str(MODEL_PATH).format(match_type=match_type)
    if not Path(path).exists():
        from models.logistic import predict as logistic_predict
        return logistic_predict(team1, team2, venue, match_type, toss_winner)

    model = joblib.load(path)
    features = _build_features(team1, team2, venue, match_type, toss_winner)
    prob = model.predict_proba([features])[0][1]
    return round(float(prob), 4)


if __name__ == "__main__":
    for fmt in ["T20", "ODI"]:
        train(fmt)
