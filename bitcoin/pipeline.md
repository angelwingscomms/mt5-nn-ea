data.mq5
```cpp
#property script_show_inputs // Show settings window
input int ticks_to_export = 2160000; // Total ticks (~5 days of Bitcoin)

// Bitcoin Tick Data Exporter - Exports only Bitcoin prices with datetime

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
   LogInfo("BITCOIN TICK DATA EXPORTER - Starting execution");
   LogSeparator();
   LogInfo(StringFormat("Parameters: ticks_to_export=%d", ticks_to_export));
   LogInfo(StringFormat("Main symbol: %s", _Symbol));
   
   MqlTick ticks[]; // Array to hold tick data
   
   // === TICK DATA COPYING PHASE ===
   LogSeparator();
   LogInfo("Phase 1: Tick Data Acquisition");
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
   
    // === FILE CREATION PHASE ===
    LogSeparator();
    LogInfo("Phase 2: File Creation");
    LogInfo("  Creating output file: fast/bitcoin_ticks.csv");
    LogInfo("  (MQL5 sandbox restricts to MQL5\\Files, run move_ticks.py after export)");
    
    int h = FileOpen("fast/bitcoin_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) {
      LogError(StringFormat("  Failed to create file! Error code: %d", GetLastError()));
      LogError("  Script terminated - cannot write data");
      return;
   }
   LogSuccess("  File opened successfully");
   
   FileWrite(h, "time_msc,bid,ask"); // Write CSV header (Bitcoin only, no USDX/USDJPY)
   LogInfo("  CSV header written: time_msc,bid,ask");
   
   // === DATA PROCESSING PHASE ===
   LogSeparator();
   LogInfo("Phase 3: Data Processing & Export");
   LogInfo(StringFormat("  Processing %d ticks...", copied));
   
   int progress_interval = copied / 10; // Report progress every 10%
   if(progress_interval < 1000) progress_interval = 1000; // Minimum 1000 ticks between reports
   
   ulong process_start = GetTickCount64();
   
   for(int i = 0; i < copied; i++) {
      // Use StringFormat for efficient string building
      string row = StringFormat("%lld,%.2f,%.2f",
                                ticks[i].time_msc,
                                ticks[i].bid,
                                ticks[i].ask);
      FileWrite(h, row);
      
      // Progress reporting
      if(progress_interval > 0 && (i + 1) % progress_interval == 0) {
         int percent = (int)((double)(i + 1) / copied * 100);
         ulong elapsed = GetTickCount64() - process_start;
         int estimated_remaining = (int)((double)elapsed / (i + 1) * (copied - i - 1) / 1000);
         LogProgress("Export", i + 1, copied, 
                     StringFormat(" | Elapsed: %ds | ETA: %ds", 
                                  (int)(elapsed / 1000), estimated_remaining));
      }
   }
   
   ulong process_time = GetTickCount64() - process_start;
   
   // === FILE FINALIZATION PHASE ===
   LogSeparator();
   LogInfo("Phase 4: File Finalization");
   FileClose(h);
   LogSuccess("  File closed successfully");
   
   // Calculate file size estimate (approximate)
   long file_size_estimate = copied * 30L; // ~30 bytes per row estimate (Bitcoin only)
   LogInfo(StringFormat("  Estimated file size: ~%.2f MB", (double)file_size_estimate / 1024 / 1024));
   
   // === FINAL SUMMARY ===
   LogSeparator();
   LogInfo("EXECUTION SUMMARY");
   LogSeparator();
   
   ulong total_time = GetTickCount64() - start_time;
   
    LogSuccess(StringFormat("Exported %d ticks to fast/bitcoin_ticks.csv", copied));
    LogInfo("  Run 'python fast/move_ticks.py' to move file to project directory");
    LogInfo(StringFormat("  Main symbol (%s): %d ticks", _Symbol, copied));
   
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
# Change this if your file is named differently or in a different folder
INPUT_TICK_DATA = os.path.join(SCRIPT_DIR, 'bitcoin_ticks.csv')

parser = argparse.ArgumentParser(description='Train Bitcoin neural network model')
parser.add_argument('--tick-density', type=int, default=144, help='Ticks per bar')
args = parser.parse_args()

TICK_DENSITY = args.tick_density
OUTPUT_ONNX_MODEL = os.path.join(SCRIPT_DIR, f'bitcoin_{TICK_DENSITY}.onnx') 

if not os.path.exists(INPUT_TICK_DATA):
    print(f"Error: {INPUT_TICK_DATA} not found. Ensure you exported data from MT5 first.")
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
df.dropna(inplace=True)

# 3. FEATURE ENGINEERING (Bitcoin-specific - 33 features, no USDX/USDJPY)
print("Building 33 Features...")
# Returns & Spreads
df['f0'] = np.log(df['close'] / df['close'].shift(1))
df['f1'] = df['spread']
df['f2'] = df['duration'] / 1000.0 # Seconds
# Candle Shapes
df['f3'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
df['f4'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
df['f5'] = (df['high'] - df['low']) / df['close']
df['f6'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)
# Oscillators (MQL5 RSI match)
df['f7'] = ta.rsi(df['close'], length=9)
df['f8'] = ta.rsi(df['close'], length=18)
df['f9'] = ta.rsi(df['close'], length=27)
# ATR (Relative)
df['f10'] = ta.atr(df['high'], df['low'], df['close'], length=9) / df['close']
df['f11'] = ta.atr(df['high'], df['low'], df['close'], length=18) / df['close']
df['f12'] = ta.atr(df['high'], df['low'], df['close'], length=27) / df['close']
# MACD (Relative)
m = ta.macd(df['close'], 12, 26, 9)
df['f13'] = m.iloc[:, 0] / df['close'] # MACD Line
df['f14'] = m.iloc[:, 1] / df['close'] # Signal Line
df['f15'] = m.iloc[:, 2] / df['close'] # Histogram
# Moving Averages (Relative)
df['f16'] = (ta.ema(df['close'], 9) - df['close']) / df['close']
df['f17'] = (ta.ema(df['close'], 18) - df['close']) / df['close']
df['f18'] = (ta.ema(df['close'], 27) - df['close']) / df['close']
df['f19'] = (ta.ema(df['close'], 54) - df['close']) / df['close']
df['f20'] = (ta.ema(df['close'], 144) - df['close']) / df['close']
# CCI
df['f21'] = ta.cci(df['high'], df['low'], df['close'], 9)
df['f22'] = ta.cci(df['high'], df['low'], df['close'], 18)
df['f23'] = ta.cci(df['high'], df['low'], df['close'], 27)
# Williams %R
df['f24'] = ta.willr(df['high'], df['low'], df['close'], 9)
df['f25'] = ta.willr(df['high'], df['low'], df['close'], 18)
df['f26'] = ta.willr(df['high'], df['low'], df['close'], 27)
# Momentum (Relative)
df['f27'] = df['close'].diff(9) / df['close']
df['f28'] = df['close'].diff(18) / df['close']
df['f29'] = df['close'].diff(27) / df['close']
# Bollinger Band Width (f30, f31, f32 instead of f32, f33, f34)
for p, f_idx in zip([9, 18, 27], [30, 31, 32]):
    bb = ta.bbands(df['close'], length=p)
    df[f'f{f_idx}'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / df['close']

df.dropna(inplace=True)

# 4. TARGETING (Matching SL/TP Logic)
TP_MULTIPLIER, SL_MULTIPLIER, H = 2.7, 0.54, 30
def label(df, tp_mult, sl_mult, h):
    c, hi, lo = df.close.values, df.high.values, df.low.values
    # Note: Using ATR18 for labeling to match execution
    atr = ta.atr(df.high, df.low, df.close, length=18).values
    t = np.zeros(len(df), dtype=int)
    for i in range(len(df)-h):
        if np.isnan(atr[i]): continue
        up, lw = c[i]+(tp_mult*atr[i]), c[i]-(sl_mult*atr[i])
        for j in range(i+1, i+h+1):
            if hi[j] >= up: t[i] = 1; break # Buy
            if lo[j] <= lw: t[i] = 2; break # Sell
    return t

df['target'] = label(df, TP_MULTIPLIER, SL_MULTIPLIER, H)
features =[f'f{i}' for i in range(33)] # Bitcoin has 33 features
X, y = df[features].values, df.target.values

# 5. SPLIT & SCALE
train_end = int(len(X) * 0.70)
X_train = X[:train_end]
median = np.median(X_train, axis=0)
iqr = np.percentile(X_train, 75, axis=0) - np.percentile(X_train, 25, axis=0)

def win(X, y):
    xs, ys = [],[]
    for i in range(len(X) - 120):
        xs.append(X[i:i+120])
        ys.append(y[i+119])
    return np.array(xs), np.array(ys)

X_s = (X - median) / (iqr + 1e-8)
X_seq, y_seq = win(X_s, y)

# --- UPDATE SECTION 6: MODEL ---
# New Input: 3960 flat numbers (120 bars * 33 features)
in_lay = tf.keras.Input(shape=(3960,), name="input") 

# Internally reshape to what LSTM needs: (Batch=1, Timesteps=120, Features=33)
rs = tf.keras.layers.Reshape((120, 33))(in_lay)

ls = tf.keras.layers.LSTM(64, return_sequences=True, activation='mish')(rs)
at = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=64)(ls, ls)
pl = tf.keras.layers.GlobalAveragePooling1D()(at)
ou = tf.keras.layers.Dense(3, activation='softmax')(pl)
model = tf.keras.Model(in_lay, ou)
model.compile(optimizer='adamw', loss='sparse_categorical_crossentropy')

# Flatten the training data to match the new input shape
X_seq_flat = X_seq.reshape(-1, 3960)

print("Training...")
model.fit(X_seq_flat, y_seq, epochs=54, batch_size=64)

# 7. EXPORT TO ONNX (FLAT SHAPE)
print("Exporting model to ONNX...")
# Input is now just a flat vector of 3960
spec = (tf.TensorSpec((None, 3960), tf.float32, name="input"),) 
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)

with open(OUTPUT_ONNX_MODEL, "wb") as f:
    f.write(model_proto.SerializeToString())

print("\n--- PASTE THESE INTO live.mq5 ---")
print(f"float medians[33] = {{{', '.join([f'{m:.8f}f' for m in median])}}};")
print(f"float iqrs[33]    = {{{', '.join([f'{s:.8f}f' for s in iqr])}}};")
```

live.mq5
```cpp
//+------------------------------------------------------------------+
//|                                              Live_Bitcoin.mq5     |
//|                                  Copyright 2026, Bitcoin Algo     |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

// 1. RESOURCE & INPUTS
#resource "\\Experts\\nn\\bitcoin\\bitcoin_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      
input double TP_MULTIPLIER = 2.7;      
input double SL_MULTIPLIER = 0.54;     
input int    MAGIC_NUMBER  = 144144;   

// --- SCALING PARAMETERS ---
float medians[33] = {0.00000000f, 27.00000000f, 87.84800000f, 0.00023141f, 0.00023753f, 0.00111235f, 0.50282486f, 50.13602989f, 49.94441432f, 49.98808796f, 0.00118962f, 0.00119550f, 0.00120811f, 0.00000008f, -0.00000390f, 0.00000120f, 0.00000691f, -0.00001362f, -0.00001406f, -0.00000063f, -0.00009099f, -39707.45091325f, -3792.52098882f, 11195.23451692f, -50.34965035f, -50.51903114f, -50.12285012f, -0.00002158f, 0.00000000f, -0.00002834f, 0.00332237f, 0.00459211f, 0.00563987f};
float iqrs[33]    = {0.00098212f, 0.14583333f, 47.63700000f, 0.00034076f, 0.00035548f, 0.00069236f, 0.56733877f, 20.22841795f, 13.83736542f, 11.20782633f, 0.00041950f, 0.00039227f, 0.00037959f, 0.00116635f, 0.00035128f, 0.00110528f, 0.00129523f, 0.00194593f, 0.00244929f, 0.00356923f, 0.00599302f, 92187.79394857f, 55475.79980033f, 44018.00685251f, 53.81116849f, 53.12096968f, 52.74723642f, 0.00303838f, 0.00435999f, 0.00543748f, 0.00247653f, 0.00321723f, 0.00389436f};

// --- GLOBAL HANDLES ---
int hRSI9, hRSI18, hRSI27, hATR9, hATR18, hATR27, hMACD, hEMA9, hEMA18, hEMA27, hEMA54, hEMA144, hCCI9, hCCI18, hCCI27, hWPR9, hWPR18, hWPR27, hBB9, hBB18, hBB27;
long onnx_handle = INVALID_HANDLE;
CTrade trade;

// --- ONNX DATA BUFFERS ---
float input_data[3960]; // 1 * 120 * 33 = 3960 (Bitcoin has 33 features, not 35)
float output_data[3];   // Softmax: [Neutral, Buy, Sell]

// --- TICK BAR STORAGE ---
struct Bar {
   double o, h, l, c, spread;
   long time_start;
};
Bar history[150]; // History buffer for returns and momentum
int ticks_in_bar = 0;
Bar current_bar;

//+------------------------------------------------------------------+
//| Initialization                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("❌ ONNX Handle Error: ", GetLastError());
      return(INIT_FAILED);
   }

   // --- SET FLAT SHAPES (1, 3960) ---
   const long in_shape[] = {1, 3960};
   const long out_shape[] = {1, 3};
   
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape) && GetLastError() != 5805) return(INIT_FAILED);
   if(!OnnxSetOutputShape(onnx_handle, 0, out_shape) && GetLastError() != 5805) return(INIT_FAILED);

   // --- INITIALIZE INDICATORS ---
   hRSI9 = iRSI(_Symbol, PERIOD_CURRENT, 9, PRICE_CLOSE);
   hRSI18 = iRSI(_Symbol, PERIOD_CURRENT, 18, PRICE_CLOSE);
   hRSI27 = iRSI(_Symbol, PERIOD_CURRENT, 27, PRICE_CLOSE);
   hATR9 = iATR(_Symbol, PERIOD_CURRENT, 9);
   hATR18 = iATR(_Symbol, PERIOD_CURRENT, 18);
   hATR27 = iATR(_Symbol, PERIOD_CURRENT, 27);
   hMACD = iMACD(_Symbol, PERIOD_CURRENT, 12, 26, 9, PRICE_CLOSE);
   hEMA9 = iMA(_Symbol, PERIOD_CURRENT, 9, 0, MODE_EMA, PRICE_CLOSE);
   hEMA18 = iMA(_Symbol, PERIOD_CURRENT, 18, 0, MODE_EMA, PRICE_CLOSE);
   hEMA27 = iMA(_Symbol, PERIOD_CURRENT, 27, 0, MODE_EMA, PRICE_CLOSE);
   hEMA54 = iMA(_Symbol, PERIOD_CURRENT, 54, 0, MODE_EMA, PRICE_CLOSE);
   hEMA144 = iMA(_Symbol, PERIOD_CURRENT, 144, 0, MODE_EMA, PRICE_CLOSE);
   hCCI9 = iCCI(_Symbol, PERIOD_CURRENT, 9, PRICE_TYPICAL);
   hCCI18 = iCCI(_Symbol, PERIOD_CURRENT, 18, PRICE_TYPICAL);
   hCCI27 = iCCI(_Symbol, PERIOD_CURRENT, 27, PRICE_TYPICAL);
   hWPR9 = iWPR(_Symbol, PERIOD_CURRENT, 9);
   hWPR18 = iWPR(_Symbol, PERIOD_CURRENT, 18);
   hWPR27 = iWPR(_Symbol, PERIOD_CURRENT, 27);
   hBB9 = iBands(_Symbol, PERIOD_CURRENT, 9, 0, 2.0, PRICE_CLOSE);
   hBB18 = iBands(_Symbol, PERIOD_CURRENT, 18, 0, 2.0, PRICE_CLOSE);
   hBB27 = iBands(_Symbol, PERIOD_CURRENT, 27, 0, 2.0, PRICE_CLOSE);

   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   Print("✅ Bitcoin Online. Flat-Tensor Model Loaded.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Tick Processing                                                  |
//+------------------------------------------------------------------+
void OnTick() {
   MqlTick t; if(!SymbolInfoTick(_Symbol, t)) return;
   
   if(ticks_in_bar == 0) {
      current_bar.o = t.bid; current_bar.h = t.bid; current_bar.l = t.bid;
      current_bar.spread = 0; current_bar.time_start = t.time_msc;
   }
   
   current_bar.h = MathMax(current_bar.h, t.bid);
   current_bar.l = MathMin(current_bar.l, t.bid);
   current_bar.c = t.bid;
   current_bar.spread += (t.ask - t.bid);
   ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      current_bar.spread /= (double)TICK_DENSITY;
      
      // Shift and save history
      for(int i=149; i>0; i--) history[i] = history[i-1];
      history[0] = current_bar;
      
      ticks_in_bar = 0;
      static int bar_count = 0; bar_count++;
      if(bar_count >= 120) Predict();
   }
}

//+------------------------------------------------------------------+
//| Inference Logic                                                  |
//+------------------------------------------------------------------+
void Predict() {
   double r9[120], r18[120], r27[120], a9[120], a18[120], a27[120], mm[120], ms[120];
   double e9[120], e18[120], e27[120], e54[120], e144[120], c9[120], c18[120], c27[120];
   double w9[120], w18[120], w27[120], b9u[120], b9l[120], b18u[120], b18l[120], b27u[120], b27l[120];

   // Copy indicators (0=newest, 119=oldest)
   if(CopyBuffer(hRSI9,0,0,120,r9) < 120) return;
   CopyBuffer(hRSI18,0,0,120,r18); CopyBuffer(hRSI27,0,0,120,r27);
   CopyBuffer(hATR9,0,0,120,a9); CopyBuffer(hATR18,0,0,120,a18); CopyBuffer(hATR27,0,0,120,a27);
   CopyBuffer(hMACD,0,0,120,mm); CopyBuffer(hMACD,1,0,120,ms);
   CopyBuffer(hEMA9,0,0,120,e9); CopyBuffer(hEMA18,0,0,120,e18); CopyBuffer(hEMA27,0,0,120,e27);
   CopyBuffer(hEMA54,0,0,120,e54); CopyBuffer(hEMA144,0,0,120,e144);
   CopyBuffer(hCCI9,0,0,120,c9); CopyBuffer(hCCI18,0,0,120,c18); CopyBuffer(hCCI27,0,0,120,c27);
   CopyBuffer(hWPR9,0,0,120,w9); CopyBuffer(hWPR18,0,0,120,w18); CopyBuffer(hWPR27,0,0,120,w27);
   CopyBuffer(hBB9,1,0,120,b9u); CopyBuffer(hBB9,2,0,120,b9l);
   CopyBuffer(hBB18,1,0,120,b18u); CopyBuffer(hBB18,2,0,120,b18l);
   CopyBuffer(hBB27,1,0,120,b27u); CopyBuffer(hBB27,2,0,120,b27l);

   // Populate the flat 3960 array (33 features * 120 bars)
   for(int i=0; i<120; i++) {
      int h_idx = 119 - i; // Older bars first [119 ... 0]
      int buf_idx = 119 - i; // Index in copied indicator buffers corresponding to h_idx
      
      float f[33]; // Bitcoin has 33 features (no USDX/USDJPY)
      double close = history[h_idx].c;
      
      f[0] = (float)MathLog(close / (history[h_idx+1].c + 1e-8));
      f[1] = (float)history[h_idx].spread;
      f[2] = (float)((double)(history[h_idx].time_start - history[h_idx+1].time_start) / 1000.0);
      f[3] = (float)((history[h_idx].h - MathMax(history[h_idx].o, close)) / close);
      f[4] = (float)((MathMin(history[h_idx].o, close) - history[h_idx].l) / close);
      f[5] = (float)((history[h_idx].h - history[h_idx].l) / close);
      f[6] = (float)((close - history[h_idx].l) / (history[h_idx].h - history[h_idx].l + 1e-8));
      f[7] = (float)r9[buf_idx]; f[8] = (float)r18[buf_idx]; f[9] = (float)r27[buf_idx];
      f[10] = (float)(a9[buf_idx] / close); f[11] = (float)(a18[buf_idx] / close); f[12] = (float)(a27[buf_idx] / close);
      f[13] = (float)(mm[buf_idx] / close); f[14] = (float)(ms[buf_idx] / close); f[15] = (float)((mm[buf_idx] - ms[buf_idx]) / close);
      f[16] = (float)((e9[buf_idx] - close) / close); f[17] = (float)((e18[buf_idx] - close) / close); f[18] = (float)((e27[buf_idx] - close) / close);
      f[19] = (float)((e54[buf_idx] - close) / close); f[20] = (float)((e144[buf_idx] - close) / close);
      f[21] = (float)c9[buf_idx]; f[22] = (float)c18[buf_idx]; f[23] = (float)c27[buf_idx];
      f[24] = (float)w9[buf_idx]; f[25] = (float)w18[buf_idx]; f[26] = (float)w27[buf_idx];
      f[27] = (float)((close - history[h_idx+9].c) / close);
      f[28] = (float)((close - history[h_idx+18].c) / close);
      f[29] = (float)((close - history[h_idx+27].c) / close);
      // f[30] and f[31] removed (no USDX/USDJPY for Bitcoin)
      f[30] = (float)((b9u[buf_idx] - b9l[buf_idx]) / close);
      f[31] = (float)((b18u[buf_idx] - b18l[buf_idx]) / close);
      f[32] = (float)((b27u[buf_idx] - b27l[buf_idx]) / close);

      for(int k=0; k<33; k++) {
         input_data[i * 33 + k] = (f[k] - medians[k]) / (iqrs[k] + 1e-8f);
      }
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      Print("❌ Inference Error: ", GetLastError());
      return;
   }
   
   int signal = ArrayMaximum(output_data);
   float prob = output_data[signal];

   if(signal == 1 && prob > 0.55 && !HasOpenPosition()) ExecuteTrade(ORDER_TYPE_BUY);
   if(signal == 2 && prob > 0.55 && !HasOpenPosition()) ExecuteTrade(ORDER_TYPE_SELL);
}

//+------------------------------------------------------------------+
//| Order Execution                                                  |
//+------------------------------------------------------------------+
void ExecuteTrade(ENUM_ORDER_TYPE type) {
   double atr_buf[1]; 
   if(CopyBuffer(hATR18, 0, 0, 1, atr_buf) < 1) return;
   
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl_dist = SL_MULTIPLIER * atr_buf[0];
   double tp_dist = TP_MULTIPLIER * atr_buf[0];
   
   double sl = (type == ORDER_TYPE_BUY) ? (price - sl_dist) : (price + sl_dist);
   double tp = (type == ORDER_TYPE_BUY) ? (price + tp_dist) : (price - tp_dist);
   
   trade.PositionOpen(_Symbol, type, 0.1, price, sl, tp);
}

bool HasOpenPosition() {
   for(int i=PositionsTotal()-1; i>=0; i--)
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER) return true;
   return false;
}

void OnDeinit(const int reason) {
   if(onnx_handle != INVALID_HANDLE) OnnxRelease(onnx_handle);
   IndicatorRelease(hRSI9); IndicatorRelease(hRSI18); IndicatorRelease(hRSI27);
   IndicatorRelease(hATR9); IndicatorRelease(hATR18); IndicatorRelease(hATR27);
   IndicatorRelease(hMACD); IndicatorRelease(hEMA9); IndicatorRelease(hEMA18);
   IndicatorRelease(hEMA27); IndicatorRelease(hEMA54); IndicatorRelease(hEMA144);
   IndicatorRelease(hCCI9); IndicatorRelease(hCCI18); IndicatorRelease(hCCI27);
   IndicatorRelease(hWPR9); IndicatorRelease(hWPR18); IndicatorRelease(hWPR27);
   IndicatorRelease(hBB9); IndicatorRelease(hBB18); IndicatorRelease(hBB27);
}
```
