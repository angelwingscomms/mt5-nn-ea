from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_market_bars(
    csv_path: Path,
    *,
    bar_type: str,
    tick_density: int,
    max_bars: int,
    bar_duration_ms: int,
    imbalance_min_ticks: int,
    imbalance_ema_span: int,
    use_imbalance_ema_threshold: bool,
    use_imbalance_min_ticks_div3_threshold: bool,
    require_gold_context: bool = False,
) -> tuple[pd.DataFrame, float]:
    use_fixed_time_bars = bar_type == "time"
    use_fixed_tick_bars = bar_type == "tick"
    t0 = time.time()
    chunks: list[pd.DataFrame] = []
    extended_usecols = ["time_msc", "bid", "ask", *GOLD_CONTEXT_TICK_COLUMNS]
    legacy_usecols = ["time_msc", "bid", "ask", "usdx", "usdjpy"]
    base_usecols = ["time_msc", "bid", "ask"]
    read_csv_kwargs = {
        "filepath_or_buffer": csv_path,
        "usecols": extended_usecols,
        "dtype": {
            "time_msc": np.int64,
            "bid": np.float64,
            "ask": np.float64,
            "usdx_bid": np.float64,
            "usdjpy_bid": np.float64,
        },
        "chunksize": 50_000,
    }

    try:
        for chunk in pd.read_csv(**read_csv_kwargs):
            chunks.append(chunk)
    except ValueError:
        chunks.clear()
        try:
            read_csv_kwargs["usecols"] = legacy_usecols
            read_csv_kwargs["dtype"] = {
                "time_msc": np.int64,
                "bid": np.float64,
                "ask": np.float64,
                "usdx": np.float64,
                "usdjpy": np.float64,
            }
            for chunk in pd.read_csv(**read_csv_kwargs):
                chunks.append(chunk)
        except ValueError:
            chunks.clear()
            read_csv_kwargs["usecols"] = base_usecols
            read_csv_kwargs["dtype"] = {"time_msc": np.int64, "bid": np.float64, "ask": np.float64}
            for chunk in pd.read_csv(**read_csv_kwargs):
                chunks.append(chunk)
    except pd.errors.ParserError as exc:
        if "out of memory" not in str(exc).lower():
            raise
        log.warning("Default CSV parser ran out of memory for %s; retrying with engine=python.", csv_path)
        chunks.clear()
        try:
            for chunk in pd.read_csv(**read_csv_kwargs, engine="python"):
                chunks.append(chunk)
        except ValueError:
            chunks.clear()
            try:
                read_csv_kwargs["usecols"] = legacy_usecols
                read_csv_kwargs["dtype"] = {
                    "time_msc": np.int64,
                    "bid": np.float64,
                    "ask": np.float64,
                    "usdx": np.float64,
                    "usdjpy": np.float64,
                }
                for chunk in pd.read_csv(**read_csv_kwargs, engine="python"):
                    chunks.append(chunk)
            except ValueError:
                chunks.clear()
                read_csv_kwargs["usecols"] = base_usecols
                read_csv_kwargs["dtype"] = {"time_msc": np.int64, "bid": np.float64, "ask": np.float64}
                for chunk in pd.read_csv(**read_csv_kwargs, engine="python"):
                    chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    if not df["time_msc"].is_monotonic_increasing:
        df = df.sort_values("time_msc").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No ticks found in {csv_path}")

    if "usdx_bid" not in df.columns:
        df["usdx_bid"] = df["usdx"] if "usdx" in df.columns else np.nan
    if "usdjpy_bid" not in df.columns:
        df["usdjpy_bid"] = df["usdjpy"] if "usdjpy" in df.columns else np.nan
    if require_gold_context:
        missing_columns = [name for name in GOLD_CONTEXT_TICK_COLUMNS if name not in df.columns]
        if missing_columns:
            raise ValueError(
                "Gold-context training requires auxiliary columns "
                f"{missing_columns} in {csv_path}. Re-export gold ticks first."
            )
        empty_columns = [name for name in GOLD_CONTEXT_TICK_COLUMNS if df[name].notna().sum() == 0]
        if empty_columns:
            raise ValueError(
                "Gold-context training found empty auxiliary columns "
                f"{empty_columns} in {csv_path}. Re-export gold ticks first."
            )

    point_size = infer_point_size_from_ticks(df)
    df["tick_sign"] = compute_tick_signs(df["bid"].to_numpy(dtype=np.float64, copy=False))
    df["spread"] = df["ask"] - df["bid"]

    if use_fixed_tick_bars:
        df["bar_id"] = build_tick_bar_ids(len(df), tick_density)
    elif use_fixed_time_bars:
        if bar_duration_ms <= 0:
            raise ValueError("PRIMARY_BAR_SECONDS must be positive.")
        df["bar_id"] = build_time_bar_ids(df["time_msc"].to_numpy(dtype=np.int64, copy=False), bar_duration_ms)
    else:
        df["bar_id"] = build_primary_bar_ids(
            df["tick_sign"].to_numpy(dtype=np.int8, copy=False),
            imbalance_min_ticks=imbalance_min_ticks,
            imbalance_ema_span=imbalance_ema_span,
            use_imbalance_ema_threshold=use_imbalance_ema_threshold,
            use_imbalance_min_ticks_div3_threshold=use_imbalance_min_ticks_div3_threshold,
        )

    grouped = (
        df.groupby("bar_id", sort=True)
        .agg(
            open=("bid", "first"),
            high=("bid", "max"),
            low=("bid", "min"),
            close=("bid", "last"),
            tick_count=("bid", "size"),
            tick_imbalance=("tick_sign", "mean"),
            ask_high=("ask", "max"),
            ask_low=("ask", "min"),
            spread=("spread", "last"),
            spread_mean=("spread", "mean"),
            time_open=("time_msc", "first"),
            time_close=("time_msc", "last"),
            usdx_bid=("usdx_bid", "last"),
            usdjpy_bid=("usdjpy_bid", "last"),
        )
        .reset_index(drop=True)
    )

    if max_bars > 0 and len(grouped) > max_bars:
        grouped = grouped.iloc[:max_bars].reset_index(drop=True)
        log.info("Capped bars to %d rows.", max_bars)

    if use_fixed_tick_bars:
        log.info(
            "Built %d bars in %.2fs using fixed %d-tick bars | point_size=%.8f",
            len(grouped),
            time.time() - t0,
            tick_density,
            point_size,
        )
    elif use_fixed_time_bars:
        log.info(
            "Built %d bars in %.2fs using fixed %dms bars | point_size=%.8f",
            len(grouped),
            time.time() - t0,
            bar_duration_ms,
            point_size,
        )
    else:
        log.info(
            "Built %d bars in %.2fs using imbalance bars min_ticks=%d span=%d | point_size=%.8f",
            len(grouped),
            time.time() - t0,
            imbalance_min_ticks,
            imbalance_ema_span,
            point_size,
        )
    return grouped, point_size
