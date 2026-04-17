from __future__ import annotations

from .shared import *  # noqa: F401,F403

def gate_metrics(labels: np.ndarray, probs: np.ndarray, threshold: float) -> dict[str, float | int]:
    preds = probs.argmax(axis=1)
    confidences = probs.max(axis=1)
    selected = confidences >= threshold if probs.shape[1] == 2 else (preds > 0) & (confidences >= threshold)
    selected_trades = int(selected.sum())
    precision = float((preds[selected] == labels[selected]).mean()) if selected_trades else float("nan")
    selected_mean_confidence = float(confidences[selected].mean()) if selected_trades else float("nan")
    return {
        "selected_trades": selected_trades,
        "trade_coverage": float(selected.mean()),
        "precision": precision,
        "mean_confidence": float(confidences.mean()),
        "selected_mean_confidence": selected_mean_confidence,
    }
