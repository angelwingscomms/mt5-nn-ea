data.mq5
```cpp
#property script_show_inputs
input int days_to_export = 60; // Export last N days
input string output_file = "gold_market_ticks.csv";
input string gold_symbol = "XAUUSD";
input string usdx_symbol = "$USDX";
input string usdjpy_symbol = "USDJPY";

void ExportSymbol(string symbol, long start_time, long end_time, int file_handle) {
   long op_start_time = (long)GetTickCount64();
   PrintFormat("[INFO] Exporting %s → %s", symbol, output_file);

   MqlTick ticks[];
   int copied = CopyTicksRange(symbol, ticks, COPY_TICKS_ALL, start_time, end_time);

   if(copied <= 0) {
      PrintFormat("❌ %s: CopyTicksRange failed. Code: %d", symbol, GetLastError());
      return;
   }

   int progress_interval = (copied > 10) ? (copied / 10) : 1000;
   long process_start = (long)GetTickCount64();

   for(int i = 0; i < copied; i++) {
      if(ticks[i].bid <= 0.0) continue;
      FileWrite(file_handle, symbol, ticks[i].time_msc, ticks[i].bid, ticks[i].ask);
      if((i + 1) % progress_interval == 0) {
         int percent = (int)(((long)(i + 1) * 100) / copied);
         long elapsed_ms = (long)GetTickCount64() - process_start;
         long eta = (i > 0) ? (long)((double)elapsed_ms / (i + 1) * (copied - i - 1) / 1000.0) : 0;
         PrintFormat("📊 %s %d%% | Elapsed: %llds | ETA: %llds", symbol, percent, elapsed_ms / 1000, eta);
      }
   }

   long total_time = (long)GetTickCount64() - op_start_time;
   PrintFormat("✅ %s: Exported %d ticks in %.2f sec", symbol, copied, total_time / 1000.0);
}

void OnStart() {
   Print("[INFO] Multi-Symbol Tick Exporter Starting...");

   int h = FileOpen(output_file, FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) {
      PrintFormat("❌ Cannot open file: %s", output_file);
      return;
   }

   FileWrite(h, "symbol", "time_msc", "bid", "ask");

   long end_time = TimeCurrent() * 1000LL;
   long start_time = end_time - (long)days_to_export * 24LL * 3600LL * 1000LL;

   ExportSymbol(gold_symbol, start_time, end_time, h);
   ExportSymbol(usdx_symbol, start_time, end_time, h);
   ExportSymbol(usdjpy_symbol, start_time, end_time, h);

   FileClose(h);

   Print("[INFO] All exports complete.");
}
```

nn.py
```python
import pandas as pd
import numpy as np
import pandas_ta as ta
import torch
import sys
from pathlib import Path
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.utils.class_weight import compute_class_weight

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from shared_mamba import SharedMambaClassifier

torch.manual_seed(42)
np.random.seed(42)

# --- CONFIG ---
TICK_DENSITY  = 54   # ticks per bar for GOLD
SEQ_LEN       = 120
TARGET_HORIZON = 30
N_FEATURES    = 28    # GOLD(16) + USDX(6) + USDJPY(6)
DATA_FILE     = "gold_market_ticks.csv"
SYMBOL_ORDER  = ("XAUUSD", "$USDX", "USDJPY")

# ─────────────────────────────────────────────────────────────
# 1. BAR CONSTRUCTION (TIME-ALIGNED)
# ─────────────────────────────────────────────────────────────
def build_aligned_bars(csv_path, symbols, tick_density):
    print(f"[INFO] Loading combined tick CSV: {csv_path}…")
    df_all = pd.read_csv(csv_path)
    df_all["symbol"] = df_all["symbol"].astype(str).str.upper()

    sym_gold = symbols[0]
    df_gold = df_all[df_all["symbol"] == sym_gold].sort_values("time_msc").reset_index(drop=True)
    if df_gold.empty:
        raise ValueError(f"No ticks found for {sym_gold}")
        
    # Create tick bars for GOLD
    df_gold['bar_id'] = np.arange(len(df_gold)) // tick_density
    bar_ends = df_gold.groupby('bar_id')['time_msc'].last().values
    
    # Bins for exact time alignment. Start slightly before the first tick.
    bins = [-1] + list(bar_ends)
    
    bars_by_symbol = {}
    for sym in symbols:
        df_sym = df_all[df_all["symbol"] == sym].sort_values("time_msc").reset_index(drop=True)
        if df_sym.empty:
            raise ValueError(f"No ticks found for {sym}")
            
        if sym == sym_gold:
            df_sym_binned = df_gold
        else:
            # Assign each tick to the corresponding GOLD bar time window
            # np.searchsorted handles duplicate timestamps properly, unlike pd.cut
            bar_ids = np.searchsorted(bar_ends, df_sym['time_msc'].values, side='left')
            valid = bar_ids < len(bar_ends)
            df_sym_binned = df_sym[valid].copy()
            df_sym_binned['bar_id'] = bar_ids[valid]

        has_ask = 'ask' in df_sym_binned.columns
        agg = {'bid': ['first', 'max', 'min', 'last'], 'time_msc': 'first'}
        
        if has_ask:
            df_sym_binned['spread'] = df_sym_binned['ask'] - df_sym_binned['bid']
            agg_spread = df_sym_binned.groupby('bar_id')['spread'].last()
            agg['ask'] = ['max', 'min']

        df_bars = df_sym_binned.groupby('bar_id').agg(agg)
        
        if has_ask:
            df_bars.columns = ['open', 'high', 'low', 'close', 'time_open', 'ask_high', 'ask_low']
            df_bars['spread'] = agg_spread
        else:
            df_bars.columns = ['open', 'high', 'low', 'close', 'time_open']
            df_bars['spread'] = 0.0
            df_bars['ask_high'] = df_bars['high']
            df_bars['ask_low'] = df_bars['low']

        # Reindex to ensure all GOLD bar_ids are present
        df_bars = df_bars.reindex(np.arange(len(bar_ends)))
        
        # Forward fill if a symbol had no ticks during a GOLD bar
        df_bars['close'] = df_bars['close'].ffill().bfill()
        df_bars['open'] = df_bars['open'].fillna(df_bars['close'])
        df_bars['high'] = df_bars['high'].fillna(df_bars['close'])
        df_bars['low'] = df_bars['low'].fillna(df_bars['close'])
        
        # Spread should also be forward-filled, not zeroed
        df_bars['spread'] = df_bars['spread'].ffill().bfill()
        
        # Ask prices should fall back to close + spread if there were no ticks
        df_bars['ask_high'] = df_bars['ask_high'].fillna(df_bars['high'] + df_bars['spread'])
        df_bars['ask_low'] = df_bars['ask_low'].fillna(df_bars['low'] + df_bars['spread'])

        if sym != sym_gold:
            gold_time_open = df_gold.groupby('bar_id')['time_msc'].first()
            df_bars['time_open'] = df_bars['time_open'].fillna(gold_time_open).ffill().bfill()

        bars_by_symbol[sym] = df_bars.reset_index(drop=True)
        print(f"[INFO] {sym}: built {len(bars_by_symbol[sym])} aligned bars.")

    return bars_by_symbol


# ─────────────────────────────────────────────────────────────
# 2. FEATURE ENGINEERING — symbol-specific features
# ─────────────────────────────────────────────────────────────
# GOLD: 16 features (all)
#   f0  = log return (close-to-close)
#   f1  = spread / close
#   f2  = bar duration in seconds
#   f3  = upper wick / close
#   f4  = lower wick / close
#   f5  = range / close
#   f6  = close position in range [0,1]
#   f7  = MACD line / close         (EMA12 - EMA26)
#   f8  = MACD signal / close       (EMA9 of MACD line)
#   f9  = MACD histogram / close    (MACD line - signal)
#   f10 = ATR(14) / close
#   f11 = sin(2π * UTC hour / 24)
#   f12 = cos(2π * UTC hour / 24)
#   f13 = sin(2π * UTC weekday / 7)
#   f14 = cos(2π * UTC weekday / 7)
#   f15 = RSI(14) / 100  — normalised to [0, 1]
#
# USDX/USDJPY: 6 features (dropped f2, f3, f4, f9, f11-f14)
#   f0  = log return (close-to-close)
#   f1  = spread / close
#   f5  = range / close
#   f6  = close position in range [0,1]
#   f7  = MACD line / close         (EMA12 - EMA26)
#   f8  = MACD signal / close       (EMA9 of MACD line)
#   f10 = ATR(14) / close
#   f15 = RSI(14) / 100  — normalised to [0, 1]

def compute_features(df, symbol_idx=0):
    """
    Computes features for a bars DataFrame.
    symbol_idx: 0=GOLD (16 features), 1=USDX (6 features), 2=USDJPY (6 features)
    Returns a (N, n_features) numpy float32 array and the datetime series.
    """
    df = df.copy()
    # Interpret time_open as raw broker time (not UTC) to match MQL5 logic
    df['dt'] = pd.to_datetime(df['time_open'], unit='ms')

    c  = df['close']
    c1 = c.shift(1)

    feat = pd.DataFrame(index=df.index)

    # Price-based features
    feat['f0']  = np.log(c / (c1 + 1e-10))
    feat['f1']  = df['spread'] / (c + 1e-10)
    
    # Only GOLD gets f2, f3, f4
    if symbol_idx == 0:
        feat['f2']  = df['dt'].diff().dt.total_seconds().fillna(0)
        feat['f3']  = (df['high'] - df[['open', 'close']].max(axis=1)) / (c + 1e-10)
        feat['f4']  = (df[['open', 'close']].min(axis=1) - df['low']) / (c + 1e-10)
    
    feat['f5']  = (df['high'] - df['low']) / (c + 1e-10)
    feat['f6']  = (c - df['low']) / (df['high'] - df['low'] + 1e-8)

    # MACD (EMA 12, 26, 9)
    # pandas_ta macd returns [MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9]
    m = ta.macd(c, 12, 26, 9)
    feat['f7']  = m.iloc[:, 0] / (c + 1e-10)   # MACD line
    feat['f8']  = m.iloc[:, 2] / (c + 1e-10)   # Signal line
    
    # Only GOLD gets f9 (MACD histogram) - it's linearly redundant (f9 = f7 - f8)
    if symbol_idx == 0:
        feat['f9']  = m.iloc[:, 1] / (c + 1e-10)   # Histogram

    # ATR(14)
    feat['f10'] = ta.atr(df['high'], df['low'], c, length=14) / (c + 1e-10)

    # Time cyclicals - only GOLD gets these (USDX/USDJPY are GOLD-aligned)
    if symbol_idx == 0:
        hours = df['dt'].dt.hour
        days  = df['dt'].dt.dayofweek # Mon=0, Sun=6 (Matches MQL5 (days+3)%7)
        
        feat['f11'] = np.sin(2 * np.pi * hours / 24.0)
        feat['f12'] = np.cos(2 * np.pi * hours / 24.0)
        feat['f13'] = np.sin(2 * np.pi * days / 7.0)
        feat['f14'] = np.cos(2 * np.pi * days / 7.0)

    # RSI(14) normalised
    feat['f15'] = ta.rsi(c, length=14) / 100.0

    return feat.values.astype(np.float32), df['dt']


# ─────────────────────────────────────────────────────────────
# 3. SYMMETRIC LABELING (GOLD only, ATR-based TP/SL)
# ─────────────────────────────────────────────────────────────
def get_symmetric_labels(df_gold, tp_mult=9.0, sl_mult=5.4):
    c   = df_gold['close'].values
    hi  = df_gold['high'].values
    lo  = df_gold['low'].values
    spr = df_gold['spread'].values
    ask_hi = df_gold['ask_high'].values if 'ask_high' in df_gold.columns else hi + spr
    ask_lo = df_gold['ask_low'].values if 'ask_low' in df_gold.columns else lo + spr
    atr = ta.atr(df_gold['high'], df_gold['low'], df_gold['close'], length=14).values
    labels = np.zeros(len(df_gold), dtype=np.int64)

    for i in range(len(df_gold) - TARGET_HORIZON):
        if np.isnan(atr[i]) or atr[i] == 0:
            continue
            
        # Long entry is at ask (close + spread), exits are evaluated at bid
        long_entry = c[i] + spr[i]
        b_tp = long_entry + tp_mult * atr[i]
        b_sl = long_entry - sl_mult * atr[i]
        
        # Short entry is at bid (close), exits are evaluated at ask (true ask_high / ask_low)
        short_entry = c[i]
        s_tp = short_entry - tp_mult * atr[i]
        s_sl = short_entry + sl_mult * atr[i]

        buy_done = sell_done = False
        buy_won  = sell_won  = False

        for j in range(i + 1, i + TARGET_HORIZON + 1):
            if not buy_done:
                hit_tp = hi[j] >= b_tp
                hit_sl = lo[j] <= b_sl
                # If both hit in same bar, assume worst case (SL)
                if hit_tp and hit_sl:
                    buy_done = True
                elif hit_tp:
                    buy_won = True;  buy_done = True
                elif hit_sl:
                    buy_done = True
                    
            if not sell_done:
                hit_tp = ask_lo[j] <= s_tp
                hit_sl = ask_hi[j] >= s_sl
                # If both hit in same bar, assume worst case (SL)
                if hit_tp and hit_sl:
                    sell_done = True
                elif hit_tp:
                    sell_won = True; sell_done = True
                elif hit_sl:
                    sell_done = True
                    
            if buy_done and sell_done:
                break

        if   buy_won and not sell_won:  labels[i] = 1
        elif sell_won and not buy_won:  labels[i] = 2

    return labels


def main():
    # ─────────────────────────────────────────────────────────────
    # 4. LOAD DATA & BUILD FEATURES
    # ─────────────────────────────────────────────────────────────
    bars_by_symbol = build_aligned_bars(DATA_FILE, SYMBOL_ORDER, TICK_DENSITY)
    df_gold   = bars_by_symbol[SYMBOL_ORDER[0]]
    df_usdx   = bars_by_symbol[SYMBOL_ORDER[1]]
    df_usdjpy = bars_by_symbol[SYMBOL_ORDER[2]]

    # Align all three to the same length (shortest wins)
    N = min(len(df_gold), len(df_usdx), len(df_usdjpy))
    df_gold   = df_gold.iloc[:N].reset_index(drop=True)
    df_usdx   = df_usdx.iloc[:N].reset_index(drop=True)
    df_usdjpy = df_usdjpy.iloc[:N].reset_index(drop=True)

    print(f"[INFO] Aligned bar count: {N}")

    feat_gold,  _ = compute_features(df_gold, symbol_idx=0)
    feat_usdx,  _ = compute_features(df_usdx, symbol_idx=1)
    feat_usdjpy,_ = compute_features(df_usdjpy, symbol_idx=2)

    # Concatenate: [gold(16) | usdx(6) | usdjpy(6)] = 28 features per bar
    X = np.concatenate([feat_gold, feat_usdx, feat_usdjpy], axis=1)  # (N, 28)
    assert X.shape[1] == N_FEATURES, f"Expected 28 features, got {X.shape[1]}"

    # Labels from GOLD bars only
    y = get_symmetric_labels(df_gold)

    # ─────────────────────────────────────────────────────────────
    # 5. ROBUST SCALING (fit on train partition only — no leakage)
    # ─────────────────────────────────────────────────────────────
    # DROP WARMUP BARS (first 50 bars) to ensure indicators are stable
    WARMUP = 50
    X = X[WARMUP:]
    y = y[WARMUP:]
    N = len(X)
    
    raw_split = int(N * 0.9)

    # Calculate median and iqr ignoring NaNs on TRAINING SET ONLY
    median = np.nanmedian(X[:raw_split], axis=0)
    median = np.nan_to_num(median, nan=0.0) 
    iqr    = (np.nanpercentile(X[:raw_split], 75, axis=0)
            - np.nanpercentile(X[:raw_split], 25, axis=0))
    iqr    = np.nan_to_num(iqr, nan=1.0)
    iqr    = np.where(iqr < 1e-6, 1.0, iqr)

    # Scale the entire dataset using training statistics
    X_s = np.clip((X - median) / iqr, -10, 10).astype(np.float32)

    # ─────────────────────────────────────────────────────────────
    # 6. SEQUENCE CONSTRUCTION  (N_seq, SEQ_LEN, 48)
    # ─────────────────────────────────────────────────────────────
    # Re-evaluate valid_mask after scaling/clipping
    valid_mask = ~np.isnan(X_s).any(axis=1)

    X_seq_train, y_seq_train = [], []
    valid_train_indices = []
    for i in range(raw_split - SEQ_LEN):
        # A sequence is valid if all bars in the sequence are valid and the label is within the valid range
        if valid_mask[i : i + SEQ_LEN].all() and (i + SEQ_LEN - 1 + TARGET_HORIZON < N):
            valid_train_indices.append(i)
            
    # USE 5.4% OF TRAINING DATA to prevent OOM on 8GB RAM
    import gc
    train_size = max(1, int(len(valid_train_indices) * 0.054))
    # Use evenly spaced samples to cover the whole training period
    # or just a random sample. A random sample is good for i.i.d.
    np.random.seed(42)
    selected_train_indices = np.random.choice(valid_train_indices, size=train_size, replace=False)
    
    for i in selected_train_indices:
        X_seq_train.append(X_s[i : i + SEQ_LEN])
        y_seq_train.append(y[i + SEQ_LEN - 1])
        
    X_seq_val, y_seq_val = [], []
    # Prevent lookahead leakage: Validation features must not overlap with training label horizons
    for i in range(raw_split + TARGET_HORIZON, N - SEQ_LEN):
        if valid_mask[i : i + SEQ_LEN].all() and (i + SEQ_LEN - 1 + TARGET_HORIZON < N):
            X_seq_val.append(X_s[i : i + SEQ_LEN])
            y_seq_val.append(y[i + SEQ_LEN - 1])

    # Free memory before tensor conversion
    del X_s, X, y
    gc.collect()

    X_train = torch.tensor(np.array(X_seq_train), dtype=torch.float32)
    y_train = torch.tensor(np.array(y_seq_train), dtype=torch.int64)
    X_val   = torch.tensor(np.array(X_seq_val), dtype=torch.float32)
    y_val   = torch.tensor(np.array(y_seq_val), dtype=torch.int64)

    # ─────────────────────────────────────────────────────────────
    # 7. DATASETS & CLASS WEIGHTS
    # ─────────────────────────────────────────────────────────────
    unique_classes = np.unique(y_seq_train)
    cw = compute_class_weight('balanced', classes=unique_classes, y=np.array(y_seq_train))
    weight_dict = {c: w for c, w in zip(unique_classes, cw)}
    cw_full = [weight_dict.get(i, 1.0) for i in range(3)]
    class_weights = torch.tensor(cw_full, dtype=torch.float32)
    print(f"[INFO] Class weights: {cw_full}")

    # For CPU, we use smaller batch size and num_workers=0 (default) for stability, but we can try to optimize
    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=16,  shuffle=True,  drop_last=True)
    val_loader   = DataLoader(TensorDataset(X_val,   y_val),   batch_size=32)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device}")

    # ─────────────────────────────────────────────────────────────
    # 8. MAMBA MODEL  (d_model = 128)
    # ─────────────────────────────────────────────────────────────
    # Reduce model size slightly for faster CPU training without losing too much capacity
    model     = SharedMambaClassifier(n_features=N_FEATURES, d_model=64, hidden=128).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    class_weights = class_weights.to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    # ─────────────────────────────────────────────────────────────
    # 9. TRAINING WITH EARLY STOPPING
    # ─────────────────────────────────────────────────────────────
    best_val_loss = float('inf')
    patience, wait = 10, 0
    best_state = None

    for epoch in range(54):
        model.train()
        train_losses = []
        for batch_idx, (xb, yb) in enumerate(train_loader):
            xb, yb = xb.to(device), yb.to(device)
            out  = model(xb)
            loss = criterion(out, yb)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item())
            
            if (batch_idx + 1) % 5 == 0 or (batch_idx + 1) == len(train_loader):
                # Use carriage return \r to overwrite the same line, preventing massive console spam
                print(f"\r  Epoch {epoch:02d} | Batch {batch_idx+1:03d}/{len(train_loader)} | loss: {loss.item():.4f}", end="", flush=True)

        print() # New line after the epoch's batches are complete

        model.eval()
        val_losses = []
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                val_losses.append(criterion(model(xb), yb).item())
        
        # Guard against empty validation set
        if len(val_losses) == 0:
            print("[WARN] Validation set is empty! Check your dataset size.")
            val_loss = float('inf')
        else:
            val_loss = float(np.mean(val_losses))
            
        train_loss = float(np.mean(train_losses))
        print(f"Epoch {epoch:02d} Summary | train_loss: {train_loss:.4f} | val_loss: {val_loss:.4f}\n")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state    = {k: v.clone() for k, v in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                print(f"✅ Early stopping triggered at epoch {epoch} (No improvement for {patience} epochs)")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    else:
        print("[WARN] No best state found. Using the last epoch's state.")

    # ─────────────────────────────────────────────────────────────
    # 10. ONNX EXPORT — input shape (1, 120, 48)
    # ─────────────────────────────────────────────────────────────
    model.eval()
    model.to("cpu")
    dummy = torch.randn(1, SEQ_LEN, N_FEATURES)
    torch.onnx.export(
        model, dummy, "gold_mamba.onnx",
        input_names=["input"], output_names=["output"],
        opset_version=14,
        dynamic_axes={"input": {0: "batch"}},
        dynamo=False,
    )
    print("✅ ONNX saved: gold_mamba.onnx")

    # ─────────────────────────────────────────────────────────────
    # 11. SCALER OUTPUT FOR live.mq5
    # ─────────────────────────────────────────────────────────────
    print("\n--- PASTE THESE INTO live.mq5 ---")
    print(f"float medians[28] = {{{', '.join([f'{v:.8f}f' for v in median])}}};")
    print(f"float iqrs[28]    = {{{', '.join([f'{v:.8f}f' for v in iqr])}}};")

if __name__ == "__main__":
    main()
```

live.mq5
```cpp
// live.mq5 — GOLD Mamba EA  (48 features: GOLD[16] | USDX[16] | USDJPY[16])
//
// Feature block layout (mirrors nn.py exactly):
//   indices  0-15  →  GOLD   features f0..f15
//   indices 16-31  →  USDX   features f0..f15
//   indices 32-47  →  USDJPY features f0..f15
//
// Per-symbol feature index offsets:
//   f0  log return          f1  spread/close      f2  bar seconds
//   f3  upper wick          f4  lower wick         f5  range/close
//   f6  close-in-range      f7  MACD line          f8  MACD signal
//   f9  MACD histogram      f10 ATR14/close        f11 sin(hour)
//   f12 cos(hour)           f13 sin(weekday)       f14 cos(weekday)
//   f15 RSI14/100

#include <Trade\Trade.mqh>
#resource "\\Experts\\nn\\gold\\gold_mamba.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 54;
input double SL_MULTIPLIER = 5.4;
input double TP_MULTIPLIER = 9.0;
input double LOT_SIZE      = 0.01;
input double CONFIDENCE    = 0.72;
input int    MAGIC_NUMBER  = 777777;

// Change to match your broker's Dollar Index and USDJPY symbols if needed
input string USDX_SYMBOL   = "USDX";
input string USDJPY_SYMBOL = "USDJPY";

long   onnx_handle = INVALID_HANDLE;
CTrade trade;

// PASTE FROM PYTHON OUTPUT
float medians[48] = {0.00004015f, 0.00002398f, 1425.88354492f, 0.00069872f, 0.00087209f, 0.00349893f, 0.53487962f, -0.00002065f, -0.00004840f, -0.00003089f, 0.00375151f, 0.00000000f, -0.25881904f, 0.43388373f, -0.22252093f, 0.49876642f, -0.00000000f, 0.00035538f, 1418.78100586f, 0.00012120f, 0.00013114f, 0.00069006f, 0.48076913f, 0.00012648f, 0.00013797f, 0.00000277f, 0.00075427f, 0.00000000f, -0.25881904f, 0.43388373f, -0.22252093f, 0.51894510f, 0.00002558f, 0.00000637f, 1425.25500488f, 0.00016493f, 0.00018991f, 0.00087831f, 0.54679620f, 0.00017734f, 0.00018634f, -0.00000766f, 0.00096094f, 0.00000000f, -0.25881904f, 0.43388373f, -0.22252093f, 0.52497852f};
float iqrs[48]    = {0.00287351f, 0.00001323f, 607.73144531f, 0.00101565f, 0.00120652f, 0.00292759f, 0.53026927f, 0.00349456f, 0.00334269f, 0.00104663f, 0.00217146f, 1.41421354f, 1.20710683f, 0.78183150f, 1.52445865f, 0.15545326f, 0.00059601f, 0.00000663f, 622.35498047f, 0.00022064f, 0.00022418f, 0.00054076f, 0.65764594f, 0.00078600f, 0.00073110f, 0.00023769f, 0.00029721f, 1.41421354f, 1.20710683f, 0.78183150f, 1.52445865f, 0.16224563f, 0.00080674f, 0.00000631f, 608.31347656f, 0.00024987f, 0.00027996f, 0.00055235f, 0.59692234f, 0.00087609f, 0.00086383f, 0.00027275f, 0.00026398f, 1.41421354f, 1.20710683f, 0.78183150f, 1.52445865f, 0.15589777f};

// ─── Bar accumulator ─────────────────────────────────────────────
struct Bar {
   double o, h, l, c, spread;
   double atr14;           // Wilder ATR(14)
   double ema12, ema26;    // for MACD
   double macd_sig;        // MACD signal EMA(9)
   double rsi_gain;        // Wilder smoothed avg gain
   double rsi_loss;        // Wilder smoothed avg loss
   ulong  time_msc;
   bool   valid;           // false until first bar after warmup
};

// 3 symbols × 200 bars ring buffer
//   GOLD=0  USDX=1  USDJPY=2
Bar history[3][200];
Bar cur_b[3];
int ticks_in_bar[3];
bool bar_started[3];
ulong last_tick_time[3];

// Per-symbol ATR warmup (need 14 bars before Wilder kicks in)
int    warmup_count[3];
double warmup_sum[3];       // accumulator for simple average during warmup

// RSI warmup: need 14 bars of gain/loss before first valid RSI
int    rsi_warmup[3];
double rsi_gain_acc[3];
double rsi_loss_acc[3];

float input_data[5760];   // 1 × 120 × 48 = 5760 floats, row-major
float output_data[3];

void UpdateIndicators(int s, Bar &b);
void Predict();
void Execute(int sig);
void LoadHistory();
void ProcessSymbolSnapshotToTime(int s, ulong end_time_msc);
void CloseBar();

//+------------------------------------------------------------------+
int OnInit() {
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("[FATAL] OnnxCreateFromBuffer failed: ", GetLastError());
      return INIT_FAILED;
   }

   const long in_shape[]  = {1, 120, 48};
   const long out_shape[] = {1, 3};
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape) ||
      !OnnxSetOutputShape(onnx_handle, 0, out_shape)) {
      Print("[FATAL] OnnxSetShape failed: ", GetLastError());
      OnnxRelease(onnx_handle);
      onnx_handle = INVALID_HANDLE;
      return INIT_FAILED;
   }

   // Reset all state
   ArrayInitialize(ticks_in_bar, 0);
   ArrayInitialize(bar_started, false);
   ArrayInitialize(last_tick_time, 0);
   ArrayInitialize(warmup_count, 0);
   ArrayInitialize(warmup_sum,   0);
   ArrayInitialize(rsi_warmup,   0);
   ArrayInitialize(rsi_gain_acc, 0);
   ArrayInitialize(rsi_loss_acc, 0);
   ArrayInitialize(input_data,    0);
   for(int s = 0; s < 3; s++)
      for(int b = 0; b < 200; b++) history[s][b].valid = false;

   // Initialize last_tick_time to current time to avoid 1970 bug
   for(int s = 0; s < 3; s++) {
      MqlTick t;
      if(SymbolInfoTick(SymbolForIdx(s), t)) {
         last_tick_time[s] = t.time_msc;
      } else {
         last_tick_time[s] = TimeCurrent() * 1000LL;
      }
   }

   Print("[INFO] EA initialised. Symbols: XAUUSD | ", USDX_SYMBOL, " | ", USDJPY_SYMBOL);
   
   trade.SetExpertMagicNumber(777777); // Set magic number to avoid interfering with other EAs/manual trades
   
   // Pre-load history to avoid 18-hour wait time
   LoadHistory();
   
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   if(onnx_handle != INVALID_HANDLE) OnnxRelease(onnx_handle);
}

//+------------------------------------------------------------------+
// Map symbol index → broker symbol string
string SymbolForIdx(int s) {
   if(s == 0) return _Symbol;
   if(s == 1) return USDX_SYMBOL;
   return USDJPY_SYMBOL;
}

//+------------------------------------------------------------------+
void ProcessTick(int s, MqlTick &t) {
   if(t.bid <= 0.0) return;
   
   if(!bar_started[s]) {
      cur_b[s].o        = t.bid;
      cur_b[s].h        = t.bid;
      cur_b[s].l        = t.bid;
      cur_b[s].c        = t.bid;
      cur_b[s].spread   = 0;
      cur_b[s].time_msc = t.time_msc;
      ticks_in_bar[s]   = 0;
      bar_started[s]    = true;
   }

   cur_b[s].h = MathMax(cur_b[s].h, t.bid);
   cur_b[s].l = MathMin(cur_b[s].l, t.bid);
   cur_b[s].c = t.bid;
   cur_b[s].spread = (t.ask - t.bid); // Store last spread to match Python's .last()
   ticks_in_bar[s]++;
}

void ProcessSymbolSnapshotToTime(int s, ulong end_time_msc) {
   if (last_tick_time[s] >= end_time_msc) return;
   
   MqlTick ticks[];
   int count = CopyTicksRange(SymbolForIdx(s), ticks, COPY_TICKS_ALL, last_tick_time[s] + 1, end_time_msc);
   if(count > 0) {
      for(int i = 0; i < count; i++) {
         if(ticks[i].bid > 0.0) {
            ProcessTick(s, ticks[i]);
         }
      }
   }
   // Always advance time pointer so we don't query empty intervals repeatedly
   last_tick_time[s] = end_time_msc;
}

void CloseBar() {
   for(int s = 0; s < 3; s++) {
      if(ticks_in_bar[s] == 0) {
         // No ticks received for this symbol during GOLD's bar. Forward fill from history.
         if(history[s][0].valid || history[s][0].c > 0) {
            double prev_c = history[s][0].c;
            cur_b[s].o = prev_c;
            cur_b[s].h = prev_c;
            cur_b[s].l = prev_c;
            cur_b[s].c = prev_c;
            cur_b[s].spread = history[s][0].spread;
         } else {
            // Fallback if very first bar has no ticks (rare but possible for illiquid crosses)
            MqlTick fallback;
            if(SymbolInfoTick(SymbolForIdx(s), fallback) && fallback.bid > 0) {
               cur_b[s].o = cur_b[s].h = cur_b[s].l = cur_b[s].c = fallback.bid;
               cur_b[s].spread = fallback.ask - fallback.bid;
            }
         }
         cur_b[s].time_msc = cur_b[0].time_msc; // align time with GOLD ONLY if empty
      }
      
      UpdateIndicators(s, cur_b[s]);
      
      for(int i = 199; i > 0; i--) history[s][i] = history[s][i-1];
      history[s][0] = cur_b[s];
      
      // Reset for next bar
      ticks_in_bar[s] = 0;
      bar_started[s] = false;
   }
}

void OnTick() {
   MqlTick gold_ticks[];
   // Fetch all GOLD ticks since last_tick_time[0]
   int count = CopyTicks(_Symbol, gold_ticks, COPY_TICKS_ALL, last_tick_time[0] + 1, 100000);
   if(count <= 0) return;

   for(int i = 0; i < count; i++) {
      if(gold_ticks[i].bid <= 0.0) continue;
      
      ProcessTick(0, gold_ticks[i]);
      last_tick_time[0] = gold_ticks[i].time_msc;
      
      if(ticks_in_bar[0] >= TICK_DENSITY) {
         // GOLD bar complete.
         // Now fetch USDX and USDJPY up to THIS exact time_msc
         ProcessSymbolSnapshotToTime(1, last_tick_time[0]);
         ProcessSymbolSnapshotToTime(2, last_tick_time[0]);
         
         CloseBar();

         if(history[0][120].valid && history[1][120].valid && history[2][120].valid) {
            Predict();
         }
      }
   }
}

void LoadHistory() {
   Print("[INFO] Pre-loading history...");
   // We need enough bars for SEQ_LEN(120) + WARMUP(50) = 170 bars. 
   // Fetching last 3 days of ticks should be more than enough for GOLD.
   ulong start_time_msc = (TimeCurrent() - 86400 * 3) * 1000LL; 
   
   MqlTick hist_ticks[];
   int copied = CopyTicks(_Symbol, hist_ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   if (copied <= 0) {
      Print("[WARN] Failed to load history ticks for GOLD. Trying 1 day...");
      start_time_msc = (TimeCurrent() - 86400 * 1) * 1000LL;
      copied = CopyTicks(_Symbol, hist_ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   }
   
   if (copied <= 0) {
      Print("[ERROR] No history ticks found.");
      return;
   }
   
   last_tick_time[0] = hist_ticks[0].time_msc - 1;
   last_tick_time[1] = hist_ticks[0].time_msc - 1;
   last_tick_time[2] = hist_ticks[0].time_msc - 1;
   
   for(int i = 0; i < copied; i++) {
      if(hist_ticks[i].bid <= 0.0) continue;
      
      ProcessTick(0, hist_ticks[i]);
      last_tick_time[0] = hist_ticks[i].time_msc;
      
      if(ticks_in_bar[0] >= TICK_DENSITY) {
         ProcessSymbolSnapshotToTime(1, last_tick_time[0]);
         ProcessSymbolSnapshotToTime(2, last_tick_time[0]);
         CloseBar();
      }
   }
   
   Print("[INFO] History loaded. Buffer status: ", history[0][120].valid ? "VALID" : "INCOMPLETE");
}

//+------------------------------------------------------------------+
// UpdateIndicators: incremental Wilder ATR(14), MACD EMAs, RSI Wilder(14)
void UpdateIndicators(int s, Bar &b) {
   Bar p = history[s][0];   // previous bar (newest in buffer before shift)

   bool is_first = (warmup_count[s] == 0);

   // ── TR / ATR(14) ──────────────────────────────────────────────
   double tr;
   if(is_first) {
      tr    = b.h - b.l;
   } else {
      tr = MathMax(b.h - b.l,
           MathMax(MathAbs(b.h - p.c),
                   MathAbs(b.l - p.c)));
   }

   if(warmup_count[s] < 14) {
      warmup_sum[s] += tr;
      warmup_count[s]++;
      b.atr14 = warmup_sum[s] / warmup_count[s];
   } else {
      double prev_atr = (p.atr14 > 0 ? p.atr14 : tr); // guard
      b.atr14 = (tr - prev_atr) / 14.0 + prev_atr;    // Wilder smoothing
   }

   // ── MACD EMAs ─────────────────────────────────────────────────
   if(is_first) {
      b.ema12    = b.c;
      b.ema26    = b.c;
      b.macd_sig = 0;
   } else {
      b.ema12    = (b.c - p.ema12)    * (2.0 / 13.0) + p.ema12;
      b.ema26    = (b.c - p.ema26)    * (2.0 / 27.0) + p.ema26;
      double macd_raw = b.ema12 - b.ema26;
      b.macd_sig = (macd_raw - p.macd_sig) * (2.0 / 10.0) + p.macd_sig;
   }

   // ── RSI(14) Wilder ────────────────────────────────────────────
   if(is_first) {
      b.rsi_gain = 0;
      b.rsi_loss = 0;
   } else {
      double chg   = b.c - p.c;
      double gain  = (chg > 0) ? chg : 0.0;
      double loss  = (chg < 0) ? -chg : 0.0;

      if(rsi_warmup[s] < 14) {
         rsi_gain_acc[s] += gain;
         rsi_loss_acc[s] += loss;
         rsi_warmup[s]++;
         if(rsi_warmup[s] == 14) {
            b.rsi_gain = rsi_gain_acc[s] / 14.0;
            b.rsi_loss = rsi_loss_acc[s] / 14.0;
         } else {
            b.rsi_gain = 0;
            b.rsi_loss = 0;
         }
      } else {
         b.rsi_gain = (p.rsi_gain * 13.0 + gain) / 14.0;
         b.rsi_loss = (p.rsi_loss * 13.0 + loss) / 14.0;
      }
   }

   b.valid = (warmup_count[s] >= 14 && rsi_warmup[s] >= 14);
}

//+------------------------------------------------------------------+
// ComputeRSI: returns RSI value in [0,100] from bar's Wilder state
double ComputeRSI(Bar &b) {
   if(b.rsi_loss < 1e-10) return (b.rsi_gain > 0) ? 100.0 : 50.0;
   double rs = b.rsi_gain / b.rsi_loss;
   return 100.0 - (100.0 / (1.0 + rs));
}

//+------------------------------------------------------------------+
// ExtractFeatures: fills f[16] for one symbol at bar index h in buffer
// 'h'   = history index (0 = newest)
// 'h+1' = previous bar for log-return denominator
void ExtractFeatures(int s, int h, float &f[]) {
   Bar b  = history[s][h];
   Bar bp = history[s][h + 1];   // previous bar

   double cl      = b.c;
   // Ensure time_msc is treated consistently with Python (broker time integer hour/weekday)
   double utc_h   = (double)((b.time_msc / 3600000ULL) % 24);
   double utc_d   = (double)(((b.time_msc / 86400000ULL) + 3) % 7);
   double macd    = b.ema12 - b.ema26;
   double rsi_val = ComputeRSI(b);

   f[0]  = (float)MathLog(cl / (bp.c + 1e-10));
   f[1]  = (float)(b.spread / (cl + 1e-10));
   f[2]  = (float)((double)(b.time_msc - bp.time_msc) / 1000.0);
   f[3]  = (float)((b.h - MathMax(b.o, cl)) / (cl + 1e-10));
   f[4]  = (float)((MathMin(b.o, cl) - b.l) / (cl + 1e-10));
   f[5]  = (float)((b.h - b.l) / (cl + 1e-10));
   f[6]  = (float)((cl - b.l) / (b.h - b.l + 1e-8));
   f[7]  = (float)(macd / (cl + 1e-10));
   f[8]  = (float)(b.macd_sig / (cl + 1e-10));
   f[9]  = (float)((macd - b.macd_sig) / (cl + 1e-10));
   f[10] = (float)(b.atr14 / (cl + 1e-10));
   f[11] = (float)MathSin(2 * M_PI * utc_h / 24.0);
   f[12] = (float)MathCos(2 * M_PI * utc_h / 24.0);
   f[13] = (float)MathSin(2 * M_PI * utc_d / 7.0);
   f[14] = (float)MathCos(2 * M_PI * utc_d / 7.0);
   f[15] = (float)(rsi_val / 100.0);
}

//+------------------------------------------------------------------+
void Predict() {
   float f_gold[16], f_usdx[16], f_usdjpy[16];

   // Build sequence: oldest bar → index 0, newest bar → index 119
   for(int i = 0; i < 120; i++) {
      int h = 119 - i;

      ExtractFeatures(0, h, f_gold);
      ExtractFeatures(1, h, f_usdx);
      ExtractFeatures(2, h, f_usdjpy);

      int base = i * 48;
      for(int k = 0; k < 16; k++) {
         float raw;
         // Safety: ensure iqr > 0 to avoid division by zero
         float iqr_g = (iqrs[k] > 1e-6f ? iqrs[k] : 1.0f);
         float iqr_x = (iqrs[16+k] > 1e-6f ? iqrs[16+k] : 1.0f);
         float iqr_j = (iqrs[32+k] > 1e-6f ? iqrs[32+k] : 1.0f);

         raw = (f_gold[k]   - medians[k])    / iqr_g;
         input_data[base + k]      = MathMax(-10.0f, MathMin(10.0f, raw));
         
         raw = (f_usdx[k]   - medians[16+k]) / iqr_x;
         input_data[base + 16 + k] = MathMax(-10.0f, MathMin(10.0f, raw));
         
         raw = (f_usdjpy[k] - medians[32+k]) / iqr_j;
         input_data[base + 32 + k] = MathMax(-10.0f, MathMin(10.0f, raw));
      }
   }

   if(OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      // Apply Softmax to output_data
      float max_val = MathMax(output_data[0], MathMax(output_data[1], output_data[2]));
      float sum_exp = 0.0f;
      for(int i = 0; i < 3; i++) {
         output_data[i] = (float)MathExp(output_data[i] - max_val);
         sum_exp += output_data[i];
      }
      for(int i = 0; i < 3; i++) {
         output_data[i] /= sum_exp;
      }

      int sig = ArrayMaximum(output_data);
      if(sig > 0 && output_data[sig] > (float)CONFIDENCE) Execute(sig);
   }
}

//+------------------------------------------------------------------+
double GetMaxLotSize(ENUM_ORDER_TYPE order_type, double price) {
   if(LOT_SIZE > 0.0) return LOT_SIZE; // User specified fixed lot size
   
   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double margin_for_one_lot = 0.0;
   
   if(!OrderCalcMargin(order_type, _Symbol, 1.0, price, margin_for_one_lot) || margin_for_one_lot <= 0.0) {
      Print("[ERROR] OrderCalcMargin failed. Fallback to MIN volume.");
      return SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   }
   
   // Use 95% of free margin to leave a safety buffer for spread/commission/execution slip
   double max_lots = (free_margin * 0.95) / margin_for_one_lot;
   
   double min_vol  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_vol  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step_vol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   
   double final_lots = MathFloor(max_lots / step_vol) * step_vol;
   
   if(final_lots < min_vol) final_lots = min_vol;
   if(final_lots > max_vol) final_lots = max_vol;
   
   return final_lots;
}

//+------------------------------------------------------------------+
void Execute(int sig) {
   bool has_position = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER) {
         has_position = true;
         break;
      }
   }
   if(has_position) return;

   double atr  = history[0][0].atr14;
   double p    = (sig == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                            : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl   = (sig == 1) ? (p - atr * SL_MULTIPLIER) : (p + atr * SL_MULTIPLIER);
   double tp   = (sig == 1) ? (p + atr * TP_MULTIPLIER) : (p - atr * TP_MULTIPLIER);

   double min_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL)
                   * SymbolInfoDouble (_Symbol, SYMBOL_POINT);

   if(MathAbs(p - sl) < min_dist || MathAbs(tp - p) < min_dist) {
      Print("[WARN] Stop/TP too close to price, skipping trade.");
      return;
   }

   ENUM_ORDER_TYPE order = (sig == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double calc_lot = GetMaxLotSize(order, p);

   trade.PositionOpen(_Symbol, order, calc_lot, p, sl, tp,
                      (sig == 1 ? "GOLD BUY" : "GOLD SELL"));
}
```
