from __future__ import annotations

from .shared import *  # noqa: F401,F403

LABEL_NAMES = ("HOLD", "BUY", "SELL")
LABEL_NAMES_BINARY = ("BUY", "SELL")

def build_prediction_frame(labels: np.ndarray, probs: np.ndarray, threshold: float, label_names: tuple[str, ...], flip: bool = False) -> pd.DataFrame:
    preds = probs.argmax(axis=1)
    num_classes = probs.shape[1]
    if flip:
        if num_classes == 2:
            preds = 1 - preds
        else:
            preds_flipped = preds.copy()
            preds_flipped[preds == 1] = 2
            preds_flipped[preds == 2] = 1
            preds = preds_flipped
    confidences = probs.max(axis=1)
    selected = confidences >= threshold if num_classes == 2 else (preds > 0) & (confidences >= threshold)
    if num_classes != len(label_names):
        label_names = LABEL_NAMES if num_classes == 3 else LABEL_NAMES_BINARY
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
    if num_classes == 3:
        frame["prob_hold"] = probs[:, 0]
        frame["prob_buy"] = probs[:, 1]
        frame["prob_sell"] = probs[:, 2]
    else:
        frame["prob_buy"] = probs[:, 0]
        frame["prob_sell"] = probs[:, 1]
    return frame
