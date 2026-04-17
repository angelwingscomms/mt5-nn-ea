from __future__ import annotations

from .shared import *  # noqa: F401,F403

def compute_features(df: pd.DataFrame, feature_columns: tuple[str, ...]) -> np.ndarray:
    close = df["close"].astype(float)
    open_price = df["open"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    tick_count = df["tick_count"].astype(float)
    tick_imbalance = df["tick_imbalance"].astype(float)
    prev_close = close.shift(1)
    ret1 = np.log(close / (prev_close + EPS))
    atr_feature = wilder_atr(df["high"], df["low"], close, period=FEATURE_ATR_PERIOD)
    spread_rel = df["spread"] / (close + EPS)

    sma_fast = close.rolling(FEATURE_SMA_FAST_PERIOD, min_periods=FEATURE_SMA_FAST_PERIOD).mean()
    sma_trend_fast = close.rolling(FEATURE_SMA_TREND_FAST_PERIOD, min_periods=FEATURE_SMA_TREND_FAST_PERIOD).mean()
    sma_mid = close.rolling(FEATURE_SMA_MID_PERIOD, min_periods=FEATURE_SMA_MID_PERIOD).mean()
    sma_slow = close.rolling(FEATURE_SMA_SLOW_PERIOD, min_periods=FEATURE_SMA_SLOW_PERIOD).mean()
    rv_3 = rolling_population_std(ret1, FEATURE_RET_3_PERIOD)
    rv_6 = rolling_population_std(ret1, FEATURE_RET_6_PERIOD)
    rv_18 = rolling_population_std(ret1, FEATURE_RV_LONG_PERIOD)
    high_fast = high.rolling(FEATURE_DONCHIAN_FAST_PERIOD, min_periods=FEATURE_DONCHIAN_FAST_PERIOD).max()
    low_fast = low.rolling(FEATURE_DONCHIAN_FAST_PERIOD, min_periods=FEATURE_DONCHIAN_FAST_PERIOD).min()
    high_slow = high.rolling(FEATURE_DONCHIAN_SLOW_PERIOD, min_periods=FEATURE_DONCHIAN_SLOW_PERIOD).max()
    low_slow = low.rolling(FEATURE_DONCHIAN_SLOW_PERIOD, min_periods=FEATURE_DONCHIAN_SLOW_PERIOD).min()
    high_stoch = high.rolling(FEATURE_STOCH_PERIOD, min_periods=FEATURE_STOCH_PERIOD).max()
    low_stoch = low.rolling(FEATURE_STOCH_PERIOD, min_periods=FEATURE_STOCH_PERIOD).min()
    stoch_k_9 = (close - low_stoch) / (high_stoch - low_stoch + EPS)
    stoch_d_3 = stoch_k_9.rolling(FEATURE_STOCH_SMOOTH_PERIOD, min_periods=FEATURE_STOCH_SMOOTH_PERIOD).mean()
    bollinger_std_20 = rolling_population_std(close, FEATURE_BOLLINGER_PERIOD)

    feat = pd.DataFrame(index=df.index)
    feat["ret1"] = ret1
    feat["high_rel_prev"] = np.log(high / (prev_close + EPS))
    feat["low_rel_prev"] = np.log(low / (prev_close + EPS))
    feat["spread_rel"] = spread_rel
    feat["close_in_range"] = (close - low) / (high - low + 1e-8)
    feat["atr_rel"] = atr_feature / (close + EPS)
    feat["rv"] = rolling_population_std(ret1, RV_PERIOD)
    feat["ret_n"] = np.log(close / (close.shift(RETURN_PERIOD) + EPS))
    feat["tick_imbalance"] = tick_imbalance

    requires_gold_context = any(name in feature_columns for name in GOLD_CONTEXT_FEATURE_COLUMNS)
    usdx_bid = df.get("usdx_bid")
    usdjpy_bid = df.get("usdjpy_bid")
    if requires_gold_context:
        if usdx_bid is None or usdjpy_bid is None:
            raise ValueError("Gold-context features requested but auxiliary columns are missing from the bar data.")
        if usdx_bid.notna().sum() == 0 or usdjpy_bid.notna().sum() == 0:
            raise ValueError("Gold-context features requested but auxiliary columns are empty after bar construction.")
        usdx_bid = usdx_bid.ffill().bfill()
        usdjpy_bid = usdjpy_bid.ffill().bfill()
    else:
        if usdx_bid is None:
            usdx_bid = close
        else:
            usdx_bid = usdx_bid.fillna(close)
        if usdjpy_bid is None:
            usdjpy_bid = close
        else:
            usdjpy_bid = usdjpy_bid.fillna(close)
    feat["usdx_ret1"] = np.log(usdx_bid / (usdx_bid.shift(1) + EPS))
    feat["usdjpy_ret1"] = np.log(usdjpy_bid / (usdjpy_bid.shift(1) + EPS))

    feat["ret_2"] = np.log(close / (close.shift(FEATURE_RET_2_PERIOD) + EPS))
    feat["ret_3"] = np.log(close / (close.shift(FEATURE_RET_3_PERIOD) + EPS))
    feat["ret_6"] = np.log(close / (close.shift(FEATURE_RET_6_PERIOD) + EPS))
    feat["ret_12"] = np.log(close / (close.shift(FEATURE_RET_12_PERIOD) + EPS))
    feat["ret_20"] = np.log(close / (close.shift(FEATURE_RET_20_PERIOD) + EPS))
    feat["open_rel_prev"] = np.log(open_price / (prev_close + EPS))
    feat["range_rel"] = (high - low) / (close + EPS)
    feat["body_rel"] = (close - open_price) / (close + EPS)
    feat["upper_wick_rel"] = (high - np.maximum(open_price, close)) / (close + EPS)
    feat["lower_wick_rel"] = (np.minimum(open_price, close) - low) / (close + EPS)
    feat["close_rel_sma_3"] = np.log(close / (sma_fast + EPS))
    feat["close_rel_sma_9"] = np.log(close / (sma_mid + EPS))
    feat["close_rel_sma_20"] = np.log(close / (sma_slow + EPS))
    feat["sma_3_9_gap"] = np.log(sma_fast / (sma_mid + EPS))
    feat["sma_5_20_gap"] = np.log(sma_trend_fast / (sma_slow + EPS))
    feat["sma_9_20_gap"] = np.log(sma_mid / (sma_slow + EPS))
    feat["sma_slope_9"] = np.log(sma_mid / (sma_mid.shift(FEATURE_SMA_SLOPE_SHIFT) + EPS))
    feat["sma_slope_20"] = np.log(sma_slow / (sma_slow.shift(FEATURE_SMA_SLOPE_SHIFT) + EPS))
    feat["rv_3"] = rv_3
    feat["rv_6"] = rv_6
    feat["rv_18"] = rv_18
    feat["donchian_pos_9"] = (close - low_fast) / (high_fast - low_fast + EPS)
    feat["donchian_width_9"] = (high_fast - low_fast) / (close + EPS)
    feat["donchian_pos_20"] = (close - low_slow) / (high_slow - low_slow + EPS)
    feat["donchian_width_20"] = (high_slow - low_slow) / (close + EPS)
    tick_count_sma_9 = tick_count.rolling(FEATURE_TICK_COUNT_PERIOD, min_periods=FEATURE_TICK_COUNT_PERIOD).mean()
    feat["tick_count_rel_9"] = tick_count / (tick_count_sma_9 + EPS) - 1.0
    feat["tick_count_z_9"] = rolling_zscore(tick_count, FEATURE_TICK_COUNT_PERIOD)
    feat["tick_count_chg"] = np.log((tick_count + 1.0) / (tick_count.shift(1) + 1.0))
    feat["tick_imbalance_sma_5"] = tick_imbalance.rolling(
        FEATURE_TICK_IMBALANCE_FAST_PERIOD,
        min_periods=FEATURE_TICK_IMBALANCE_FAST_PERIOD,
    ).mean()
    feat["tick_imbalance_sma_9"] = tick_imbalance.rolling(
        FEATURE_TICK_IMBALANCE_SLOW_PERIOD,
        min_periods=FEATURE_TICK_IMBALANCE_SLOW_PERIOD,
    ).mean()
    feat["spread_z_9"] = rolling_zscore(spread_rel, FEATURE_SPREAD_Z_PERIOD)
    feat["rsi_6"] = simple_rsi(close, FEATURE_RSI_FAST_PERIOD)
    feat["rsi_14"] = simple_rsi(close, FEATURE_RSI_SLOW_PERIOD)
    feat["stoch_k_9"] = stoch_k_9
    feat["stoch_d_3"] = stoch_d_3
    feat["stoch_gap"] = stoch_k_9 - stoch_d_3
    feat["bollinger_pos_20"] = (close - sma_slow) / (2.0 * bollinger_std_20 + EPS)
    feat["bollinger_width_20"] = (4.0 * bollinger_std_20) / (sma_slow + EPS)
    feat["atr_ratio_20"] = np.log(
        atr_feature
        / (
            atr_feature.rolling(FEATURE_ATR_RATIO_PERIOD, min_periods=FEATURE_ATR_RATIO_PERIOD).mean() + EPS
        )
    )

    missing_features = [name for name in feature_columns if name not in feat.columns]
    if missing_features:
        raise KeyError(f"Missing computed features: {missing_features}")
    return feat.loc[:, feature_columns].to_numpy(dtype=np.float32, copy=False)
