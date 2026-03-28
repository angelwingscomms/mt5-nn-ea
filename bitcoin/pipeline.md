data.mq5
```cpp
#property script_show_inputs
input int ticks_to_export = 2160000;
input int days_lookback   = 180;     // Force anchor 6 months into the past
input int chunk_size      = 100000;

void OnStart() {
   Print("[INFO] Initializing Absolute-Chronological Tick Export...");
   ResetLastError();

   int h = FileOpen("fast/bitcoin_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) { 
      Print("❌ FATAL I/O ERROR: Cannot open CSV file."); 
      return; 
   }
   
   FileWrite(h, "time_msc", "bid", "ask", "vol"); 
   
   MqlTick ticks[];
   int total_copied = 0;
   
   // CRITICAL FIX: Establish a strict temporal anchor in the deep past (Safe 64-bit math)
   ulong anchor_msc = ((ulong)TimeCurrent() - ((ulong)days_lookback * 86400ull)) * 1000ull;
   ulong last_time  = anchor_msc;
   
   PrintFormat("[INFO] Temporal Anchor set to %d days ago. Moving strictly forward in time...", days_lookback);
   
   while(total_copied < ticks_to_export) {
      int to_copy = MathMin(chunk_size, ticks_to_export - total_copied);
      
      ulong fetch_start = GetTickCount64();
      int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, last_time, to_copy);
      ulong fetch_time = GetTickCount64() - fetch_start;
      
      if(copied <= 0) {
         PrintFormat("⚠️ Stream exhausted. The broker has no more historical data. Copied: %d | Total: %d", copied, total_copied);
         break;
      }
      
      // Advance pointer strictly forward to the exact millisecond after the last recorded tick
      last_time = ticks[copied-1].time_msc + 1; 
      
      int valid_ticks = 0;
      for(int i = 0; i < copied; i++) {
         if(ticks[i].bid <= 0.0 || ticks[i].ask < ticks[i].bid) continue; // Noise filter
         
         double v = (ticks[i].volume > 0) ? (double)ticks[i].volume : 1.0;
         FileWrite(h, ticks[i].time_msc, ticks[i].bid, ticks[i].ask, v);
         valid_ticks++;
      }
      
      total_copied += copied;
      
      // Real-time telemetry: Watch the date advance chronologically
      double progress = ((double)total_copied / ticks_to_export) * 100.0;
      PrintFormat("[STREAM] %.2f%% | Fetched: %d | Processing Date: %s | Total: %d / %d", 
                  progress, copied, TimeToString(ticks[copied-1].time), total_copied, ticks_to_export);
                  
      // Halt if we slam into the present moment
      if(last_time >= (ulong)TimeCurrent() * 1000ull) {
          Print("[INFO] Temporal pointer reached the present moment. Halting stream.");
          break;
      }
                  
      Sleep(10); // Yield to MT5 Main Thread
   }
   
   FileClose(h);
   PrintFormat("✅ EXPORT COMPLETE. Serialized %d ticks. Proceed to Python tensor generation.", total_copied);
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
from tensorflow.keras import layers, Model, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix

tf.keras.utils.set_random_seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TICK_DATA = os.path.join(SCRIPT_DIR, 'bitcoin_ticks.csv')
TICK_DENSITY = 144
SEQ_LEN = 120
TARGET_HORIZON = 30
OUTPUT_ONNX_MODEL = os.path.join(SCRIPT_DIR, f'bitcoin_{TICK_DENSITY}.onnx') 

print("Loading Microstructure Bars...")
df_t = pd.read_csv(INPUT_TICK_DATA)
df_t['vol'] = df_t['vol'].replace(0, 1.0) 
df_t['bar_id'] = np.arange(len(df_t)) // TICK_DENSITY

df = df_t.groupby('bar_id').agg({
    'bid':['first', 'max', 'min', 'last'],
    'vol': 'sum',
    'time_msc': 'first'
})
df.columns =['open', 'high', 'low', 'close', 'volume', 'time_open']
df['spread'] = df_t.groupby('bar_id').apply(lambda x: (x['ask']-x['bid']).mean()).values

print("Engineering 17 Orthogonal Features...")
df['tpv'] = df['close'] * df['volume']
df['tvwp'] = df['tpv'].rolling(144).sum() / (df['volume'].rolling(144).sum() + 1e-8)
df['dt'] = pd.to_datetime(df['time_open'], unit='ms', utc=True)

# [f0 - f6] Price & Microstructure
df['f0'] = np.log(df['close'] / df['close'].shift(1))
df['f1'] = df['spread']
df['f2'] = df['dt'].diff().dt.total_seconds().fillna(0)
df['f3'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
df['f4'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
df['f5'] = (df['high'] - df['low']) / df['close']
df['f6'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)

# [f7 - f9] MACD Core
m = ta.macd(df['close'], 12, 26, 9)
df['f7'], df['f8'], df['f9'] = m.iloc[:, 0]/df['close'], m.iloc[:, 2]/df['close'], m.iloc[:, 1]/df['close']

# [f10] Volatility
df['f10'] = ta.atr(df['high'], df['low'], df['close'], length=18) / df['close']

# [f11 - f14] Time Embeddings (Strict UTC)
df['f11'] = np.sin(2 * np.pi * df['dt'].dt.hour / 24)
df['f12'] = np.cos(2 * np.pi * df['dt'].dt.hour / 24)
df['f13'] = np.sin(2 * np.pi * df['dt'].dt.dayofweek / 7)
df['f14'] = np.cos(2 * np.pi * df['dt'].dt.dayofweek / 7)

# [f15 - f16] Volume & TVWP Drift
df['f15'] = np.log(df['volume'] + 1)
df['f16'] = (df['close'] - df['tvwp']) / df['close'] 

df.dropna(inplace=True)
df.reset_index(drop=True, inplace=True)

def get_labels(df):
    c, hi, lo = df.close.values, df.high.values, df.low.values
    atr = ta.atr(df.high, df.low, df.close, length=18).values
    t = np.zeros(len(df), dtype=int)
    for i in range(len(df)-TARGET_HORIZON):
        if np.isnan(atr[i]): continue
        up, lw = c[i]+(2.7*atr[i]), c[i]-(0.54*atr[i])
        for j in range(i+1, i+TARGET_HORIZON+1):
            if hi[j] >= up: t[i] = 1; break 
            if lo[j] <= lw: t[i] = 2; break 
    return t

df['target'] = get_labels(df)
X, y = df[[f'f{i}' for i in range(17)]].values, df['target'].values

# ======================================================================
# 🛡️ ARMOR-PLATED TENSOR SCALING
# ======================================================================
split_time = int(len(X) * 0.9)
median = np.median(X[:split_time], axis=0)
iqr = np.percentile(X[:split_time], 75, axis=0) - np.percentile(X[:split_time], 25, axis=0)

# CRITICAL FIX: Prevent Micro-Variance Scaling Explosions
# If a feature has zero variance in the small training window, default its scale to 1.0
iqr = np.where(iqr < 1e-4, 1.0, iqr)

X_s = (X - median) / iqr

# CRITICAL FIX: Strict Feature Space Clipping
# No input feature is mathematically allowed to exceed +/- 10 standard deviations.
X_s = np.clip(X_s, -10.0, 10.0)

X_seq, y_seq = [],[]
for i in range(len(X_s)-SEQ_LEN):
    X_seq.append(X_s[i:i+SEQ_LEN])
    y_seq.append(y[i+(SEQ_LEN-1)])
X_seq, y_seq = np.array(X_seq), np.array(y_seq)

# ======================================================================
# 🚨 STRICT PURGED EMBARGO TIME-SERIES SPLIT
# ======================================================================
gap = SEQ_LEN + TARGET_HORIZON
total_seqs = len(X_seq)

print(f"[INFO] Total Temporal Sequences Generated: {total_seqs}")

if total_seqs <= gap + 32:
    print(f"❌ FATAL ERROR: Dimensional Starvation.")
    print(f"You have {total_seqs} sequences. The causality gap requires {gap} steps, leaving nothing for validation.")
    print(f"Fix: Export a vastly larger tick history from MQL5.")
    exit(1)

# Dynamically calculate split to guarantee AT LEAST 10% or a minimum of 32 samples for validation
val_size = max(32, int(total_seqs * 0.10))
train_idx = total_seqs - gap - val_size

if train_idx < 32:
    print("❌ FATAL ERROR: Training set would be reduced to less than 1 batch due to the required Embargo Gap.")
    exit(1)

X_train, y_train = X_seq[:train_idx], y_seq[:train_idx]
X_val, y_val     = X_seq[train_idx+gap:], y_seq[train_idx+gap:]

print(f"[INFO] Array Partitioning Complete:")
print(f"       -> Training Tensor:   {X_train.shape[0]} samples")
print(f"       -> Embargo Gap:       {gap} samples (Purged)")
print(f"       -> Validation Tensor: {X_val.shape[0]} samples")

X_train = X_train.reshape(-1, 2040)
X_val   = X_val.reshape(-1, 2040)

# ======================================================================
# 🛡️ L2-REGULARIZED CAUSAL TCN ARCHITECTURE
# ======================================================================
from tensorflow.keras import regularizers

def tcn_block(x, filters, dilation):
    # Added L2 regularization to completely eliminate weight explosions
    reg = regularizers.l2(1e-4)
    
    shortcut = layers.Conv1D(filters, 1, padding='same', kernel_regularizer=reg)(x)
    x = layers.Conv1D(filters, 3, padding='causal', dilation_rate=dilation, 
                      activation='relu', kernel_regularizer=reg)(x)
    x = layers.LayerNormalization()(x)
    x = layers.Conv1D(filters, 3, padding='causal', dilation_rate=dilation, 
                      activation='relu', kernel_regularizer=reg)(x)
    x = layers.LayerNormalization()(x)
    return layers.Add()([shortcut, x])

inp = Input(shape=(2040,), name="input")
x = layers.Reshape((120, 17))(inp)

for d in[1, 2, 4, 8, 16]: 
    x = tcn_block(x, 64, d)

x = layers.GlobalAveragePooling1D()(x)
x = layers.Dense(128, activation='relu', kernel_regularizer=regularizers.l2(1e-4))(x)
x = layers.Dropout(0.4)(x) # Increased dropout for extreme small-sample protection
out = layers.Dense(3, activation='softmax', name="output")(x)

model = Model(inp, out)

model.compile(optimizer=tf.keras.optimizers.AdamW(1e-3, weight_decay=1e-4, clipnorm=1.0), 
              loss='sparse_categorical_crossentropy', 
              metrics=['accuracy'])

# Defend against mode collapse dynamically
cw = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
class_weights = {i: w for i, w in zip(np.unique(y_train), cw)}

callbacks =[
    EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
]

print("\n[INFO] Commencing Training Phase...")
model.fit(X_train, y_train, 
          validation_data=(X_val, y_val), 
          epochs=144, 
          batch_size=32, 
          class_weight=class_weights, 
          callbacks=callbacks)

print("\n[INFO] Post-Training Empirical Evaluation:")
# Explicit check to prevent crashes if validation array is severely compromised
if len(X_val) > 0:
    y_pred = np.argmax(model.predict(X_val, batch_size=32, verbose=0), axis=1)
    
    # Check if all classes are predicted to avoid scikit-learn warnings
    labels_present = np.unique(np.concatenate((y_val, y_pred)))
    print(classification_report(y_val, y_pred, labels=labels_present, zero_division=0))
    print("Confusion Matrix:\n", confusion_matrix(y_val, y_pred, labels=labels_present))
else:
    print("⚠️ WARNING: Validation tensor empty. Evaluation bypassed.")

# EXPORT (Batch Size 1)
spec = (tf.TensorSpec((1, 2040), tf.float32, name="input"),)
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)
with open(OUTPUT_ONNX_MODEL, "wb") as f: f.write(model_proto.SerializeToString())

print("\n--- UPDATE live.mq5 WITH THESE 17-DIMENSIONAL SCALERS ---")
print(f"float medians[17] = {{{', '.join([f'{m:.8f}f' for m in median])}}};")
print(f"float iqrs[17]    = {{{', '.join([f'{s:.8f}f' for s in iqr])}}};")
```

live.mq5
```cpp
﻿#include <Trade\Trade.mqh>

#resource "\\Experts\\nn\\bitcoin\\bitcoin_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      
input double TP_MULTIPLIER = 2.7;      
input double SL_MULTIPLIER = 0.54;     
input int    MAGIC_NUMBER  = 144144;   

// --- PASTE SCALERS FROM PYTHON HERE ---
float medians[17] = {0.0f}; // Replace
float iqrs[17]    = {1.0f}; // Replace

long onnx_handle = INVALID_HANDLE;
CTrade trade;
float input_data[2040]; 
float output_data[3];   
datetime last_loss_time = 0;

// High-Density Orthogonal Feature Struct
struct Bar { 
   double o, h, l, c, v, spread, tvwp; 
   ulong time_msc; // Preserved exactly from tick for UTC math
   double atr18; 
   double macd_ema12, macd_ema26, macd_sig;
};
Bar history[200]; 
int ticks_in_bar = 0;
Bar cur_b;
bool warmed_up = false;

int OnInit() {
   if(ArraySize(model_buffer) == 0) return(INIT_FAILED);
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) return(INIT_FAILED);

   const long in_shape[] = {1, 2040};
   const long out_shape[] = {1, 3};
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape)) return(INIT_FAILED);
   if(!OnnxSetOutputShape(onnx_handle, 0, out_shape)) return(INIT_FAILED);
   
   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   
   Print("[INFO] Pre-warming Internal Indicator States...");
   MqlTick pre_ticks[];
   int copied = CopyTicks(_Symbol, pre_ticks, COPY_TICKS_ALL, 0, 50000);
   for(int i = 0; i < copied; i++) ProcessTick(pre_ticks[i]);
   warmed_up = true;
   
   Print("✅ Neural Architecture Locked. State Warmed (17 Features).");
   return(INIT_SUCCEEDED);
}

void OnTick() {
   MqlTick t; if(SymbolInfoTick(_Symbol, t)) ProcessTick(t);
}

void ProcessTick(MqlTick &t) {
   if(ticks_in_bar == 0) {
      cur_b.o = t.bid; cur_b.h = t.bid; cur_b.l = t.bid; cur_b.c = t.bid; 
      cur_b.v = 0; cur_b.spread = 0; cur_b.time_msc = t.time_msc;
   }
   cur_b.h = MathMax(cur_b.h, t.bid); 
   cur_b.l = MathMin(cur_b.l, t.bid); 
   cur_b.c = t.bid;
   double tv = (t.volume > 0) ? (double)t.volume : 1.0;
   cur_b.v += tv; 
   cur_b.spread += (t.ask - t.bid);
   ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      cur_b.spread /= TICK_DENSITY;
      ComputeIndicators(cur_b);
      
      for(int i=199; i>0; i--) history[i] = history[i-1];
      history[0] = cur_b;
      ticks_in_bar = 0;
      
      if(warmed_up) Predict();
   }
}

// Minimal, exact mathematical parity
void ComputeIndicators(Bar &b) {
   Bar p = history[0]; 
   if(p.c == 0.0) p = b; 
   
   // RMA Smoothing (Wilder's ATR 18)
   double tr = MathMax(b.h - b.l, MathMax(MathAbs(b.h - p.c), MathAbs(b.l - p.c)));
   b.atr18 = (tr - p.atr18)/18.0 + p.atr18;

   // MACD 12, 26, 9
   b.macd_ema12 = (b.c - p.macd_ema12)*(2.0/13.0) + p.macd_ema12;
   b.macd_ema26 = (b.c - p.macd_ema26)*(2.0/27.0) + p.macd_ema26;
   double macd_raw = b.macd_ema12 - b.macd_ema26;
   b.macd_sig = (macd_raw - p.macd_sig)*(2.0/10.0) + p.macd_sig;
   
   // TVWP
   double sum_pv = 0, sum_v = 0;
   for(int j=0; j<143 && j<200; j++) { sum_pv += (history[j].c * history[j].v); sum_v += history[j].v; }
   sum_pv += (b.c * b.v); sum_v += b.v;
   b.tvwp = sum_pv / (sum_v + 1e-8);
}

void Predict() {
   if(history[144].c == 0.0) return; 
   if(TimeCurrent() < last_loss_time + 3600) return; 

   for(int i=0; i<120; i++) {
      int h = 119 - i; 
      float f[17];
      double cl = history[h].c;
      
      // ABSOLUTE UTC TIME PARITY (Bypasses MQL5 Broker Timezone Offset)
      double utc_hour = (double)((history[h].time_msc / 3600000) % 24);
      double utc_dow  = (double)(((history[h].time_msc / 86400000) + 4) % 7); // Jan 1 1970 was Thursday (4)

      f[0]=(float)MathLog(cl/(history[h+1].c+1e-8)); 
      f[1]=(float)history[h].spread; 
      f[2]=(float)((history[h].time_msc - history[h+1].time_msc) / 1000.0); 
      f[3]=(float)((history[h].h-MathMax(history[h].o,cl))/cl); 
      f[4]=(float)((MathMin(history[h].o,cl)-history[h].l)/cl);
      f[5]=(float)((history[h].h-history[h].l)/cl); 
      f[6]=(float)((cl-history[h].l)/(history[h].h-history[h].l+1e-8));
      
      double mm = history[h].macd_ema12 - history[h].macd_ema26;
      f[7]=(float)(mm/cl); 
      f[8]=(float)(history[h].macd_sig/cl); 
      f[9]=(float)((mm-history[h].macd_sig)/cl);
      
      f[10]=(float)(history[h].atr18/cl);
      
      f[11]=(float)MathSin(2.0*M_PI*utc_hour/24.0); 
      f[12]=(float)MathCos(2.0*M_PI*utc_hour/24.0);
      f[13]=(float)MathSin(2.0*M_PI*utc_dow/7.0); 
      f[14]=(float)MathCos(2.0*M_PI*utc_dow/7.0);
      
      f[15]=(float)MathLog(history[h].v + 1.0); 
      f[16]=(float)((cl - history[h].tvwp)/cl);

      for(int k=0; k<17; k++) input_data[i*17+k] = (f[k]-medians[k])/(iqrs[k]);
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) return;
   
   int sig = ArrayMaximum(output_data);
   if((sig == 1 || sig == 2) && output_data[sig] > 0.65 && !HasPos()) {
      Exec(sig == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   }
}

void Exec(ENUM_ORDER_TYPE type) {
   double atr = history[0].atr18;
   double p = (type==ORDER_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_ASK):SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double sl = (type==ORDER_TYPE_BUY)?(p-atr*SL_MULTIPLIER):(p+atr*SL_MULTIPLIER);
   double tp = (type==ORDER_TYPE_BUY)?(p+atr*TP_MULTIPLIER):(p-atr*TP_MULTIPLIER);
   trade.PositionOpen(_Symbol,type,0.1,p,sl,tp);
}

bool HasPos() {
   for(int i=PositionsTotal()-1; i>=0; i--)
      if(PositionGetSymbol(i)==_Symbol && PositionGetInteger(POSITION_MAGIC)==MAGIC_NUMBER) return true;
   return false;
}

void OnDeinit(const int reason) { if(onnx_handle != INVALID_HANDLE) OnnxRelease(onnx_handle); }
```
