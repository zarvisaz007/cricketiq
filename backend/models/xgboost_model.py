"""
models/xgboost_model.py
XGBoost match prediction model (most accurate).
Uses same feature set as logistic model + additional features.
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
from models.elo import get_elo, _elo_prob
from features.team_features import (get_team_strength, get_venue_win_rate,
                                     get_team_recent_form, get_head_to_head)

MODEL_PATH = Path("models/xgb_{match_type}.pkl")


def _build_features(team1: str, team2: str, venue: str, match_type: str,
                    toss_winner: str = None) -> list:
    """Extended feature vector for XGBoost."""
    strength1 = get_team_strength(team1, match_type, venue)
    strength2 = get_team_strength(team2, match_type, venue)
    elo1 = get_elo(team1, match_type)
    elo2 = get_elo(team2, match_type)
    form1 = get_team_recent_form(team1, match_type)
    form2 = get_team_recent_form(team2, match_type)
    venue_adv1 = get_venue_win_rate(team1, venue, match_type) if venue else 50.0
    venue_adv2 = get_venue_win_rate(team2, venue, match_type) if venue else 50.0
    h2h = get_head_to_head(team1, team2, match_type)
    toss_adv = 1.0 if toss_winner == team1 else (0.0 if toss_winner == team2 else 0.5)

    return [
        strength1 - strength2,
        _elo_prob(elo1, elo2),
        elo1 - elo2,
        form1 - form2,
        venue_adv1 - venue_adv2,
        toss_adv,
        h2h["team1_win_pct"] / 100.0,
        strength1 / 100.0,
        strength2 / 100.0,
        form1 / 100.0,
        form2 / 100.0,
    ]


def train(match_type: str):
    """Train XGBoost on historical data."""
    try:
        import xgboost as xgb
    except ImportError:
        print("[XGB] xgboost not installed. Run: pip install xgboost")
        return None

    from sklearn.model_selection import train_test_split

    conn = get_connection()
    matches = conn.execute("""
        SELECT team1, team2, venue, toss_winner, winner FROM matches
        WHERE match_type = ? AND winner IS NOT NULL
        ORDER BY date ASC
    """, (match_type,)).fetchall()
    conn.close()

    if len(matches) < 100:
        print(f"[XGB/{match_type}] Not enough data ({len(matches)} matches). Need 100+.")
        return None

    print(f"[XGB/{match_type}] Building features for {len(matches)} matches...")

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

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2,
                                                        random_state=42, shuffle=False)

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train,
              eval_set=[(X_val, y_val)],
              verbose=False)

    path = str(MODEL_PATH).format(match_type=match_type)
    joblib.dump(model, path)

    val_acc = (model.predict(X_val) == y_val).mean()
    print(f"[XGB/{match_type}] Trained. Val accuracy: {val_acc:.2%} | Saved to {path}")
    return model


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
