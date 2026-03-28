!pip install tf2onnx pandas_ta -q # Install necessary libraries
import pandas as pd
import numpy as np
import pandas_ta as ta
import tensorflow as tf
import tf2onnx
from google.colab import drive

# 1. SETUP
TICK_DENSITY = 144 # Every 144 ticks becomes 1 bar
drive.mount('/content/drive') # Connect to Google Drive
df_t = pd.read_csv('/content/drive/MyDrive/fx/achilles_ticks.csv') # Load ticks

# 2. TICK-BAR CONSTRUCTION (Summarizing 144 ticks into 1 bar)
df = df_t.iloc[::TICK_DENSITY].copy() # Get every 144th row for Time
df['open'] = df_t['bid'].iloc[::TICK_DENSITY].values # Open price
df['high'] = df_t['bid'].rolling(TICK_DENSITY).max().iloc[::TICK_DENSITY].values # Highest bid
df['low'] = df_t['bid'].rolling(TICK_DENSITY).min().iloc[::TICK_DENSITY].values # Lowest bid
df['close'] = df_t['bid'].shift(-1).iloc[::TICK_DENSITY].values # Close price
df['spread'] = (df_t['ask'] - df_t['bid']).rolling(TICK_DENSITY).mean().iloc[::TICK_DENSITY].values # Avg spread
df['duration'] = df_t['time_msc'].diff(TICK_DENSITY).iloc[::TICK_DENSITY].values # Time to finish bar
df.dropna(inplace=True) # Remove empty rows

# 3. FEATURE ENGINEERING (35 FEATURES)
print("Building 35 Features...")
# Microstructure (f0-f6)
df['f0'] = np.log(df['close'] / df['close'].shift(1)) # Log Returns (Price speed)
df['f1'] = df['spread'] # Cost of trading
df['f2'] = df['duration'] # Market intensity (Fast = High activity)
df['f3'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close'] # Upper Shadow (Rejection)
df['f4'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close'] # Lower Shadow (Support)
df['f5'] = (df['high'] - df['low']) / df['close'] # Bar Range (Volatility)
df['f6'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8) # Intrabar Pos (Where it ended)
# Indicators (f7-f29)
df['f7'] = ta.rsi(df['close'], length=9) # RSI 9
df['f8'] = ta.rsi(df['close'], length=18) # RSI 18
df['f9'] = ta.rsi(df['close'], length=27) # RSI 27
df['f10'] = ta.atr(df['high'], df['low'], df['close'], length=9) # Volatility 9
df['f11'] = ta.atr(df['high'], df['low'], df['close'], length=18) # Volatility 18
df['f12'] = ta.atr(df['high'], df['low'], df['close'], length=27) # Volatility 27
m = ta.macd(df['close'], 9, 18, 9) # MACD
df['f13'], df['f14'], df['f15'] = m.iloc[:,0], m.iloc[:,2], m.iloc[:,1] # Line, Signal, Hist
df['f16'] = ta.ema(df['close'], 9) - df['close'] # Dist to EMA 9
df['f17'] = ta.ema(df['close'], 18) - df['close'] # Dist to EMA 18
df['f18'] = ta.ema(df['close'], 27) - df['close'] # Dist to EMA 27
df['f19'] = ta.ema(df['close'], 54) - df['close'] # Dist to EMA 54
df['f20'] = ta.ema(df['close'], 144) - df['close'] # Dist to EMA 144
df['f21'] = ta.cci(df['high'], df['low'], df['close'], 9) # Commodity Channel 9
df['f22'] = ta.cci(df['high'], df['low'], df['close'], 18) # Commodity Channel 18
df['f23'] = ta.cci(df['high'], df['low'], df['close'], 27) # Commodity Channel 27
df['f24'] = ta.willr(df['high'], df['low'], df['close'], 9) # Williams %R 9
df['f25'] = ta.willr(df['high'], df['low'], df['close'], 18) # Williams %R 18
df['f26'] = ta.willr(df['high'], df['low'], df['close'], 27) # Williams %R 27
df['f27'] = ta.mom(df['close'], 9) # Momentum 9
df['f28'] = ta.mom(df['close'], 18) # Momentum 18
df['f29'] = ta.mom(df['close'], 27) # Momentum 27
# Intermarket & BB (f30-f34)
df['f30'] = df['usdx'].pct_change() # Dollar move
df['f31'] = df['usdjpy'].pct_change() # Yield proxy move
for p, f_idx in zip([9, 18, 27], [32, 33, 34]): # Bollinger Widths
    bb = ta.bbands(df['close'], length=p)
    df[f'f{f_idx}'] = (bb.iloc[:,2] - bb.iloc[:,0]) / (bb.iloc[:,1] + 1e-8)
df.dropna(inplace=True)

# 4. TARGETING & TRAINING
TP, SL, H = 1.44, 0.50, 30 # Targets
def label(df, tp, sl, h):
    c, hi, lo = df.close.values, df.high.values, df.low.values
    t = np.zeros(len(df), dtype=int)
    for i in range(len(df)-h):
        up, lw = c[i]+tp, c[i]-sl
        for j in range(i+1, i+h+1):
            if hi[j] >= up: t[i]=1; break
            if lo[j] <= lw: t[i]=2; break
    return t
df['target'] = label(df, TP, SL, H)

# 5. MODEL (LSTM + MULTI-HEAD ATTENTION)
X = df[[f'f{i}' for i in range(35)]].values
mean, std = X.mean(axis=0), X.std(axis=0)
X_s = (X - mean) / (std + 1e-8)
def win(X, y):
    xs, ys = [], []
    for i in range(len(X)-120):
        xs.append(X[i:i+120]); ys.append(y[i+119])
    return np.array(xs), np.array(ys)
X_seq, y_seq = win(X_s, df.target.values)

in_lay = tf.keras.Input(shape=(120, 35))
ls = tf.keras.layers.LSTM(35, return_sequences=True, activation='mish')(in_lay)
at = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=35)(ls, ls)
pl = tf.keras.layers.GlobalAveragePooling1D()(tf.keras.layers.Add()([ls, at]))
ou = tf.keras.layers.Dense(3, activation='softmax')(tf.keras.layers.Dense(20, activation='mish')(pl))
model = tf.keras.Model(in_lay, ou)
model.compile(optimizer='adamw', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(X_seq, y_seq, epochs=54, batch_size=64, validation_split=0.2)

# 6. EXPORT
model.export("/content/ach")
!python -m tf2onnx.convert --saved-model /content/ach --output "/content/drive/MyDrive/fx/achilles_144.onnx" --opset 13
print(f"float means[35]={{{','.join([f'{m:.6f}f' for m in mean])}}};")
print(f"float stds[35]={{{','.join([f'{s:.6f}f' for s in std])}}};")