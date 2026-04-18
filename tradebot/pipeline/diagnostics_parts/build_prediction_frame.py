from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_prediction_frame(labels: np.ndarray, probs: np.ndarray, threshold: float, label_names: tuple[str, ...]) -> pd.DataFrame:
    preds = probs.argmax(axis=1)
    confidences = probs.max(axis=1)
    selected = confidences >= threshold if probs.shape[1] == 2 else (preds > 0) & (confidences >= threshold)
    frame = pd.DataFrame(
        {
            "true_label": labels.astype(np.int64),
            "pred_label": preds.astype(np.int64),
            "true_name": [label_names[int(v)] for v in labels],
            "pred_name": [label_names[int(v)] for v in preds],
            "confidence": confidences,
            "selected_trade": selected.astype(np.int64),
            "correct": (preds == labels).astype(np.int64),
        }
    )
    if probs.shape[1] == 3:
        frame["prob_hold"] = probs[:, 0]
        frame["prob_buy"] = probs[:, 1]
        frame["prob_sell"] = probs[:, 2]
    else:
        frame["prob_buy"] = probs[:, 0]
        frame["prob_sell"] = probs[:, 1]
    return frame
