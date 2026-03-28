data.mq5
```cpp
#property script_show_inputs
input int ticks_to_export = 2160000; 

void OnStart() {
   long start_time = (long)GetTickCount64(); // Cast to long for signed arithmetic
   Print("[INFO] BITCOIN TICK DATA EXPORTER - Starting");

   MqlTick ticks[];
   // CopyTicks returns int, so we stay in signed integer space for the count
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, (uint)ticks_to_export);
   
   if(copied <= 0) {
      PrintFormat("❌ Error: CopyTicks failed. Code: %d", GetLastError());
      return;
   }

   int h = FileOpen("achilles_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) return;

   FileWrite(h, "time_msc", "bid", "ask");

   // Define progress intervals as int to match the loop index 'i'
   int progress_interval = (copied > 10) ? (copied / 10) : 1000;
   long process_start = (long)GetTickCount64();

   for(int i = 0; i < copied; i++) {
      // 1. Data Integrity Check
      if(ticks[i].bid <= 0.0) continue;

      // 2. High-Performance Write (No StringFormat overhead)
      FileWrite(h, ticks[i].time_msc, ticks[i].bid, ticks[i].ask);

      // 3. Warning-Free Progress Logic
      // We use 'i' (int) and progress_interval (int) - No sign mismatch
      if((i + 1) % progress_interval == 0) {
         int percent = (int)(((long)(i + 1) * 100) / copied);
         long elapsed_ms = (long)GetTickCount64() - process_start;
         
         // Calculate ETA using long to prevent overflow
         long eta = (i > 0) ? (long)((double)elapsed_ms / (i + 1) * (copied - i - 1) / 1000.0) : 0;
         
         PrintFormat("📊 Progress: %d%% | Elapsed: %llds | ETA: %llds", 
                     percent, elapsed_ms / 1000, eta);
      }
   }

   FileClose(h);
   long total_time = (long)GetTickCount64() - start_time;
   PrintFormat("✅ Export Complete. Total Time: %.2f sec", total_time / 1000.0);
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
# Load tick data from MT5 Files directory
TICK_FILE_NAME = 'achilles_ticks.csv'
INPUT_TICK_DATA = os.path.join(SCRIPT_DIR, '..', '..', 'Files', TICK_FILE_NAME)

parser = argparse.ArgumentParser(description='Train Achilles neural network model')
parser.add_argument('--tick-density', type=int, default=144, help='Ticks per bar')
args = parser.parse_args()

TICK_DENSITY = args.tick_density
OUTPUT_ONNX_MODEL = os.path.join(SCRIPT_DIR, f'achilles_{TICK_DENSITY}.onnx') 

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

# 3. FEATURE ENGINEERING (Parity with MQL5 Built-ins)
print("Building 35 Features...")
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
# Correlations
df['f30'] = df['usdx'].pct_change()
df['f31'] = df['usdjpy'].pct_change()
# Bollinger Band Width
for p, f_idx in zip([9, 18, 27], [32, 33, 34]):
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
features =[f'f{i}' for i in range(35)]
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
# New Input: 4200 flat numbers (120 bars * 35 features)
in_lay = tf.keras.Input(shape=(4200,), name="input") 

# Internally reshape to what LSTM needs: (Batch=1, Timesteps=120, Features=35)
rs = tf.keras.layers.Reshape((120, 35))(in_lay)

ls = tf.keras.layers.LSTM(64, return_sequences=True, activation='mish')(rs)
at = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=64)(ls, ls)
pl = tf.keras.layers.GlobalAveragePooling1D()(at)
ou = tf.keras.layers.Dense(3, activation='softmax')(pl)
model = tf.keras.Model(in_lay, ou)
model.compile(optimizer='adamw', loss='sparse_categorical_crossentropy')

# Flatten the training data to match the new input shape
X_seq_flat = X_seq.reshape(-1, 4200)

print("Training...")
model.fit(X_seq_flat, y_seq, epochs=10, batch_size=64)

# 7. EXPORT TO ONNX (FLAT SHAPE)
print("Exporting model to ONNX...")
# Input is now just a flat vector of 4200
spec = (tf.TensorSpec((None, 4200), tf.float32, name="input"),) 
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)

with open(OUTPUT_ONNX_MODEL, "wb") as f:
    f.write(model_proto.SerializeToString())

print("\n--- PASTE THESE INTO live.mq5 ---")
print(f"float medians[35] = {{{', '.join([f'{m:.8f}f' for m in median])}}};")
print(f"float iqrs[35] = {{{', '.join([f'{s:.8f}f' for s in iqr])}}};")
```

live.mq5
```cpp
﻿//+------------------------------------------------------------------+
//|                                              Live_Achilles.mq5   |
//|                                  Copyright 2026, Achilles Algo   |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

// 1. RESOURCE & INPUTS
#resource "\\Experts\\nn\\achilles_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      
input double TP_MULTIPLIER = 2.7;      
input double SL_MULTIPLIER = 0.54;     
input string USDX_Symbol   = "$USDX";  
input string USDJPY_Symbol = "USDJPY"; 
input int    MAGIC_NUMBER  = 144144;   

// --- SCALING PARAMETERS ---
// PASTE THE OUTPUT FROM YOUR PYTHON SCRIPT HERE
float medians[35] = {-0.000006f, 0.104931f, 30150.0f, 0.000127f, 0.000132f, 0.000805f, 0.503401f, 49.824540f, 49.608665f, 49.568888f, 0.000869f, 0.000876f, 0.000880f, -0.000016f, -0.000016f, -0.000000f, 0.000017f, 0.000014f, 0.000043f, 0.000105f, 0.000096f, -126020.69f, -83237.61f, -65911.13f, -49.7117f, -49.7000f, -48.6915f, -0.000023f, -0.000085f, -0.000105f, 0.000000f, 0.000000f, 0.002801f, 0.003922f, 0.004775f};
float iqrs[35]    = {0.000780f, 0.022743f, 5272.5f, 0.000250f, 0.000255f, 0.000658f, 0.663998f, 21.478885f, 14.504269f, 11.509027f, 0.000528f, 0.000507f, 0.000490f, 0.000749f, 0.000683f, 0.000274f, 0.001109f, 0.001674f, 0.002106f, 0.002950f, 0.005309f, 124022.83f, 75234.65f, 57520.73f, 59.110822f, 57.496001f, 56.672005f, 0.002549f, 0.003638f, 0.004620f, 0.000101f, 0.000113f, 0.002482f, 0.003295f, 0.004007f};

// --- GLOBAL HANDLES ---
int hRSI9, hRSI18, hRSI27, hATR9, hATR18, hATR27, hMACD, hEMA9, hEMA18, hEMA27, hEMA54, hEMA144, hCCI9, hCCI18, hCCI27, hWPR9, hWPR18, hWPR27, hBB9, hBB18, hBB27;
long onnx_handle = INVALID_HANDLE;
CTrade trade;

// --- ONNX DATA BUFFERS ---
float input_data[4200]; // 1 * 120 * 35 = 4200
float output_data[3];   // Softmax: [Neutral, Buy, Sell]

// --- TICK BAR STORAGE ---
struct Bar {
   double o, h, l, c, spread, usdx, jpy;
   long time_start;
};
Bar history[150]; // History buffer for returns and momentum
int ticks_in_bar = 0;
Bar current_bar;

//+------------------------------------------------------------------+
//| Initialization                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   if(!SymbolSelect(USDX_Symbol, true) || !SymbolSelect(USDJPY_Symbol, true)) {
      Print("❌ Missing Symbols: ", USDX_Symbol, " or ", USDJPY_Symbol);
      return(INIT_FAILED);
   }
   
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("❌ ONNX Handle Error: ", GetLastError());
      return(INIT_FAILED);
   }

   // --- SET FLAT SHAPES (1, 4200) ---
   const long in_shape[] = {1, 4200};
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
   Print("✅ Achilles Online. Flat-Tensor Model Loaded.");
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
      current_bar.usdx = SymbolInfoDouble(USDX_Symbol, SYMBOL_BID);
      current_bar.jpy = SymbolInfoDouble(USDJPY_Symbol, SYMBOL_BID);
      
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

   // Populate the flat 4200 array
   for(int i=0; i<120; i++) {
      int h_idx = 119 - i; // Older bars first [119 ... 0]
      int ind = i;         // Index in indicator buffer (where 0 is newest)
      // Note: pandas_ta calculates newest at the bottom of the dataframe. 
      // We fill the 120-window such that i=0 is oldest and i=119 is newest bar.
      int buf_idx = 119 - i; // Index in copied indicator buffers corresponding to h_idx
      
      float f[35];
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
      f[30] = (float)((history[h_idx].usdx - history[h_idx+1].usdx) / (history[h_idx+1].usdx + 1e-8));
      f[31] = (float)((history[h_idx].jpy - history[h_idx+1].jpy) / (history[h_idx+1].jpy + 1e-8));
      f[32] = (float)((b9u[buf_idx] - b9l[buf_idx]) / close);
      f[33] = (float)((b18u[buf_idx] - b18l[buf_idx]) / close);
      f[34] = (float)((b27u[buf_idx] - b27l[buf_idx]) / close);

      for(int k=0; k<35; k++) {
         input_data[i * 35 + k] = (f[k] - medians[k]) / (iqrs[k] + 1e-8f);
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
