"""
models/prediction_tracker.py
Logs every prediction to predictions_log table.
Supports backfilling outcomes and generating accuracy reports.
"""
import sys
import os
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _p in [_root, os.path.join(_root, "backend")]:
    if _p not in sys.path: sys.path.insert(0, _p)

from database.db import get_connection


def log_prediction(team1: str, team2: str, match_type: str,
                   model_name: str, team1_win_prob: float,
                   ensemble_prob: float = None, confidence: str = None,
                   venue: str = None, match_id: int = None):
    """Log a single prediction to the database."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO predictions_log
            (match_id, match_type, team1, team2, venue, predicted_at,
             model_name, team1_win_prob, ensemble_prob, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (match_id, match_type, team1, team2, venue,
          datetime.now().isoformat(), model_name,
          round(team1_win_prob, 4), round(ensemble_prob, 4) if ensemble_prob else None,
          confidence))
    conn.commit()
    conn.close()


def backfill_outcomes():
    """
    For predictions that have a match_id, look up the actual winner
    and mark was_correct.
    """
    conn = get_connection()
    pending = conn.execute("""
        SELECT pl.id, pl.match_id, pl.team1, pl.team1_win_prob
        FROM predictions_log pl
        JOIN matches m ON pl.match_id = m.id
        WHERE pl.actual_winner IS NULL AND m.winner IS NOT NULL
    """).fetchall()

    updated = 0
    for row in pending:
        winner = conn.execute("SELECT winner FROM matches WHERE id = ?",
                              (row["match_id"],)).fetchone()
        if winner and winner["winner"]:
            actual = winner["winner"]
            predicted_team1 = row["team1_win_prob"] >= 0.5
            team1_won = actual == row["team1"]
            was_correct = 1 if predicted_team1 == team1_won else 0

            conn.execute("""
                UPDATE predictions_log
                SET actual_winner = ?, was_correct = ?
                WHERE id = ?
            """, (actual, was_correct, row["id"]))
            updated += 1

    conn.commit()
    conn.close()
    print(f"[PredictionTracker] Backfilled {updated} outcomes")
    return updated


def get_accuracy_report(match_type: str = None) -> dict:
    """
    Generate prediction accuracy report with overall accuracy,
    per-model accuracy, and calibration stats.
    """
    conn = get_connection()

    where = "WHERE was_correct IS NOT NULL"
    params = []
    if match_type:
        where += " AND match_type = ?"
        params.append(match_type)

    # Overall accuracy
    rows = conn.execute(f"""
        SELECT COUNT(*) as total,
               SUM(was_correct) as correct,
               AVG(was_correct) as accuracy
        FROM predictions_log {where}
    """, params).fetchone()

    # Per-model accuracy
    model_rows = conn.execute(f"""
        SELECT model_name,
               COUNT(*) as total,
               SUM(was_correct) as correct,
               AVG(was_correct) as accuracy,
               AVG((team1_win_prob - was_correct) * (team1_win_prob - was_correct)) as brier
        FROM predictions_log {where}
        GROUP BY model_name
    """, params).fetchall()

    # Calibration bins
    import numpy as np
    all_preds = conn.execute(f"""
        SELECT team1_win_prob, was_correct FROM predictions_log {where}
    """, params).fetchall()
    conn.close()

    calibration_bins = []
    if all_preds:
        probs = np.array([r["team1_win_prob"] for r in all_preds])
        labels = np.array([r["was_correct"] for r in all_preds])
        bins = np.linspace(0, 1, 11)
        for i in range(10):
            mask = (probs >= bins[i]) & (probs < bins[i + 1])
            count = mask.sum()
            if count > 0:
                calibration_bins.append({
                    "range": f"{bins[i]:.1f}-{bins[i+1]:.1f}",
                    "predicted": round(float(probs[mask].mean()), 3),
                    "actual": round(float(labels[mask].mean()), 3),
                    "count": int(count),
                })

    return {
        "total_predictions": rows["total"] if rows else 0,
        "correct": rows["correct"] if rows else 0,
        "accuracy": round(rows["accuracy"] * 100, 1) if rows and rows["accuracy"] else 0,
        "per_model": [
            {
                "model": r["model_name"],
                "total": r["total"],
                "accuracy": round(r["accuracy"] * 100, 1) if r["accuracy"] else 0,
                "brier": round(r["brier"], 4) if r["brier"] else None,
            }
            for r in model_rows
        ],
        "calibration": calibration_bins,
    }


def log_model_record(model_name: str, match_type: str, val_accuracy: float,
                     train_samples: int, feature_count: int = None,
                     brier_score: float = None, hyperparams: str = None,
                     model_path: str = None):
    """Log a model training record."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO model_records
            (model_name, match_type, trained_at, train_samples,
             val_accuracy, brier_score, feature_count, hyperparams, model_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (model_name, match_type, datetime.now().isoformat(),
          train_samples, round(val_accuracy, 4),
          round(brier_score, 4) if brier_score else None,
          feature_count, hyperparams, model_path))
    conn.commit()
    conn.close()
