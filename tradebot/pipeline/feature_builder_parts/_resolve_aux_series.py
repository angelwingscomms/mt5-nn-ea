from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _resolve_aux_series(df: pd.DataFrame, feature_columns: tuple[str, ...]) -> tuple[pd.Series, pd.Series]:
    requires_aux_context = _aux_context_required(feature_columns)
    usdx_bid = df.get("usdx_bid")
    usdjpy_bid = df.get("usdjpy_bid")
    if requires_aux_context:
        if usdx_bid is None or usdjpy_bid is None:
            raise ValueError("Auxiliary USDX/USDJPY features were requested but the bar data is missing those columns.")
        if usdx_bid.notna().sum() == 0 or usdjpy_bid.notna().sum() == 0:
            raise ValueError("Auxiliary USDX/USDJPY features were requested but the bar data is empty for them.")
        return usdx_bid.ffill().bfill(), usdjpy_bid.ffill().bfill()

    fallback = df["close"].astype(float)
    return (
        fallback if usdx_bid is None else usdx_bid.fillna(fallback),
        fallback if usdjpy_bid is None else usdjpy_bid.fillna(fallback),
    )
