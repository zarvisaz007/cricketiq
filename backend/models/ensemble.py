"""
models/ensemble.py
Confidence-weighted ensemble for match predictions.
Weights models by their recent Brier scores (lower = better = higher weight).
Flags reduced confidence when models disagree >20%.
"""
import sys
import os
import numpy as np

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

# Default weights (equal) — updated as models are evaluated
DEFAULT_WEIGHTS = {
    "elo": 0.15,
    "logistic": 0.20,
    "xgboost": 0.40,
    "monte_carlo": 0.25,
}


def weighted_ensemble(predictions: dict, weights: dict = None) -> dict:
    """
    Compute weighted ensemble prediction.

    Args:
        predictions: {"elo": 0.65, "logistic": 0.62, "xgboost": 0.71, "monte_carlo": 0.64}
        weights: {"elo": 0.15, "logistic": 0.20, ...} (default: DEFAULT_WEIGHTS)

    Returns:
        {
            "ensemble_prob": 0.66,
            "confidence": "HIGH",
            "model_agreement": True,
            "individual": {model: prob},
            "weights_used": {model: weight},
        }
    """
    if weights is None:
        weights = dict(DEFAULT_WEIGHTS)

    # Filter to models that actually produced predictions
    active = {m: p for m, p in predictions.items() if p is not None}
    if not active:
        return {"ensemble_prob": 0.5, "confidence": "LOW", "model_agreement": True,
                "individual": {}, "weights_used": {}}

    # Normalize weights for active models
    active_weights = {m: weights.get(m, 0.25) for m in active}
    total_w = sum(active_weights.values())
    if total_w > 0:
        active_weights = {m: w / total_w for m, w in active_weights.items()}

    # Weighted average
    ensemble_prob = sum(active[m] * active_weights[m] for m in active)

    # Check model agreement
    probs = list(active.values())
    spread = max(probs) - min(probs)
    model_agreement = spread <= 0.20  # models agree within 20%

    # Confidence
    margin = abs(ensemble_prob - 0.5)
    if not model_agreement:
        confidence = "LOW"
    elif margin >= 0.15:
        confidence = "HIGH"
    elif margin >= 0.07:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "ensemble_prob": round(ensemble_prob, 4),
        "confidence": confidence,
        "model_agreement": model_agreement,
        "spread": round(spread, 4),
        "individual": {m: round(p, 4) for m, p in active.items()},
        "weights_used": {m: round(w, 4) for m, w in active_weights.items()},
    }


def update_weights_from_brier(model_brier_scores: dict) -> dict:
    """
    Compute new weights from recent Brier scores.
    Lower Brier = better calibrated = higher weight.
    Uses inverse Brier score as weight.
    """
    if not model_brier_scores:
        return dict(DEFAULT_WEIGHTS)

    # Inverse Brier (capped to avoid div-by-zero)
    inv_brier = {}
    for model, brier in model_brier_scores.items():
        inv_brier[model] = 1.0 / max(brier, 0.01)

    total = sum(inv_brier.values())
    weights = {m: round(v / total, 4) for m, v in inv_brier.items()}
    return weights
