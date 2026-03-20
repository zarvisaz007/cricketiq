"""
models/logistic.py
Logistic Regression match prediction model.
Trained on historical matches using team/elo/venue features.
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
from features.team_features import get_team_strength, get_venue_win_rate

MODEL_PATH = Path("models/logistic_{match_type}.pkl")


def _build_features(team1: str, team2: str, venue: str, match_type: str,
                    toss_winner: str = None) -> list:
    """Build feature vector for a single match."""
    strength1 = get_team_strength(team1, match_type, venue)
    strength2 = get_team_strength(team2, match_type, venue)
    elo1 = get_elo(team1, match_type)
    elo2 = get_elo(team2, match_type)
    venue_adv1 = get_venue_win_rate(team1, venue, match_type) if venue else 50.0
    toss_advantage = 1.0 if toss_winner == team1 else (0.0 if toss_winner == team2 else 0.5)

    return [
        strength1 - strength2,          # team strength diff
        _elo_prob(elo1, elo2),           # elo win probability
        venue_adv1 / 100.0,             # venue advantage (0-1)
        toss_advantage,                  # toss (0, 0.5, 1)
        (strength1 - 50) / 50,          # normalized team1 strength
        (strength2 - 50) / 50,          # normalized team2 strength
    ]


def train(match_type: str):
    """Train logistic regression on historical match data."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline

    conn = get_connection()
    matches = conn.execute("""
        SELECT team1, team2, venue, toss_winner, winner FROM matches
        WHERE match_type = ? AND winner IS NOT NULL
        ORDER BY date ASC
    """, (match_type,)).fetchall()
    conn.close()

    if len(matches) < 50:
        print(f"[Logistic/{match_type}] Not enough data ({len(matches)} matches). Need 50+.")
        return None

    print(f"[Logistic/{match_type}] Building features for {len(matches)} matches...")

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

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, C=1.0))
    ])
    model.fit(X, y)

    path = str(MODEL_PATH).format(match_type=match_type)
    joblib.dump(model, path)

    # Quick accuracy check
    preds = model.predict(X)
    accuracy = (preds == y).mean()
    print(f"[Logistic/{match_type}] Trained. Train accuracy: {accuracy:.2%} | Saved to {path}")
    return model


def predict(team1: str, team2: str, venue: str, match_type: str,
            toss_winner: str = None) -> float:
    """
    Returns P(team1 wins) using logistic regression.
    Falls back to Elo if model not trained.
    """
    path = str(MODEL_PATH).format(match_type=match_type)
    if not Path(path).exists():
        # Fallback to Elo
        from models.elo import win_probability
        return win_probability(team1, team2, match_type)

    model = joblib.load(path)
    features = _build_features(team1, team2, venue, match_type, toss_winner)
    prob = model.predict_proba([features])[0][1]
    return round(float(prob), 4)


if __name__ == "__main__":
    for fmt in ["T20", "ODI"]:
        train(fmt)
