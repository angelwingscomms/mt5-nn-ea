"""split/time.py - Makes time bars from ticks, splits into train/val/test."""

import pandas as pd
import numpy as np
from pathlib import Path

# Where ticks live (raw tick data)
TICKS_PATH = Path("data/gold.csv")

# Output directory for train/val/test parquet files
OUTPUT_DIR = Path("data/split")

# Bar settings (from min.yaml: bars.density.primary_bar_seconds = 54)
BAR_SECONDS = 54

# Split percentages + embargo gap
TRAIN_END = 0.70      # 70% of bars go to train
VAL_END = 0.85        # 15% go to val (70->85)
EMBARGO = 1           # 1 bar gap between splits (prevents data leakage)

# Sequence length (from min.yaml: training.seq_len = 9)
SEQ_LEN = 9

# Label timeout (from min.yaml: target.label_timeout_bars = 9)
LABEL_TIMEOUT = 9


def load_ticks(path):
    """Load raw ticks from CSV."""
    df = pd.read_csv(path, parse_dates=["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df


def build_time_bar_ids(times, bar_seconds):
    """
    Assign a bar_id to each tick based on time.
    
    All ticks within the same bar_seconds window get the same bar_id.
    Example: if bar_seconds=54, every 54 seconds = new bar.
    """
    times = pd.to_datetime(times)
    bar_ids = (times - times.min()).dt.total_seconds() // bar_seconds
    return bar_ids.astype(int).values


def make_bars(ticks_df, bar_ids):
    """
    Group ticks by bar_id and compute OHLCV for each bar.
    
    OHLCV = Open, High, Low, Close, Volume
    - open:   first tick price in the group
    - high:   max price in the group
    - low:    min price in the group
    - close:  last tick price in the group
    - volume: sum of volumes in the group
    
    Returns DataFrame with one row per bar.
    """
    bars = []
    
    # Group all ticks by bar_id
    for bar_id, group in ticks_df.groupby(bar_ids):
        group = group.sort_values("time")
        bars.append({
            "bar_id": bar_id,
            "time": group["time"].iloc[0],    # first tick time
            "open": group["price"].iloc[0],   # first price
            "high": group["price"].max(),     # highest price
            "low": group["price"].min(),      # lowest price
            "close": group["price"].iloc[-1],  # last price
            "volume": group["volume"].sum() if "volume" in group.columns else 0,
            "tick_count": len(group),          # how many ticks in this bar
        })
    
    bars_df = pd.DataFrame(bars)
    bars_df = bars_df.sort_values("bar_id").reset_index(drop=True)
    return bars_df


def split_bars(bars_df, train_end, val_end, embargo):
    """
    Split bars into train/val/test sets with embargo gap.
    
    This prevents data leakage - model trained on recent bars 
    shouldn't "see" the validation data during training.
    
    Structure:
        Train: bars[0 : train_end]
        Gap:   bars[train_end : train_end + embargo]  (discarded)
        Val:   bars[train_end + embargo : val_end]
        Gap:   bars[val_end : val_end + embargo]    (discarded)
        Test:  bars[val_end + embargo : end]
    
    Args:
        bars_df: DataFrame with all bars
        train_end: float (0.0 to 1.0) - train cutoff
        val_end: float (0.0 to 1.0) - validation cutoff  
        embargo: int - number of bars to skip between splits
    
    Returns:
        train_df, val_df, test_df
    """
    n = len(bars_df)
    
    # Calculate indices
    train_idx = int(n * train_end)
    val_idx = int(n * val_end)
    
    # Apply embargo gaps
    val_start = train_idx + embargo
    test_start = val_idx + embargo
    
    # If test set would be empty, raise error
    if test_start >= n:
        raise ValueError(f"Dataset too small. n_bars={n}, but test would start at {test_start}")
    
    # Split the data
    train_df = bars_df.iloc[:train_idx].copy()
    val_df = bars_df.iloc[val_start:val_idx].copy()
    test_df = bars_df.iloc[test_start:].copy()
    
    print(f"Split results:")
    print(f"  Train: {len(train_df)} bars (0 to {train_idx})")
    print(f"  Val:   {len(val_df)} bars ({val_start} to {val_idx})")
    print(f"  Test:  {len(test_df)} bars ({test_start} to {n})")
    print(f"  Embargo: {embargo} bars between splits")
    
    return train_df, val_df, test_df


def main():
    """Main function: load ticks -> make bars -> split -> save."""
    print("="*50)
    print("split/time.py - minimal time-bar pipeline")
    print("="*50)
    
    # 1. Load raw ticks
    print(f"\n1. Loading ticks from {TICKS_PATH}")
    ticks = load_ticks(TICKS_PATH)
    print(f"   Loaded {len(ticks)} ticks")
    
    # 2. Assign bar_ids based on time
    print(f"\n2. Building time bars (bar_seconds={BAR_SECONDS})")
    bar_ids = build_time_bar_ids(ticks["time"], BAR_SECONDS)
    print(f"   Created {bar_ids.max() + 1} bars")
    
    # 3. Convert ticks to OHLCV bars
    print("\n3. Making OHLCV bars")
    bars = make_bars(ticks, bar_ids)
    print(f"   Created {len(bars)} bars")
    
    # 4. Split into train/val/test with embargo
    print("\n4. Splitting into train/val/test")
    train_df, val_df, test_df = split_bars(bars, TRAIN_END, VAL_END, EMBARGO)
    
    # 5. Save to parquet files
    print("\n5. Saving to parquet files")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    train_df.to_parquet(OUTPUT_DIR / "train.parquet", index=False)
    val_df.to_parquet(OUTPUT_DIR / "val.parquet", index=False)
    test_df.to_parquet(OUTPUT_DIR / "test.parquet", index=False)
    
    print(f"   Saved to {OUTPUT_DIR}/")
    print(f"   - train.parquet: {len(train_df)} bars")
    print(f"   - val.parquet:   {len(val_df)} bars")
    print(f"   - test.parquet:  {len(test_df)} bars")
    
    print("\nDone!")


if __name__ == "__main__":
    main()