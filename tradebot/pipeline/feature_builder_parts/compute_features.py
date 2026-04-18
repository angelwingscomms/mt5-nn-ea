from __future__ import annotations

from .shared import *  # noqa: F401,F403

def compute_features(
    df: pd.DataFrame,
    feature_columns: tuple[str, ...],
    config: FeatureEngineeringConfig,
) -> np.ndarray:
    feat = compute_feature_frame(df, feature_columns=feature_columns, config=config)
    missing_features = [name for name in feature_columns if name not in feat.columns]
    if missing_features:
        raise KeyError(f"Missing computed features: {missing_features}")
    return feat.loc[:, feature_columns].to_numpy(dtype=np.float32, copy=False)
