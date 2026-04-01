from __future__ import annotations

import argparse
import gc
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_class_weight
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from shared_mamba import SharedMambaClassifier

EPS = 1e-10
SEQ_LEN = 120
TARGET_HORIZON = 30
SYMBOL_ORDER = ("XAUUSD", "$USDX", "USDJPY")
DEFAULT_DATA_FILE = "gold_market_ticks.csv"
DEFAULT_OUTPUT_FILE = "gold_mamba.onnx"
GOLD_FEATURE_COLUMNS = (
    "ret1",
    "high_rel_prev",
    "low_rel_prev",
    "spread_rel",
    "duration_s",
    "close_in_range",
    "atr14_rel",
    "rv4",
    "rv16",
    "ret8",
    "hour_sin",
    "hour_cos",
)
AUX_FEATURE_COLUMNS = ("ret1", "close_in_range", "atr14_rel", "ret8")
N_FEATURES = len(GOLD_FEATURE_COLUMNS) + 2 * len(AUX_FEATURE_COLUMNS)
PRETRAIN_TARGET_INDICES = (0, 1, 2, 6, 12, 16)
META_FEATURE_INPUT_INDICES = (3, 6, 7, 8)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the laptop-safe GOLD Mamba model.")
    parser.add_argument("--tick-density", type=int, default=540, help="Ticks per primary XAUUSD bar.")
    parser.add_argument("--data-file", type=str, default=DEFAULT_DATA_FILE, help="Combined CSV with symbol,time_msc,bid,ask.")
    parser.add_argument("--output-file", type=str, default=DEFAULT_OUTPUT_FILE, help="ONNX output file.")
    parser.add_argument("--epochs", type=int, default=28, help="Max fine-tuning epochs.")
    parser.add_argument("--pretrain-epochs", type=int, default=3, help="Cheap self-supervised warmup epochs.")
    parser.add_argument("--batch-size", type=int, default=32, help="Fine-tuning batch size.")
    parser.add_argument("--max-train-windows", type=int, default=3072, help="Training window cap for slow laptops.")
    parser.add_argument("--max-eval-windows", type=int, default=1024, help="Validation/calibration/test window cap.")
    parser.add_argument("--device", type=str, default="", help="Optional torch device override.")
    return parser.parse_args()


def build_aligned_bars(csv_path: str, symbols: tuple[str, ...], tick_density: int) -> dict[str, pd.DataFrame]:
    print(f"[INFO] Loading combined tick CSV: {csv_path}...")
    df_all = pd.read_csv(csv_path)
    df_all["symbol"] = df_all["symbol"].astype(str).str.upper()

    sym_gold = symbols[0]
    df_gold = df_all[df_all["symbol"] == sym_gold].sort_values("time_msc").reset_index(drop=True)
    if df_gold.empty:
        raise ValueError(f"No ticks found for {sym_gold}")

    df_gold["bar_id"] = np.arange(len(df_gold)) // tick_density
    bar_ends = df_gold.groupby("bar_id")["time_msc"].last().values

    bars_by_symbol: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df_sym = df_all[df_all["symbol"] == sym].sort_values("time_msc").reset_index(drop=True)
        if df_sym.empty:
            raise ValueError(f"No ticks found for {sym}")

        if sym == sym_gold:
            df_sym_binned = df_gold
        else:
            bar_ids = np.searchsorted(bar_ends, df_sym["time_msc"].values, side="left")
            valid = bar_ids < len(bar_ends)
            df_sym_binned = df_sym[valid].copy()
            df_sym_binned["bar_id"] = bar_ids[valid]

        has_ask = "ask" in df_sym_binned.columns
        agg = {"bid": ["first", "max", "min", "last"], "time_msc": "first"}
        if has_ask:
            df_sym_binned["spread"] = df_sym_binned["ask"] - df_sym_binned["bid"]
            agg_spread = df_sym_binned.groupby("bar_id")["spread"].last()
            agg["ask"] = ["max", "min"]

        df_bars = df_sym_binned.groupby("bar_id").agg(agg)
        if has_ask:
            df_bars.columns = ["open", "high", "low", "close", "time_open", "ask_high", "ask_low"]
            df_bars["spread"] = agg_spread
        else:
            df_bars.columns = ["open", "high", "low", "close", "time_open"]
            df_bars["spread"] = 0.0
            df_bars["ask_high"] = df_bars["high"]
            df_bars["ask_low"] = df_bars["low"]

        df_bars = df_bars.reindex(np.arange(len(bar_ends)))
        df_bars["close"] = df_bars["close"].ffill().bfill()
        df_bars["open"] = df_bars["open"].fillna(df_bars["close"])
        df_bars["high"] = df_bars["high"].fillna(df_bars["close"])
        df_bars["low"] = df_bars["low"].fillna(df_bars["close"])
        df_bars["spread"] = df_bars["spread"].ffill().bfill().fillna(0.0)
        df_bars["ask_high"] = df_bars["ask_high"].fillna(df_bars["high"] + df_bars["spread"])
        df_bars["ask_low"] = df_bars["ask_low"].fillna(df_bars["low"] + df_bars["spread"])

        if sym != sym_gold:
            gold_time_open = df_gold.groupby("bar_id")["time_msc"].first()
            df_bars["time_open"] = df_bars["time_open"].fillna(gold_time_open).ffill().bfill()

        bars_by_symbol[sym] = df_bars.reset_index(drop=True)
        print(f"[INFO] {sym}: built {len(bars_by_symbol[sym])} aligned bars.")

    return bars_by_symbol


def rolling_std(values: pd.Series, window: int) -> pd.Series:
    return values.rolling(window, min_periods=window).std(ddof=0)


def compute_features(df: pd.DataFrame, symbol_idx: int = 0) -> np.ndarray:
    df = df.copy()
    df["dt"] = pd.to_datetime(df["time_open"], unit="ms", utc=True)

    c = df["close"].astype(float)
    prev_c = c.shift(1)
    ret1 = np.log(c / (prev_c + EPS))

    feat = pd.DataFrame(index=df.index)
    feat["ret1"] = ret1
    feat["close_in_range"] = (c - df["low"]) / (df["high"] - df["low"] + 1e-8)
    feat["atr14_rel"] = ta.atr(df["high"], df["low"], c, length=14) / (c + EPS)
    feat["ret8"] = np.log(c / (c.shift(8) + EPS))

    if symbol_idx == 0:
        feat["high_rel_prev"] = np.log(df["high"] / (prev_c + EPS))
        feat["low_rel_prev"] = np.log(df["low"] / (prev_c + EPS))
        feat["spread_rel"] = df["spread"] / (c + EPS)
        feat["duration_s"] = df["dt"].diff().dt.total_seconds().fillna(0.0)
        feat["rv4"] = rolling_std(ret1, 4)
        feat["rv16"] = rolling_std(ret1, 16)
        hours = df["dt"].dt.hour + (df["dt"].dt.minute / 60.0)
        feat["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
        feat["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
        feature_columns = GOLD_FEATURE_COLUMNS
    else:
        feature_columns = AUX_FEATURE_COLUMNS

    return feat.loc[:, feature_columns].values.astype(np.float32)


def get_triple_barrier_labels(
    df_gold: pd.DataFrame,
    tp_mult: float = 9.0,
    sl_mult: float = 5.4,
    horizon: int = TARGET_HORIZON,
) -> np.ndarray:
    c = df_gold["close"].values
    hi = df_gold["high"].values
    lo = df_gold["low"].values
    spr = df_gold["spread"].values
    ask_hi = df_gold["ask_high"].values if "ask_high" in df_gold.columns else hi + spr
    ask_lo = df_gold["ask_low"].values if "ask_low" in df_gold.columns else lo + spr
    atr = ta.atr(df_gold["high"], df_gold["low"], df_gold["close"], length=14).values
    labels = np.zeros(len(df_gold), dtype=np.int64)

    for i in range(len(df_gold) - horizon):
        vol = atr[i]
        if not np.isfinite(vol) or vol <= 0.0:
            continue

        long_entry = c[i] + spr[i]
        short_entry = c[i]

        long_tp = long_entry + tp_mult * vol
        long_sl = long_entry - sl_mult * vol
        short_tp = short_entry - tp_mult * vol
        short_sl = short_entry + sl_mult * vol

        long_result = 0
        short_result = 0

        for j in range(i + 1, i + horizon + 1):
            if long_result == 0:
                hit_tp = hi[j] >= long_tp
                hit_sl = lo[j] <= long_sl
                if hit_tp and not hit_sl:
                    long_result = 1
                elif hit_sl and not hit_tp:
                    long_result = -1
                elif hit_tp and hit_sl:
                    long_result = -1

            if short_result == 0:
                hit_tp = ask_lo[j] <= short_tp
                hit_sl = ask_hi[j] >= short_sl
                if hit_tp and not hit_sl:
                    short_result = 1
                elif hit_sl and not hit_tp:
                    short_result = -1
                elif hit_tp and hit_sl:
                    short_result = -1

            if long_result != 0 and short_result != 0:
                break

        if long_result == 1 and short_result != 1:
            labels[i] = 1
        elif short_result == 1 and long_result != 1:
            labels[i] = 2

    return labels


def choose_evenly_spaced(indices: np.ndarray, max_count: int) -> np.ndarray:
    if len(indices) <= max_count:
        return indices.astype(np.int64)
    positions = np.linspace(0, len(indices) - 1, max_count)
    return indices[np.unique(np.round(positions).astype(np.int64))]


def build_segment_end_indices(
    valid_mask: np.ndarray,
    start_bar: int,
    end_bar: int,
    seq_len: int,
    horizon: int,
) -> np.ndarray:
    first_end = start_bar + seq_len - 1
    last_end = end_bar - horizon - 1
    if last_end < first_end:
        return np.empty(0, dtype=np.int64)

    ends: list[int] = []
    for end_idx in range(first_end, last_end + 1):
        start_idx = end_idx - seq_len + 1
        if valid_mask[start_idx : end_idx + 1].all():
            ends.append(end_idx)
    return np.asarray(ends, dtype=np.int64)


def build_windows(
    features: np.ndarray,
    labels: np.ndarray,
    end_indices: np.ndarray,
    seq_len: int,
) -> tuple[np.ndarray, np.ndarray]:
    xs = np.empty((len(end_indices), seq_len, features.shape[1]), dtype=np.float32)
    ys = np.empty(len(end_indices), dtype=np.int64)
    for i, end_idx in enumerate(end_indices):
        start_idx = end_idx - seq_len + 1
        xs[i] = features[start_idx : end_idx + 1]
        ys[i] = labels[end_idx]
    return xs, ys


class MaskedNextBarHead(nn.Module):
    def __init__(self, backbone: SharedMambaClassifier, target_dim: int):
        super().__init__()
        self.backbone = backbone
        self.head = nn.Sequential(
            nn.Linear(backbone.d_model, backbone.d_model),
            nn.SiLU(),
            nn.Linear(backbone.d_model, target_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone.encode_last(x))


def make_loaders(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
    y_eval: np.ndarray,
    batch_size: int,
) -> tuple[DataLoader, DataLoader]:
    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train)),
        batch_size=batch_size,
        shuffle=True,
    )
    eval_loader = DataLoader(
        TensorDataset(torch.from_numpy(x_eval), torch.from_numpy(y_eval)),
        batch_size=max(batch_size, 64),
        shuffle=False,
    )
    return train_loader, eval_loader


def evaluate_model(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    with torch.no_grad():
        for xb, yb in loader:
            logits = model(xb.to(device)).cpu().numpy()
            logits_list.append(logits)
            labels_list.append(yb.numpy())
    return np.concatenate(logits_list, axis=0), np.concatenate(labels_list, axis=0)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    if len(logits) == 0:
        return 1.0

    logits_t = torch.tensor(logits, dtype=torch.float32)
    labels_t = torch.tensor(labels, dtype=torch.long)
    log_temperature = nn.Parameter(torch.zeros(1))
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.2, max_iter=50, line_search_fn="strong_wolfe")

    def closure() -> torch.Tensor:
        optimizer.zero_grad()
        temperature = torch.exp(log_temperature).clamp_min(1e-3)
        loss = F.cross_entropy(logits_t / temperature, labels_t)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.exp(log_temperature).clamp(0.5, 5.0).item())


def apply_temperature(logits: np.ndarray, temperature: float) -> np.ndarray:
    scaled = logits / max(temperature, 1e-3)
    scaled -= scaled.max(axis=1, keepdims=True)
    probs = np.exp(scaled)
    probs /= probs.sum(axis=1, keepdims=True)
    return probs


def build_meta_features(probs: np.ndarray, x_seq: np.ndarray) -> np.ndarray:
    max_prob = probs.max(axis=1)
    second_prob = np.partition(probs, -2, axis=1)[:, -2]
    entropy = -(probs * np.log(probs + 1e-12)).sum(axis=1)
    last_step = x_seq[:, -1, :]
    extras = last_step[:, META_FEATURE_INPUT_INDICES]
    return np.column_stack([probs, max_prob, max_prob - second_prob, entropy, extras]).astype(np.float32)


def train_meta_classifier(probs: np.ndarray, labels: np.ndarray, x_seq: np.ndarray) -> LogisticRegression | None:
    preds = probs.argmax(axis=1)
    candidate_mask = preds > 0
    if candidate_mask.sum() < 40:
        return None

    features = build_meta_features(probs[candidate_mask], x_seq[candidate_mask])
    targets = (preds[candidate_mask] == labels[candidate_mask]).astype(np.int64)
    if len(np.unique(targets)) < 2:
        return None

    model = LogisticRegression(max_iter=400, class_weight="balanced", solver="lbfgs")
    model.fit(features, targets)
    return model


def choose_thresholds(
    probs: np.ndarray,
    labels: np.ndarray,
    x_seq: np.ndarray,
    meta_model: LogisticRegression | None,
) -> tuple[float, float]:
    preds = probs.argmax(axis=1)
    candidate_mask = preds > 0
    base_conf = probs.max(axis=1)
    meta_probs = np.ones(len(probs), dtype=np.float32)
    meta_grid = [0.0]

    if meta_model is not None and candidate_mask.any():
        candidate_features = build_meta_features(probs[candidate_mask], x_seq[candidate_mask])
        meta_probs[candidate_mask] = meta_model.predict_proba(candidate_features)[:, 1]
        meta_grid = list(np.linspace(0.45, 0.90, 19))

    min_selected = max(12, int(0.03 * len(labels)))
    best_choice: tuple[float, float] | None = None
    best_precision = -1.0
    best_coverage = -1.0

    for primary_thr in np.linspace(0.40, 0.85, 19):
        for meta_thr in meta_grid:
            selected = candidate_mask & (base_conf >= primary_thr) & (meta_probs >= meta_thr)
            if selected.sum() < min_selected:
                continue

            precision = float((preds[selected] == labels[selected]).mean())
            coverage = float(selected.mean())
            if precision > best_precision + 1e-12 or (
                abs(precision - best_precision) <= 1e-12 and coverage > best_coverage
            ):
                best_choice = (float(primary_thr), float(meta_thr))
                best_precision = precision
                best_coverage = coverage

    if best_choice is None:
        return 0.60, 0.55 if meta_model is not None else 0.0
    return best_choice


def summarize_gate(
    name: str,
    probs: np.ndarray,
    labels: np.ndarray,
    x_seq: np.ndarray,
    primary_thr: float,
    meta_model: LogisticRegression | None,
    meta_thr: float,
) -> None:
    preds = probs.argmax(axis=1)
    candidate_mask = preds > 0
    selected = candidate_mask & (probs.max(axis=1) >= primary_thr)

    if meta_model is not None and candidate_mask.any():
        meta_features = build_meta_features(probs[candidate_mask], x_seq[candidate_mask])
        meta_probs = meta_model.predict_proba(meta_features)[:, 1]
        selected_candidates = meta_probs >= meta_thr
        selected = candidate_mask.copy()
        selected[candidate_mask] = selected[candidate_mask] & selected_candidates & (
            probs[candidate_mask].max(axis=1) >= primary_thr
        )

    coverage = float(selected.mean())
    if selected.any():
        precision = float((preds[selected] == labels[selected]).mean())
        print(f"[INFO] {name}: selected precision={precision:.4f} coverage={coverage:.4f} trades={int(selected.sum())}")
    else:
        print(f"[WARN] {name}: no trades passed the abstention gate.")


def format_float_array(values: np.ndarray) -> str:
    return ", ".join(f"{float(v):.8f}f" for v in values)


def build_export_block(
    tick_density: int,
    medians: np.ndarray,
    iqrs: np.ndarray,
    temperature: float,
    primary_thr: float,
    meta_thr: float,
    meta_model: LogisticRegression | None,
) -> str:
    meta_weights = np.zeros(3 + 1 + 1 + 1 + len(META_FEATURE_INPUT_INDICES), dtype=np.float32)
    meta_bias = 0.0
    if meta_model is not None:
        meta_weights = meta_model.coef_[0].astype(np.float32)
        meta_bias = float(meta_model.intercept_[0])

    return "\n".join(
        [
            "--- PASTE THESE INTO gold/live.mq5 ---",
            f"input int    TICK_DENSITY        = {tick_density};",
            f"input double TEMPERATURE         = {temperature:.8f};",
            f"input double PRIMARY_CONFIDENCE  = {primary_thr:.8f};",
            f"input double META_THRESHOLD      = {meta_thr:.8f};",
            f"float medians[{N_FEATURES}] = {{{format_float_array(medians)}}};",
            f"float iqrs[{N_FEATURES}]    = {{{format_float_array(iqrs)}}};",
            f"float meta_weights[{len(meta_weights)}] = {{{format_float_array(meta_weights)}}};",
            f"float meta_bias = {meta_bias:.8f}f;",
        ]
    )


def main() -> None:
    args = parse_args()
    torch.manual_seed(42)
    np.random.seed(42)

    device = torch.device(args.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    print(f"[INFO] Using device: {device}")

    bars_by_symbol = build_aligned_bars(args.data_file, SYMBOL_ORDER, args.tick_density)
    df_gold = bars_by_symbol[SYMBOL_ORDER[0]]
    df_usdx = bars_by_symbol[SYMBOL_ORDER[1]]
    df_usdjpy = bars_by_symbol[SYMBOL_ORDER[2]]

    n_bars = min(len(df_gold), len(df_usdx), len(df_usdjpy))
    df_gold = df_gold.iloc[:n_bars].reset_index(drop=True)
    df_usdx = df_usdx.iloc[:n_bars].reset_index(drop=True)
    df_usdjpy = df_usdjpy.iloc[:n_bars].reset_index(drop=True)
    print(f"[INFO] Aligned bar count: {n_bars}")

    feat_gold = compute_features(df_gold, symbol_idx=0)
    feat_usdx = compute_features(df_usdx, symbol_idx=1)
    feat_usdjpy = compute_features(df_usdjpy, symbol_idx=2)
    X = np.concatenate([feat_gold, feat_usdx, feat_usdjpy], axis=1)
    assert X.shape[1] == N_FEATURES, f"Expected {N_FEATURES} features, got {X.shape[1]}"

    y = get_triple_barrier_labels(df_gold)

    warmup = 20
    X = X[warmup:]
    y = y[warmup:]
    n_rows = len(X)
    embargo = max(SEQ_LEN, TARGET_HORIZON)

    train_end = int(n_rows * 0.70)
    val_end = int(n_rows * 0.82)
    calib_end = int(n_rows * 0.91)

    train_range = (0, train_end)
    val_range = (train_end + embargo, val_end)
    calib_range = (val_end + embargo, calib_end)
    test_range = (calib_end + embargo, n_rows)
    if test_range[0] >= test_range[1]:
        raise ValueError("Dataset is too small for leakage-safe train/val/calibration/test splits.")

    median = np.nanmedian(X[: train_range[1]], axis=0)
    median = np.nan_to_num(median, nan=0.0)
    iqr = np.nanpercentile(X[: train_range[1]], 75, axis=0) - np.nanpercentile(X[: train_range[1]], 25, axis=0)
    iqr = np.nan_to_num(iqr, nan=1.0)
    iqr = np.where(iqr < 1e-6, 1.0, iqr)
    X_s = np.clip((X - median) / iqr, -10.0, 10.0).astype(np.float32)
    valid_mask = ~np.isnan(X_s).any(axis=1)

    train_end_idx = choose_evenly_spaced(
        build_segment_end_indices(valid_mask, *train_range, SEQ_LEN, TARGET_HORIZON),
        args.max_train_windows,
    )
    val_end_idx = choose_evenly_spaced(
        build_segment_end_indices(valid_mask, *val_range, SEQ_LEN, TARGET_HORIZON),
        args.max_eval_windows,
    )
    calib_end_idx = choose_evenly_spaced(
        build_segment_end_indices(valid_mask, *calib_range, SEQ_LEN, TARGET_HORIZON),
        args.max_eval_windows,
    )
    test_end_idx = choose_evenly_spaced(
        build_segment_end_indices(valid_mask, *test_range, SEQ_LEN, TARGET_HORIZON),
        args.max_eval_windows,
    )

    if min(len(train_end_idx), len(val_end_idx), len(calib_end_idx), len(test_end_idx)) == 0:
        raise ValueError("One or more leakage-safe splits ended up empty. Try a smaller tick density or more data.")

    x_train, y_train = build_windows(X_s, y, train_end_idx, SEQ_LEN)
    x_val, y_val = build_windows(X_s, y, val_end_idx, SEQ_LEN)
    x_calib, y_calib = build_windows(X_s, y, calib_end_idx, SEQ_LEN)
    x_test, y_test = build_windows(X_s, y, test_end_idx, SEQ_LEN)
    print(
        f"[INFO] Window counts | train={len(x_train)} val={len(x_val)} calib={len(x_calib)} test={len(x_test)} "
        f"(embargo={embargo})"
    )

    del X
    gc.collect()

    unique_classes = np.unique(y_train)
    class_weights_raw = compute_class_weight("balanced", classes=unique_classes, y=y_train)
    weight_dict = {int(c): float(w) for c, w in zip(unique_classes, class_weights_raw)}
    class_weights = torch.tensor([weight_dict.get(i, 1.0) for i in range(3)], dtype=torch.float32, device=device)
    print(f"[INFO] Class weights: {[round(float(v), 4) for v in class_weights.cpu().numpy()]}")

    model = SharedMambaClassifier(
        n_features=N_FEATURES,
        d_model=48,
        hidden=96,
        dropout=0.20,
        n_layers=2,
        use_sequence_norm=True,
    ).to(device)

    if args.pretrain_epochs > 0:
        pretrain_count = min(len(x_train), args.max_train_windows)
        pretrain_inputs = x_train[:pretrain_count].copy()
        pretrain_targets = pretrain_inputs[:, -1, PRETRAIN_TARGET_INDICES].copy()
        pretrain_inputs[:, -1, :] = 0.0

        pretrain_model = MaskedNextBarHead(model, target_dim=len(PRETRAIN_TARGET_INDICES)).to(device)
        pretrain_loader = DataLoader(
            TensorDataset(torch.from_numpy(pretrain_inputs), torch.from_numpy(pretrain_targets.astype(np.float32))),
            batch_size=args.batch_size,
            shuffle=True,
        )
        pretrain_optimizer = torch.optim.AdamW(pretrain_model.parameters(), lr=6e-4, weight_decay=1e-4)
        pretrain_criterion = nn.SmoothL1Loss()

        print(f"[INFO] Self-supervised warmup on {pretrain_count} windows for {args.pretrain_epochs} epochs...")
        for epoch in range(args.pretrain_epochs):
            pretrain_model.train()
            losses = []
            for xb, yb in pretrain_loader:
                xb = xb.to(device)
                yb = yb.to(device)
                pred = pretrain_model(xb)
                loss = pretrain_criterion(pred, yb)
                pretrain_optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(pretrain_model.parameters(), 1.0)
                pretrain_optimizer.step()
                losses.append(float(loss.item()))
            print(f"  pretrain epoch {epoch + 1:02d} | loss={np.mean(losses):.4f}")

        del pretrain_inputs, pretrain_targets, pretrain_model, pretrain_loader
        gc.collect()

    train_loader, val_loader = make_loaders(x_train, y_train, x_val, y_val, args.batch_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=6e-4, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.02)

    best_val_loss = float("inf")
    best_state = None
    patience = 6
    wait = 0

    for epoch in range(args.epochs):
        model.train()
        train_losses: list[float] = []
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            logits = model(xb)
            loss = criterion(logits, yb)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(float(loss.item()))

        val_logits, val_labels = evaluate_model(model, val_loader, device)
        val_loss = float(F.cross_entropy(torch.tensor(val_logits), torch.tensor(val_labels), weight=class_weights.cpu()).item())
        train_loss = float(np.mean(train_losses))
        print(f"Epoch {epoch:02d} | train_loss={train_loss:.4f} | val_loss={val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                print(f"[INFO] Early stopping at epoch {epoch}")
                break

    if best_state is None:
        raise RuntimeError("Training did not produce a valid checkpoint.")
    model.load_state_dict(best_state)
    model.to(device)

    calib_mid = max(1, len(x_calib) // 2)
    x_temp, y_temp = x_calib[:calib_mid], y_calib[:calib_mid]
    x_meta, y_meta = x_calib[calib_mid:], y_calib[calib_mid:]
    if len(x_meta) == 0:
        x_meta, y_meta = x_temp, y_temp

    temp_loader = DataLoader(TensorDataset(torch.from_numpy(x_temp), torch.from_numpy(y_temp)), batch_size=128, shuffle=False)
    meta_loader = DataLoader(TensorDataset(torch.from_numpy(x_meta), torch.from_numpy(y_meta)), batch_size=128, shuffle=False)
    test_loader = DataLoader(TensorDataset(torch.from_numpy(x_test), torch.from_numpy(y_test)), batch_size=128, shuffle=False)

    temp_logits, temp_labels = evaluate_model(model, temp_loader, device)
    temperature = fit_temperature(temp_logits, temp_labels)
    print(f"[INFO] Temperature scaling fitted with T={temperature:.4f}")

    meta_logits, meta_labels = evaluate_model(model, meta_loader, device)
    meta_probs = apply_temperature(meta_logits, temperature)
    meta_model = train_meta_classifier(meta_probs, meta_labels, x_meta)
    if meta_model is None:
        print("[WARN] Meta-label gate skipped because the calibration slice was too small or one-sided.")
    else:
        print("[INFO] Meta-label gate trained.")

    primary_thr, meta_thr = choose_thresholds(meta_probs, meta_labels, x_meta, meta_model)
    print(f"[INFO] Selected thresholds | primary={primary_thr:.3f} meta={meta_thr:.3f}")
    summarize_gate("calibration", meta_probs, meta_labels, x_meta, primary_thr, meta_model, meta_thr)

    test_logits, test_labels = evaluate_model(model, test_loader, device)
    test_probs = apply_temperature(test_logits, temperature)
    summarize_gate("holdout", test_probs, test_labels, x_test, primary_thr, meta_model, meta_thr)

    model.eval()
    model.to("cpu")
    dummy = torch.randn(1, SEQ_LEN, N_FEATURES)
    torch.onnx.export(
        model,
        dummy,
        args.output_file,
        input_names=["input"],
        output_names=["output"],
        opset_version=14,
        dynamic_axes={"input": {0: "batch"}},
        dynamo=False,
    )
    print(f"[INFO] ONNX saved: {args.output_file}")

    export_block = build_export_block(args.tick_density, median, iqr, temperature, primary_thr, meta_thr, meta_model)
    export_path = Path("gold_export_values.txt")
    export_path.write_text(export_block + "\n", encoding="utf-8")
    print(export_block)
    print(f"[INFO] Export values also written to {export_path}")


if __name__ == "__main__":
    main()
