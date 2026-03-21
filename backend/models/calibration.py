"""
models/calibration.py
Prediction calibration using Platt scaling (logistic) or isotonic regression.
Ensures predicted probabilities are well-calibrated: "70% predictions" should
actually win ~70% of the time.
"""
import sys
import os
import joblib
import numpy as np
from pathlib import Path

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

CALIBRATOR_PATH = Path("models/calibrator_{match_type}.pkl")


def train_calibrator(raw_probs: np.ndarray, labels: np.ndarray,
                     match_type: str, method: str = "isotonic") -> object:
    """
    Train a calibrator on raw model probabilities vs actual outcomes.

    Args:
        raw_probs: array of predicted P(team1 wins) from ensemble
        labels: array of 1 (team1 won) or 0 (team1 lost)
        match_type: T20, ODI, etc.
        method: "isotonic" or "platt"
    """
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.linear_model import LogisticRegression
    from sklearn.isotonic import IsotonicRegression

    if method == "platt":
        # Platt scaling: fit logistic regression on raw probs
        calibrator = LogisticRegression(max_iter=1000)
        calibrator.fit(raw_probs.reshape(-1, 1), labels)
    else:
        # Isotonic regression: non-parametric monotonic calibration
        calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
        calibrator.fit(raw_probs, labels)

    path = str(CALIBRATOR_PATH).format(match_type=match_type)
    joblib.dump({"calibrator": calibrator, "method": method}, path)
    print(f"[Calibration/{match_type}] Saved {method} calibrator to {path}")
    return calibrator


def calibrate(raw_prob: float, match_type: str) -> float:
    """
    Calibrate a single raw probability.
    Returns the calibrated probability, or the raw prob if no calibrator exists.
    """
    path = str(CALIBRATOR_PATH).format(match_type=match_type)
    if not Path(path).exists():
        return raw_prob

    data = joblib.load(path)
    calibrator = data["calibrator"]
    method = data["method"]

    if method == "platt":
        return float(calibrator.predict_proba(np.array([[raw_prob]]))[0][1])
    else:
        return float(calibrator.predict(np.array([raw_prob]))[0])


def compute_calibration_stats(probs: np.ndarray, labels: np.ndarray,
                              n_bins: int = 10) -> dict:
    """
    Compute calibration metrics: Brier score, ECE (Expected Calibration Error),
    and bin-level accuracy vs confidence.
    """
    brier = float(np.mean((probs - labels) ** 2))

    # Bin-level stats
    bins = np.linspace(0, 1, n_bins + 1)
    bin_stats = []
    ece = 0.0

    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i + 1])
        count = mask.sum()
        if count > 0:
            avg_pred = float(probs[mask].mean())
            avg_actual = float(labels[mask].mean())
            ece += abs(avg_pred - avg_actual) * (count / len(probs))
            bin_stats.append({
                "bin_start": round(bins[i], 2),
                "bin_end": round(bins[i + 1], 2),
                "avg_predicted": round(avg_pred, 3),
                "avg_actual": round(avg_actual, 3),
                "count": int(count),
            })

    return {
        "brier_score": round(brier, 4),
        "ece": round(ece, 4),
        "bins": bin_stats,
    }
