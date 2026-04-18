from __future__ import annotations

from .shared import *  # noqa: F401,F403

def confusion_matrix_df(labels: np.ndarray, preds: np.ndarray, label_names: tuple[str, ...] | None = None) -> pd.DataFrame:
    if label_names is None:
        label_names = LABEL_NAMES
    matrix = np.zeros((len(label_names), len(label_names)), dtype=np.int64)
    for true_label, pred_label in zip(labels.astype(np.int64), preds.astype(np.int64)):
        matrix[true_label, pred_label] += 1
    return pd.DataFrame(
        matrix,
        index=[f"true_{name.lower()}" for name in label_names],
        columns=[f"pred_{name.lower()}" for name in label_names],
    )
