data.mq5
```cpp
#property script_show_inputs // Show settings window
input int ticks_to_export = 2160000; // Total ticks (~5 days of Gold)
input string USDX_Symbol = "$USDX"; // Name of USD Index
input string USDJPY_Symbol = "USDJPY"; // Name of USDJPY

// FLAW 4.4 FIX: Optimized tick data exporting with StringFormat and Two-Pointer Merge

//+------------------------------------------------------------------+
//| Logging helper functions                                          |
//+------------------------------------------------------------------+
void LogInfo(string message) {
   Print("[INFO] ", message);
}

void LogSuccess(string message) {
   Print("✅ [SUCCESS] ", message);
}

void LogWarning(string message) {
   Print("⚠️ [WARNING] ", message);
}

void LogError(string message) {
   Print("❌ [ERROR] ", message);
}

void LogProgress(string stage, int current, int total, string extra = "") {
   int percent = (int)((double)current / total * 100);
   Print("📊 [PROGRESS] ", stage, ": ", current, "/", total, " (", percent, "%)", extra);
}

void LogSeparator() {
   Print("═══════════════════════════════════════════════════════════════");
}

//+------------------------------------------------------------------+
//| Main script function                                              |
//+------------------------------------------------------------------+
void OnStart() {
   ulong start_time = GetTickCount64(); // Script start timestamp
   LogSeparator();
   LogInfo("ACHILLES TICK DATA EXPORTER - Starting execution");
   LogSeparator();
   LogInfo(StringFormat("Parameters: ticks_to_export=%d, USDX='%s', USDJPY='%s'", 
                        ticks_to_export, USDX_Symbol, USDJPY_Symbol));
   LogInfo(StringFormat("Main symbol: %s", _Symbol));
   
   MqlTick ticks[], usdx_ticks[], usdjpy_ticks[]; // Arrays to hold tick data
   
   // === SYMBOL SELECTION PHASE ===
   LogInfo("Phase 1: Symbol Selection");
   LogInfo(StringFormat("  Attempting to select USDX symbol: '%s'", USDX_Symbol));
   bool usdx_available = SymbolSelect(USDX_Symbol, true);
   if(usdx_available) {
      LogSuccess(StringFormat("  USDX symbol '%s' selected successfully", USDX_Symbol));
   } else {
      LogWarning(StringFormat("  USDX symbol '%s' NOT available - will use placeholder (0.0)", USDX_Symbol));
   }
   
   LogInfo(StringFormat("  Attempting to select USDJPY symbol: '%s'", USDJPY_Symbol));
   bool usdjpy_available = SymbolSelect(USDJPY_Symbol, true);
   if(usdjpy_available) {
      LogSuccess(StringFormat("  USDJPY symbol '%s' selected successfully", USDJPY_Symbol));
   } else {
      LogWarning(StringFormat("  USDJPY symbol '%s' NOT available - will use placeholder (0.0)", USDJPY_Symbol));
   }
   
   // === TICK DATA COPYING PHASE ===
   LogSeparator();
   LogInfo("Phase 2: Tick Data Acquisition");
   LogInfo(StringFormat("  Copying %d ticks for main symbol '%s'...", ticks_to_export, _Symbol));
   
   ulong copy_start = GetTickCount64();
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, ticks_to_export);
   ulong copy_time = GetTickCount64() - copy_start;
   
   if(copied <= 0) {
      LogError(StringFormat("  Failed to copy ticks for '%s'! Error code: %d", _Symbol, GetLastError()));
      LogError("  Script terminated - no data to export");
      return;
   }
   LogSuccess(StringFormat("  Copied %d ticks for '%s' in %llu ms", copied, _Symbol, copy_time));
   
   // Log tick data time range
   if(copied > 0) {
      datetime first_time = (datetime)(ticks[0].time_msc / 1000);
      datetime last_time = (datetime)(ticks[copied-1].time_msc / 1000);
      LogInfo(StringFormat("  Tick time range: %s to %s", 
                           TimeToString(first_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                           TimeToString(last_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS)));
   }
   
   // Get tick data for auxiliary symbols if available
   int usdx_copied = 0, usdjpy_copied = 0;
   
   if(usdx_available) {
      LogInfo(StringFormat("  Copying %d ticks for USDX '%s'...", ticks_to_export, USDX_Symbol));
      copy_start = GetTickCount64();
      usdx_copied = CopyTicks(USDX_Symbol, usdx_ticks, COPY_TICKS_ALL, 0, ticks_to_export);
      copy_time = GetTickCount64() - copy_start;
      
      if(usdx_copied <= 0) {
         LogWarning(StringFormat("  USDX ticks not available (error: %d), using placeholder", GetLastError()));
         usdx_available = false;
      } else {
         LogSuccess(StringFormat("  Copied %d USDX ticks in %llu ms", usdx_copied, copy_time));
      }
   }
   
   if(usdjpy_available) {
      LogInfo(StringFormat("  Copying %d ticks for USDJPY '%s'...", ticks_to_export, USDJPY_Symbol));
      copy_start = GetTickCount64();
      usdjpy_copied = CopyTicks(USDJPY_Symbol, usdjpy_ticks, COPY_TICKS_ALL, 0, ticks_to_export);
      copy_time = GetTickCount64() - copy_start;
      
      if(usdjpy_copied <= 0) {
         LogWarning(StringFormat("  USDJPY ticks not available (error: %d), using placeholder", GetLastError()));
         usdjpy_available = false;
      } else {
         LogSuccess(StringFormat("  Copied %d USDJPY ticks in %llu ms", usdjpy_copied, copy_time));
      }
   }
   
    // === FILE CREATION PHASE ===
    LogSeparator();
    LogInfo("Phase 3: File Creation");
    LogInfo("  Creating output file: fast/achilles_ticks.csv");
    LogInfo("  (MQL5 sandbox restricts to MQL5\\Files, run move_ticks.py after export)");
    
    int h = FileOpen("fast/achilles_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) {
      LogError(StringFormat("  Failed to create file! Error code: %d", GetLastError()));
      LogError("  Script terminated - cannot write data");
      return;
   }
   LogSuccess("  File opened successfully");
   
   FileWrite(h, "time_msc,bid,ask,usdx,usdjpy"); // Write CSV header
   LogInfo("  CSV header written: time_msc,bid,ask,usdx,usdjpy");
   
   // === DATA PROCESSING PHASE ===
   LogSeparator();
   LogInfo("Phase 4: Data Processing & Export");
   LogInfo(StringFormat("  Processing %d ticks with Two-Pointer Merge algorithm...", copied));
   LogInfo("  Algorithm complexity: O(N) - linear time");
   
   // FLAW 4.4 FIX: Two-Pointer Merge algorithm for O(N) timestamp alignment
   int usdx_idx = 0, usdjpy_idx = 0; // Indices for auxiliary tick arrays
   double usdx_bid = 0.0, usdjpy_bid = 0.0; // Current matched prices
   
   int usdx_matches = 0, usdjpy_matches = 0; // Count of successful matches
   int progress_interval = copied / 10; // Report progress every 10%
   if(progress_interval < 1000) progress_interval = 1000; // Minimum 1000 ticks between reports
   
   ulong process_start = GetTickCount64();
   
   for(int i = 0; i < copied; i++) {
      ulong t = ticks[i].time_msc; // Current tick timestamp
      
      // FLAW 4.4 FIX: Two-Pointer Merge for USDX
      if(usdx_available && usdx_copied > 0) {
         int prev_idx = usdx_idx;
         while(usdx_idx < usdx_copied - 1 && usdx_ticks[usdx_idx + 1].time_msc <= t) {
            usdx_idx++;
         }
         if(usdx_idx != prev_idx) usdx_matches++;
         usdx_bid = usdx_ticks[usdx_idx].bid;
      }
      
      // FLAW 4.4 FIX: Two-Pointer Merge for USDJPY
      if(usdjpy_available && usdjpy_copied > 0) {
         int prev_idx = usdjpy_idx;
         while(usdjpy_idx < usdjpy_copied - 1 && usdjpy_ticks[usdjpy_idx + 1].time_msc <= t) {
            usdjpy_idx++;
         }
         if(usdjpy_idx != prev_idx) usdjpy_matches++;
         usdjpy_bid = usdjpy_ticks[usdjpy_idx].bid;
      }
      
      // Use StringFormat for efficient string building
      string row = StringFormat("%lld,%.5f,%.5f,%.5f,%.5f",
                                ticks[i].time_msc,
                                ticks[i].bid,
                                ticks[i].ask,
                                usdx_bid,
                                usdjpy_bid);
      FileWrite(h, row);
      
      // Progress reporting
      if(progress_interval > 0 && (i + 1) % progress_interval == 0) {
         int percent = (int)((double)(i + 1) / copied * 100);
         ulong elapsed = GetTickCount64() - process_start;
         int estimated_total = (int)((double)elapsed / (i + 1) * copied / 1000);
         int estimated_remaining = (int)((double)elapsed / (i + 1) * (copied - i - 1) / 1000);
         LogProgress("Export", i + 1, copied, 
                     StringFormat(" | Elapsed: %ds | ETA: %ds", 
                                  (int)(elapsed / 1000), estimated_remaining));
      }
   }
   
   ulong process_time = GetTickCount64() - process_start;
   
   // === FILE FINALIZATION PHASE ===
   LogSeparator();
   LogInfo("Phase 5: File Finalization");
   FileClose(h);
   LogSuccess("  File closed successfully");
   
   // Calculate file size estimate (approximate)
   long file_size_estimate = copied * 60L; // ~60 bytes per row estimate
   LogInfo(StringFormat("  Estimated file size: ~%.2f MB", (double)file_size_estimate / 1024 / 1024));
   
   // === FINAL SUMMARY ===
   LogSeparator();
   LogInfo("EXECUTION SUMMARY");
   LogSeparator();
   
   ulong total_time = GetTickCount64() - start_time;
   
    LogSuccess(StringFormat("Exported %d ticks to fast/achilles_ticks.csv", copied));
    LogInfo("  Run 'python fast/move_ticks.py' to move file to project directory");
    LogInfo(StringFormat("  Main symbol (%s): %d ticks", _Symbol, copied));
   
   if(usdx_available) {
      LogInfo(StringFormat("  USDX (%s): %d ticks loaded, %d timestamp matches", 
                           USDX_Symbol, usdx_copied, usdx_matches));
   } else {
      LogInfo("  USDX: Not available (used placeholder 0.0)");
   }
   
   if(usdjpy_available) {
      LogInfo(StringFormat("  USDJPY (%s): %d ticks loaded, %d timestamp matches", 
                           USDJPY_Symbol, usdjpy_copied, usdjpy_matches));
   } else {
      LogInfo("  USDJPY: Not available (used placeholder 0.0)");
   }
   
   LogInfo(StringFormat("Processing time: %llu ms (%.2f seconds)", process_time, (double)process_time / 1000));
   LogInfo(StringFormat("Throughput: %.0f ticks/second", (double)copied / (process_time / 1000.0)));
   LogInfo(StringFormat("Total script execution time: %llu ms (%.2f seconds)", total_time, (double)total_time / 1000));
   
   LogSeparator();
   LogSuccess("SCRIPT COMPLETED SUCCESSFULLY");
   LogSeparator();
}
```

nn.py
```python
import pandas as pd
import numpy as np
import pandas_ta as ta
import tensorflow as tf
import tf2onnx
import os
import argparse

# 1. SETUP & PATHS
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TICK_DATA = os.path.join(SCRIPT_DIR, 'achilles_ticks.csv')

parser = argparse.ArgumentParser(description='Train Achilles neural network model')
parser.add_argument('--tick-density', type=int, default=144, help='Ticks per bar')
args = parser.parse_args()

TICK_DENSITY = args.tick_density
OUTPUT_ONNX_MODEL = os.path.join(SCRIPT_DIR, f'achilles_{TICK_DENSITY}.onnx') 

if not os.path.exists(INPUT_TICK_DATA):
    print(f"Error: {INPUT_TICK_DATA} not found.")
    exit()

print("Loading data...")
df_t = pd.read_csv(INPUT_TICK_DATA)

# 2. TICK-BAR CONSTRUCTION
print("Constructing Tick Bars...")
df_t['bar_id'] = np.arange(len(df_t)) // TICK_DENSITY
df_t['spread_tick'] = df_t['ask'] - df_t['bid']

agg_dict = {
    'bid':['first', 'max', 'min', 'last'],
    'time_msc': ['first', 'last'],
    'spread_tick': 'mean'
}

if 'usdx' in df_t.columns: agg_dict['usdx'] = 'last'
if 'usdjpy' in df_t.columns: agg_dict['usdjpy'] = 'last'

df_agg = df_t.groupby('bar_id').agg(agg_dict)
df = pd.DataFrame({
    'open': df_agg[('bid', 'first')].values,
    'high': df_agg[('bid', 'max')].values,
    'low': df_agg[('bid', 'min')].values,
    'close': df_agg[('bid', 'last')].values,
    'spread': df_agg[('spread_tick', 'mean')].values,
    'time_open': df_agg[('time_msc', 'first')].values,
    'time_close': df_agg[('time_msc', 'last')].values
})

df['duration'] = df['time_close'] - df['time_open']
df['usdx'] = df_agg[('usdx', 'last')].values if 'usdx' in df_t.columns else df['close']
df['usdjpy'] = df_agg[('usdjpy', 'last')].values if 'usdjpy' in df_t.columns else df['close']
df.dropna(inplace=True)

# 3. FEATURE ENGINEERING
print("Building 35 Features...")
df['f0'] = np.log(df['close'] / df['close'].shift(1))
df['f1'] = df['spread']
df['f2'] = df['duration']
df['f3'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
df['f4'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
df['f5'] = (df['high'] - df['low']) / df['close']
df['f6'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
df['f7'] = ta.rsi(df['close'], length=9)
df['f8'] = ta.rsi(df['close'], length=18)
df['f9'] = ta.rsi(df['close'], length=27)
df['f10'] = ta.atr(df['high'], df['low'], df['close'], length=9) / df['close']
df['f11'] = ta.atr(df['high'], df['low'], df['close'], length=18) / df['close']
df['f12'] = ta.atr(df['high'], df['low'], df['close'], length=27) / df['close']
df['atr18'] = ta.atr(df['high'], df['low'], df['close'], length=18)
m = ta.macd(df['close'], 9, 18, 9)
df['f13'], df['f14'], df['f15'] = m.iloc[:,0] / df['close'], m.iloc[:,2] / df['close'], m.iloc[:,1] / df['close']
df['f16'] = (ta.ema(df['close'], 9) - df['close']) / df['close']
df['f17'] = (ta.ema(df['close'], 18) - df['close']) / df['close']
df['f18'] = (ta.ema(df['close'], 27) - df['close']) / df['close']
df['f19'] = (ta.ema(df['close'], 54) - df['close']) / df['close']
df['f20'] = (ta.ema(df['close'], 144) - df['close']) / df['close']
df['f21'] = ta.cci(df['high'], df['low'], df['close'], 9)
df['f22'] = ta.cci(df['high'], df['low'], df['close'], 18)
df['f23'] = ta.cci(df['high'], df['low'], df['close'], 27)
df['f24'] = ta.willr(df['high'], df['low'], df['close'], 9)
df['f25'] = ta.willr(df['high'], df['low'], df['close'], 18)
df['f26'] = ta.willr(df['high'], df['low'], df['close'], 27)
df['f27'] = ta.mom(df['close'], 9) / df['close']
df['f28'] = ta.mom(df['close'], 18) / df['close']
df['f29'] = ta.mom(df['close'], 27) / df['close']
df['f30'] = df['usdx'].pct_change()
df['f31'] = df['usdjpy'].pct_change()
for p, f_idx in zip([9, 18, 27], [32, 33, 34]):
    bb = ta.bbands(df['close'], length=p)
    df[f'f{f_idx}'] = (bb.iloc[:,2] - bb.iloc[:,0]) / (bb.iloc[:,1] + 1e-8)
df.dropna(inplace=True)

# 4. TARGETING
TP_MULTIPLIER, SL_MULTIPLIER, H = 2.7, 0.0, 30
def label(df, tp_mult, sl_mult, h):
    c, hi, lo, atr = df.close.values, df.high.values, df.low.values, df.atr18.values
    t = np.zeros(len(df), dtype=int)
    for i in range(len(df)-h):
        up, lw = c[i]+(tp_mult*atr[i]), c[i]-(sl_mult*atr[i])
        for j in range(i+1, i+h+1):
            if hi[j] >= up: t[i] = 1; break
            if lo[j] <= lw: t[i] = 2; break
    return t

df['target'] = label(df, TP_MULTIPLIER, SL_MULTIPLIER, H)
features =[f'f{i}' for i in range(35)]
X, y = df[features].values, df.target.values

# 5. SPLIT & SCALE
train_end = int(len(X) * 0.70)
X_train, y_train = X[:train_end], y[:train_end]
median, iqr = np.median(X_train, axis=0), np.percentile(X_train, 75, axis=0) - np.percentile(X_train, 25, axis=0)

def win(X, y):
    xs, ys = [],[]
    for i in range(len(X) - 120):
        xs.append(X[i:i+120]); ys.append(y[i+119])
    return np.array(xs), np.array(ys)

X_s = (X - median) / (iqr + 1e-8)
X_seq, y_seq = win(X_s, y)

# 6. MODEL
in_lay = tf.keras.Input(shape=(120, 35))
ls = tf.keras.layers.LSTM(35, return_sequences=True, activation='mish')(in_lay)
at = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=35)(ls, ls)
pl = tf.keras.layers.Lambda(lambda x: x[:, -1, :])(at)
ou = tf.keras.layers.Dense(3, activation='softmax')(pl)
model = tf.keras.Model(in_lay, ou)
model.compile(optimizer='adamw', loss='sparse_categorical_crossentropy')

print("Training...")
model.fit(X_seq, y_seq, epochs=1, batch_size=64)

# 7. EXPORT TO ONNX (FIX: FIXED BATCH SIZE 1)
print("Exporting model to ONNX...")
spec = (tf.TensorSpec((1, 120, 35), tf.float32, name="input"),) # Fixed shape [1, 120, 35]
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)

with open(OUTPUT_ONNX_MODEL, "wb") as f:
    f.write(model_proto.SerializeToString())

print(f"Medians: {','.join([f'{m:.6f}f' for m in median])}")
print(f"IQRs: {','.join([f'{s:.6f}f' for s in iqr])}")
```

live.mq5
```cpp
﻿//+------------------------------------------------------------------+
//|                                  Live_Achilles_TickBar.mq5       |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

// Resource: No fixed size, compiler calculates it
#resource "\\Files\\achilles_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      
input double TP_MULTIPLIER = 2.7;      
input double SL_MULTIPLIER = 0.54;     
input string USDX_Symbol   = "$USDX";  
input string USDJPY_Symbol = "USDJPY"; 
input int    MAGIC_NUMBER  = 144144;   

// Scaling params (to be updated by Python script)
float medians[35]={-0.000006f, 0.104931f, 30150.000000f, 0.000127f, 0.000132f, 0.000805f, 0.503401f, 49.824540f, 49.608665f, 49.568888f, 0.000869f, 0.000876f, 0.000880f, -0.000016f, -0.000016f, -0.000000f, 0.000017f, 0.000014f, 0.000043f, 0.000105f, 0.000096f, -126020.696511f, -83237.614809f, -65911.134177f, -49.711723f, -49.700000f, -48.691589f, -0.000023f, -0.000085f, -0.000105f, 0.000000f, 0.000000f, 0.002801f, 0.003922f, 0.004775f};
float iqrs[35]={0.000780f,0.022743f,5272.500000f,0.000250f,0.000255f,0.000658f,0.663998f,21.478885f,14.504269f,11.509027f,0.000528f,0.000507f,0.000490f,0.000749f,0.000683f,0.000274f,0.001109f,0.001674f,0.002106f,0.002950f,0.005309f,124022.833442f,75234.652891f,57520.732921f,59.110822f,57.496001f,56.672005f,0.002549f,0.003638f,0.004620f,0.000101f,0.000113f,0.002482f,0.003295f,0.004007f};

CTrade trade;
long onnx = INVALID_HANDLE;

// Multi-dimensional arrays matching ONNX [Batch][Window][Features]
float input_data[1][120][35]; 
float out_data[1][3];

// Ring Buffer implementation
#define RING_SIZE 512
#define RING_MASK 511  
double o_a[RING_SIZE], h_a[RING_SIZE], l_a[RING_SIZE], c_a[RING_SIZE], s_a[RING_SIZE], d_a[RING_SIZE], dx_a[RING_SIZE], jp_a[RING_SIZE];
int head_index = 0, ticks_in_bar = 0, bars = 0;
double b_open, b_high, b_low, b_spread;
long b_start_time; 

// Technical indicators states
double ema9_state, ema18_state, ema27_state, ema54_state, ema144_state, macd_signal_state;
double ema9_a[RING_SIZE], ema18_a[RING_SIZE], ema27_a[RING_SIZE], ema54_a[RING_SIZE], ema144_a[RING_SIZE];
double macd_a[RING_SIZE], macd_signal_a[RING_SIZE], macd_hist_a[RING_SIZE];
double cci9_a[RING_SIZE], cci18_a[RING_SIZE], cci27_a[RING_SIZE];
bool ema_initialized = false;

int OnInit() {
   if(!SymbolSelect(USDX_Symbol, true) || !SymbolSelect(USDJPY_Symbol, true)) return(INIT_FAILED);
   
   onnx = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx == INVALID_HANDLE) {
      Print("❌ ONNX Model Error: ", GetLastError());
      return(INIT_FAILED);
   }
   
   // Crucial: Set shapes explicitly
   const long in_shape[] = {1, 120, 35};
   const long out_shape[] = {1, 3};
   
   if(!OnnxSetInputShape(onnx, 0, in_shape) || !OnnxSetOutputShape(onnx, 0, out_shape)) {
      Print("❌ Shape Error: ", GetLastError());
      return(INIT_FAILED);
   }
   
   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   InitializeEMAs();
   return(INIT_SUCCEEDED);
}

void InitializeEMAs() {
   MqlTick ticks[];
   int count = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, 150000); 
   if(count < TICK_DENSITY * 270) return;
   
   // (Simplified bootstrap: just filling the buffer for calculation)
   int tick_idx = 0;
   while(tick_idx < count && bars < RING_SIZE) {
      double bh = ticks[tick_idx].bid, bl = ticks[tick_idx].bid, bs = 0;
      long bt = ticks[tick_idx].time_msc;
      int tb = 0;
      while(tick_idx < count && tb < TICK_DENSITY) {
         bh = MathMax(bh, ticks[tick_idx].bid);
         bl = MathMin(bl, ticks[tick_idx].bid);
         bs += (ticks[tick_idx].ask - ticks[tick_idx].bid);
         tb++; tick_idx++;
      }
      Shift(ticks[tick_idx-tb].bid, bh, bl, ticks[tick_idx-1].bid, bs/tb, (double)(ticks[tick_idx-1].time_msc - bt));
   }
   ema_initialized = true;
}

void OnTick() {
   MqlTick t; if(!SymbolInfoTick(_Symbol, t)) return;
   if(ticks_in_bar == 0) { b_open=t.bid; b_high=t.bid; b_low=t.bid; b_spread=0; b_start_time=t.time_msc; }
   b_high=MathMax(b_high, t.bid); b_low=MathMin(b_low, t.bid);
   b_spread += (t.ask-t.bid); ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      Shift(b_open, b_high, b_low, t.bid, b_spread/(double)TICK_DENSITY, (double)(t.time_msc - b_start_time));
      ticks_in_bar = 0;
      if(bars >= 270) Predict(); 
   }
}

void Shift(double o, double h, double l, double c, double s, double d) {
   int idx = head_index;
   o_a[idx]=o; h_a[idx]=h; l_a[idx]=l; c_a[idx]=c; s_a[idx]=s; d_a[idx]=d;
   dx_a[idx]=SymbolInfoDouble(USDX_Symbol, SYMBOL_BID);
   jp_a[idx]=SymbolInfoDouble(USDJPY_Symbol, SYMBOL_BID);
   
   // Update Technicals (Simplified EMA logic)
   double alpha9 = 2.0/10.0;
   ema9_state = bars==0 ? c : (c - ema9_state) * alpha9 + ema9_state;
   ema18_state = bars==0 ? c : (c - ema18_state) * (2.0/19.0) + ema18_state;
   ema27_state = bars==0 ? c : (c - ema27_state) * (2.0/28.0) + ema27_state;
   ema54_state = bars==0 ? c : (c - ema54_state) * (2.0/55.0) + ema54_state;
   ema144_state = bars==0 ? c : (c - ema144_state) * (2.0/145.0) + ema144_state;
   
   ema9_a[idx]=ema9_state; ema18_a[idx]=ema18_state; ema27_a[idx]=ema27_state; 
   ema54_a[idx]=ema54_state; ema144_a[idx]=ema144_state;
   
   double macd = ema9_state - ema18_state;
   macd_signal_state = bars==0 ? macd : (macd - macd_signal_state) * 0.2 + macd_signal_state;
   macd_a[idx]=macd; macd_signal_a[idx]=macd_signal_state; macd_hist_a[idx]=macd-macd_signal_state;
   
   cci9_a[idx]=CalcCCI(idx, 9); cci18_a[idx]=CalcCCI(idx, 18); cci27_a[idx]=CalcCCI(idx, 27);
   
   head_index = (head_index + 1) & RING_MASK;
   bars++;
}

int RingIdx(int logical) { return (head_index - 1 - logical) & RING_MASK; }

void Predict() {
   for(int i=0; i<120; i++) {
      int x = RingIdx(119-i);  
      int x1 = RingIdx(119-i+1);  
      
      float f[35];
      f[0]=(float)MathLog(c_a[x]/(c_a[x1]+1e-8)); f[1]=(float)s_a[x]; f[2]=(float)d_a[x];
      f[3]=(float)((h_a[x]-MathMax(o_a[x],c_a[x]))/c_a[x]);
      f[4]=(float)((MathMin(o_a[x],c_a[x])-l_a[x])/c_a[x]);
      f[5]=(float)((h_a[x]-l_a[x])/c_a[x]);
      f[6]=(float)((c_a[x]-l_a[x])/(h_a[x]-l_a[x]+1e-8));
      f[7]=CRSI(x,9); f[8]=CRSI(x,18); f[9]=CRSI(x,27);
      f[10]=CATR(x,9)/c_a[x]; f[11]=CATR(x,18)/c_a[x]; f[12]=CATR(x,27)/c_a[x];
      f[13]=macd_a[x]/c_a[x]; f[14]=macd_signal_a[x]/c_a[x]; f[15]=macd_hist_a[x]/c_a[x];
      f[16]=(ema9_a[x]-c_a[x])/c_a[x]; f[17]=(ema18_a[x]-c_a[x])/c_a[x]; f[18]=(ema27_a[x]-c_a[x])/c_a[x];
      f[19]=(ema54_a[x]-c_a[x])/c_a[x]; f[20]=(ema144_a[x]-c_a[x])/c_a[x];
      f[21]=cci9_a[x]; f[22]=cci18_a[x]; f[23]=cci27_a[x];
      f[24]=CWPR(x,9); f[25]=CWPR(x,18); f[26]=CWPR(x,27);
      f[27]=(c_a[x]-c_a[RingIdx(119-i+9)])/c_a[x];
      f[28]=(c_a[x]-c_a[RingIdx(119-i+18)])/c_a[x];
      f[29]=(c_a[x]-c_a[RingIdx(119-i+27)])/c_a[x];
      f[30]=(dx_a[x]-dx_a[x1])/(dx_a[x1]+1e-8); f[31]=(jp_a[x]-jp_a[x1])/(jp_a[x1]+1e-8);
      f[32]=CBBW(x,9); f[33]=CBBW(x,18); f[34]=CBBW(x,27);

      for(int k=0; k<35; k++) input_data[0][i][k] = (f[k]-medians[k])/(iqrs[k]+1e-8);
   }

   if(!OnnxRun(onnx, ONNX_DEFAULT, input_data, out_data)) return;
   
   if(out_data[0][0] > 0.5) return; 
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(out_data[0][1] > 0.55 && !HasOpenPosition()) Execute(ORDER_TYPE_BUY, ask);
   if(out_data[0][2] > 0.55 && !HasOpenPosition()) Execute(ORDER_TYPE_SELL, bid);
}

void Execute(ENUM_ORDER_TYPE type, double p) {
   double atr = CATR(RingIdx(0), 18);  
   double sl = (type==ORDER_TYPE_BUY) ? p-(SL_MULTIPLIER*atr) : p+(SL_MULTIPLIER*atr);
   double tp = (type==ORDER_TYPE_BUY) ? p+(TP_MULTIPLIER*atr) : p-(TP_MULTIPLIER*atr);
   trade.PositionOpen(_Symbol, type, 0.01, p, sl, tp);
}

bool HasOpenPosition() {
   for(int i=PositionsTotal()-1; i>=0; i--)
      if(PositionGetSymbol(i)==_Symbol && PositionGetInteger(POSITION_MAGIC)==MAGIC_NUMBER) return true;
   return false;
}

// Indicator helper stubs (Standard formulas)
float CRSI(int x, int p) { double u=0, d=0; for(int i=0; i<p; i++) { double df=c_a[(x+i)&RING_MASK]-c_a[(x+i+1)&RING_MASK]; if(df>0) u+=df; else d-=df; } return (d==0)?100:(float)(100-(100/(1+u/(d+1e-8)))); }
float CATR(int x, int p) { double s=0; for(int i=0; i<p; i++) s+=MathMax(h_a[(x+i)&RING_MASK]-l_a[(x+i)&RING_MASK], MathAbs(h_a[(x+i)&RING_MASK]-c_a[(x+i+1)&RING_MASK])); return (float)(s/p); }
float CWPR(int x, int p) { double h=h_a[x], l=l_a[x]; for(int i=1; i<p; i++) { h=MathMax(h,h_a[(x+i)&RING_MASK]); l=MathMin(l,l_a[(x+i)&RING_MASK]); } return (h==l)?0:(float)(-100*(h-c_a[x])/(h-l+1e-8)); }
float CBBW(int x, int p) { double s=0, sq=0; for(int i=0; i<p; i++) s+=c_a[(x+i)&RING_MASK]; double m=s/p; for(int i=0; i<p; i++) sq+=MathPow(c_a[(x+i)&RING_MASK]-m,2); return (float)((MathSqrt(sq/p)*4)/(m+1e-8)); }
float CalcCCI(int x, int p) { double tp_sum=0; for(int i=0; i<p; i++) tp_sum+=(h_a[(x+i)&RING_MASK]+l_a[(x+i)&RING_MASK]+c_a[(x+i)&RING_MASK])/3.0; double sma=tp_sum/p, md=0; for(int i=0; i<p; i++) md+=MathAbs(((h_a[(x+i)&RING_MASK]+l_a[(x+i)&RING_MASK]+c_a[(x+i)&RING_MASK])/3.0)-sma); return (md==0)?0:(float)((((h_a[x]+l_a[x]+c_a[x])/3.0)-sma)/(0.015*(md/p))); }

void OnDeinit(const int r) { if(onnx!=INVALID_HANDLE) OnnxRelease(onnx); }
```
