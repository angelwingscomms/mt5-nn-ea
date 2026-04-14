import pandas as pd
import numpy as np
import pandas_ta as ta
import tensorflow as tf
import tf2onnx
import os

# 1. SETUP & PATHS
# Adjust these paths to where your files actually are on your computer
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TICK_DATA = os.path.join(SCRIPT_DIR, 'achilles_ticks.csv')
OUTPUT_ONNX_MODEL = os.path.join(SCRIPT_DIR, 'achilles_144.onnx')
TICK_DENSITY = 144 

if not os.path.exists(INPUT_TICK_DATA):
    print(f"Error: {INPUT_TICK_DATA} not found. Please place the CSV in the same folder.")
    exit()

print("Loading data...")
df_t = pd.read_csv(INPUT_TICK_DATA)

# 2. TICK-BAR CONSTRUCTION
print("Constructing Tick Bars...")
df = df_t.iloc[::TICK_DENSITY].copy()
df['open'] = df_t['bid'].iloc[::TICK_DENSITY].values  # First tick of each bar
df['high'] = df_t['bid'].rolling(TICK_DENSITY).max().iloc[::TICK_DENSITY].values
df['low'] = df_t['bid'].rolling(TICK_DENSITY).min().iloc[::TICK_DENSITY].values
# FIX: Use tick at index (TICK_DENSITY-1) as close (last tick of each bar)
# Previously used shift(-1) which leaked future data from the next bar
df['close'] = df_t['bid'].iloc[TICK_DENSITY-1::TICK_DENSITY].values
df['spread'] = (df_t['ask'] - df_t['bid']).rolling(TICK_DENSITY).mean().iloc[::TICK_DENSITY].values
df['duration'] = df_t['time_msc'].diff(TICK_DENSITY).iloc[::TICK_DENSITY].values

# Dummy columns for USDX/USDJPY if they don't exist in your specific tick file 
# (Based on your original code f30/f31)
if 'usdx' not in df.columns: df['usdx'] = df['close'] # Placeholder
if 'usdjpy' not in df.columns: df['usdjpy'] = df['close'] # Placeholder

df.dropna(inplace=True)

# 3. FEATURE ENGINEERING (35 FEATURES)
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
df['f10'] = ta.atr(df['high'], df['low'], df['close'], length=9)
df['f11'] = ta.atr(df['high'], df['low'], df['close'], length=18)
df['f12'] = ta.atr(df['high'], df['low'], df['close'], length=27)

m = ta.macd(df['close'], 9, 18, 9)
df['f13'], df['f14'], df['f15'] = m.iloc[:,0], m.iloc[:,2], m.iloc[:,1]

df['f16'] = ta.ema(df['close'], 9) - df['close']
df['f17'] = ta.ema(df['close'], 18) - df['close']
df['f18'] = ta.ema(df['close'], 27) - df['close']
df['f19'] = ta.ema(df['close'], 54) - df['close']
df['f20'] = ta.ema(df['close'], 144) - df['close']

df['f21'] = ta.cci(df['high'], df['low'], df['close'], 9)
df['f22'] = ta.cci(df['high'], df['low'], df['close'], 18)
df['f23'] = ta.cci(df['high'], df['low'], df['close'], 27)

df['f24'] = ta.willr(df['high'], df['low'], df['close'], 9)
df['f25'] = ta.willr(df['high'], df['low'], df['close'], 18)
df['f26'] = ta.willr(df['high'], df['low'], df['close'], 27)

df['f27'] = ta.mom(df['close'], 9)
df['f28'] = ta.mom(df['close'], 18)
df['f29'] = ta.mom(df['close'], 27)

df['f30'] = df['usdx'].pct_change()
df['f31'] = df['usdjpy'].pct_change()

for p, f_idx in zip([9, 18, 27], [32, 33, 34]):
    bb = ta.bbands(df['close'], length=p)
    df[f'f{f_idx}'] = (bb.iloc[:,2] - bb.iloc[:,0]) / (bb.iloc[:,1] + 1e-8)

df.dropna(inplace=True)

# 4. TARGETING
TP, SL, H = 1.44, 0.50, 30
def label(df, tp, sl, h):
    c, hi, lo = df.close.values, df.high.values, df.low.values
    t = np.zeros(len(df), dtype=int)
    for i in range(len(df)-h):
        up, lw = c[i]+tp, c[i]-sl
        for j in range(i+1, i+h+1):
            if hi[j] >= up: t[i]=1; break
            if lo[j] <= lw: t[i]=2; break
    return t

print("Labeling data...")
df['target'] = label(df, TP, SL, H)

# 5. MODEL PREP
features = [f'f{i}' for i in range(35)]
X = df[features].values
mean, std = X.mean(axis=0), X.std(axis=0)
X_s = (X - mean) / (std + 1e-8)

def win(X, y, horizon=30):
    xs, ys = [], []
    # FIX: Ensure all labels are valid by limiting range
    # Label at position j is valid only if j <= len(df)-horizon-1
    # We use y[i+119], so i+119 <= len(X)-horizon-1, thus i <= len(X)-horizon-120
    max_i = len(X) - 120 - horizon
    for i in range(max_i + 1):  # +1 because range is exclusive
        xs.append(X[i:i+120]); ys.append(y[i+119])
    return np.array(xs), np.array(ys)

X_seq, y_seq = win(X_s, df.target.values, H)

# 6. MODEL ARCHITECTURE
in_lay = tf.keras.Input(shape=(120, 35))
ls = tf.keras.layers.LSTM(35, return_sequences=True, activation='mish')(in_lay)
at = tf.keras.layers.MultiHeadAttention(num_heads=4, key_dim=35)(ls, ls)
pl = tf.keras.layers.GlobalAveragePooling1D()(tf.keras.layers.Add()([ls, at]))
ou = tf.keras.layers.Dense(3, activation='softmax')(tf.keras.layers.Dense(20, activation='mish')(pl))

model = tf.keras.Model(in_lay, ou)
model.compile(optimizer='adamw', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

print("Starting training...")
model.fit(X_seq, y_seq, epochs=54, batch_size=64, validation_split=0.2)

# 7. EXPORT TO ONNX
print("Exporting model to ONNX...")
spec = (tf.TensorSpec((None, 120, 35), tf.float32, name="input"),)
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)

with open(OUTPUT_ONNX_MODEL, "wb") as f:
    f.write(model_proto.SerializeToString())

print(f"Model saved to {OUTPUT_ONNX_MODEL}")

# PRINT STATS FOR MQL5 / TRADING BOT
print("\n--- Copy these into your C++ / MQL5 code ---")
means_str = f"float means[35]={{{','.join([f'{m:.6f}f' for m in mean])}}};".replace(',', ', ')
stds_str = f"float stds[35]={{{','.join([f'{s:.6f}f' for s in std])}}};"

print(means_str)
print(stds_str)

# Save to file for easy reference
with open(os.path.join(SCRIPT_DIR, 'normalization_params.txt'), 'w') as f:
    f.write("// Copy these lines into live.mq5 (lines 14-15)\n\n")
    f.write(means_str + "\n")
    f.write(stds_str + "\n")

# Auto-generate updated live.mq5 with correct normalization params
print("\n✅ Generated live_updated.mq5 with correct normalization parameters")
live_template = os.path.join(SCRIPT_DIR, 'live.mq5')
if os.path.exists(live_template):
    with open(live_template, 'r') as f_in:
        content = f_in.read()
    
    # Replace placeholder lines 14-15
    content_updated = content.replace(
        'float means[35] = {0.0f}; // ⚠️ PASTE FROM PYTHON',
        means_str
    ).replace(
        'float stds[35]  = {1.0f}; // ⚠️ PASTE FROM PYTHON',
        stds_str
    )
    
    output_file = os.path.join(SCRIPT_DIR, 'live_updated.mq5')
    with open(output_file, 'w') as f_out:
        f_out.write(content_updated)
    
    print(f"   📄 File saved: {output_file}")
    print("   ℹ️  Replace live.mq5 with live_updated.mq5 or copy lines 14-15 from it")