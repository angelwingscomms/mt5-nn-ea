"""Show how many bars the active config would build without training."""

from __future__ import annotations

from pathlib import Path

from tradebot.pipeline.market_data import build_market_bars as build_market_bars_frame
from tradebot.project_config import resolve_active_project_config
from tradebot.training import apply_shared_settings
from tradebot.workspace import ROOT_DIR, resolve_active_config_path


def main() -> None:
    active_config_path = resolve_active_config_path()
    project = resolve_active_project_config(active_config_path)
    apply_shared_settings(project.values, project=project, shared_config_path=project.config_path)

    values = project.values
    data_path = Path(str(values["DATA_FILE"]))
    if not data_path.is_absolute():
        data_path = (ROOT_DIR / data_path).resolve()
    if not data_path.exists():
        raise FileNotFoundError(
            f"Tick CSV not found: {data_path}. Export data first or point DATA_FILE at an existing CSV."
        )

    use_fixed_time_bars = bool(values.get("USE_FIXED_TIME_BARS", values.get("USE_SECOND_BARS", False)))
    bars, point_size = build_market_bars_frame(
        data_path,
        use_fixed_time_bars=use_fixed_time_bars,
        use_fixed_tick_bars=bool(values["USE_FIXED_TICK_BARS"]),
        tick_density=int(values["PRIMARY_TICK_DENSITY"]),
        max_bars=int(values["MAX_BARS"]) if bool(values.get("USE_MAX_BARS", False)) else 0,
        bar_duration_ms=int(values["PRIMARY_BAR_SECONDS"]) * 1000,
        imbalance_min_ticks=int(values["IMBALANCE_MIN_TICKS"]),
        imbalance_ema_span=int(values["IMBALANCE_EMA_SPAN"]),
        use_imbalance_ema_threshold=bool(values["USE_IMBALANCE_EMA_THRESHOLD"]),
        use_imbalance_min_ticks_div3_threshold=bool(values["USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD"]),
        require_gold_context=bool(values["USE_GOLD_CONTEXT"]) and not bool(values["USE_MINIMAL_FEATURE_SET"]),
    )
    print(f"config={project.config_path}")
    print(f"symbol={values['SYMBOL']}")
    print(f"bars={len(bars)}")
    print(f"point_size={point_size:.8f}")
