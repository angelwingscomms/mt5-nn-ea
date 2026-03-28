import pandas as pd
import numpy as np
import pandas_ta as ta
import tensorflow as tf
import tf2onnx
import os
from tensorflow.keras import layers, Model, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.utils.class_weight import compute_class_weight

# PATHS
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TICK_DATA = os.path.join(SCRIPT_DIR, 'bitcoin_ticks.csv')
TICK_DENSITY = 144
OUTPUT_ONNX_MODEL = os.path.join(SCRIPT_DIR, f'bitcoin_{TICK_DENSITY}.onnx') 

if not os.path.exists(INPUT_TICK_DATA):
    print(f"❌ Error: {INPUT_TICK_DATA} not found.")
    exit()

print("Loading and preparing Microstructure Bars...")
df_t = pd.read_csv(INPUT_TICK_DATA)
df_t['vol'] = df_t['vol'].replace(0, 1.0) 
df_t['bar_id'] = np.arange(len(df_t)) // TICK_DENSITY

df = df_t.groupby('bar_id').agg({
    'bid': ['first', 'max', 'min', 'last'],
    'vol': 'sum',
    'time_msc': 'first'
})
df.columns = ['open', 'high', 'low', 'close', 'volume', 'time_open']
df['spread'] = df_t.groupby('bar_id').apply(lambda x: (x['ask']-x['bid']).mean()).values

print("Engineering 39 Institutional Features...")
df['tpv'] = df['close'] * df['volume']
df['tvwp'] = df['tpv'].rolling(144).sum() / (df['volume'].rolling(144).sum() + 1e-8)
df['f38'] = (df['close'] - df['tvwp']) / df['close'] 
df['dt'] = pd.to_datetime(df['time_open'], unit='ms')
df['f33'] = np.sin(2 * np.pi * df['dt'].dt.hour / 24)
df['f34'] = np.cos(2 * np.pi * df['dt'].dt.hour / 24)
df['f35'] = np.sin(2 * np.pi * df['dt'].dt.dayofweek / 7)
df['f36'] = np.cos(2 * np.pi * df['dt'].dt.dayofweek / 7)
df['f37'] = np.log(df['volume'] + 1)
df['f0'] = np.log(df['close'] / df['close'].shift(1))
df['f1'] = df['spread']
df['f2'] = df['dt'].diff().dt.total_seconds().fillna(0) / 1000.0
df['f3'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
df['f4'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']
df['f5'] = (df['high'] - df['low']) / df['close']
df['f6'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-8)

for p, f_idx in zip([9, 18, 27], [7, 8, 9]): df[f'f{f_idx}'] = ta.rsi(df['close'], length=p)
for p, f_idx in zip([9, 18, 27], [10, 11, 12]): df[f'f{f_idx}'] = ta.atr(df['high'], df['low'], df['close'], length=p) / df['close']
m = ta.macd(df['close'], 12, 26, 9)
df['f13'], df['f14'], df['f15'] = m.iloc[:, 0]/df['close'], m.iloc[:, 2]/df['close'], m.iloc[:, 1]/df['close']

for p, f_idx in zip([9, 18, 27, 54, 144],[16, 17, 18, 19, 20]): df[f'f{f_idx}'] = (ta.ema(df['close'], p) - df['close']) / df['close']
for p, f_idx in zip([9, 18, 27], [21, 22, 23]): df[f'f{f_idx}'] = ta.cci(df['high'], df['low'], df['close'], p)
for p, f_idx in zip([9, 18, 27], [24, 25, 26]): df[f'f{f_idx}'] = ta.willr(df['high'], df['low'], df['close'], p)
for p, f_idx in zip([9, 18, 27],[27, 28, 29]): df[f'f{f_idx}'] = df['close'].diff(p) / df['close']
for p, f_idx in zip([9, 18, 27],[30, 31, 32]):
    bb = ta.bbands(df['close'], length=p)
    df[f'f{f_idx}'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / df['close']

df.dropna(inplace=True)

def get_labels(df):
    c, hi, lo = df.close.values, df.high.values, df.low.values
    atr = ta.atr(df.high, df.low, df.close, length=18).values
    t = np.zeros(len(df), dtype=int)
    for i in range(len(df)-30):
        if np.isnan(atr[i]): continue
        up, lw = c[i]+(2.7*atr[i]), c[i]-(0.54*atr[i])
        for j in range(i+1, i+31):
            if hi[j] >= up: t[i] = 1; break 
            if lo[j] <= lw: t[i] = 2; break 
    return t

df['target'] = get_labels(df)
features = [f'f{i}' for i in range(39)]
X, y = df[features].values, df['target'].values

train_end = int(len(X) * 0.7)
median = np.median(X[:train_end], axis=0)
iqr = np.percentile(X[:train_end], 75, axis=0) - np.percentile(X[:train_end], 25, axis=0) + 1e-8
X_s = (X - median) / iqr

X_seq, y_seq = [], []
for i in range(len(X_s)-120):
    X_seq.append(X_s[i:i+120])
    y_seq.append(y[i+119])
X_seq, y_seq = np.array(X_seq), np.array(y_seq)

# 7. TCN MODEL (RELU FOR ONNX COMPATIBILITY)
def tcn_block(x, filters, dilation):
    shortcut = layers.Conv1D(filters, 1, padding='same')(x)
    # Changed 'gelu' to 'relu' to avoid Erfc operator issues in MT5
    x = layers.Conv1D(filters, 3, padding='causal', dilation_rate=dilation, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv1D(filters, 3, padding='causal', dilation_rate=dilation, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    return layers.Add()([shortcut, x])

inp = Input(shape=(4680,), name="input")
x = layers.Reshape((120, 39))(inp)
for d in [1, 2, 4, 8, 16]: x = tcn_block(x, 64, d)
x = layers.GlobalAveragePooling1D()(x)
x = layers.Dense(128, activation='relu')(x)
x = layers.Dropout(0.3)(x)
out = layers.Dense(3, activation='softmax', name="output")(x)

model = Model(inp, out)
model.compile(optimizer=tf.keras.optimizers.AdamW(1e-3), loss='sparse_categorical_crossentropy')

# 8. TRAINING
split = int(len(X_seq) * 0.85)
X_train, X_val = X_seq[:split].reshape(-1, 4680), X_seq[split:].reshape(-1, 4680)
y_train, y_val = y_seq[:split], y_seq[split:]

cw = compute_class_weight('balanced', classes=np.unique(y_seq), y=y_seq)
callbacks = [
    EarlyStopping(monitor='val_loss', patience=12, restore_best_weights=True, verbose=1),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
]

model.fit(X_train, y_train, validation_data=(X_val, y_val), 
          epochs=144, batch_size=64, class_weight=dict(enumerate(cw)), callbacks=callbacks)

# 9. EXPORT (OPSET 13)
spec = (tf.TensorSpec((None, 4680), tf.float32, name="input"),)
model_proto, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)
with open(OUTPUT_ONNX_MODEL, "wb") as f: f.write(model_proto.SerializeToString())

print("\n--- NEW PARAMETERS ---")
print(f"float medians[39] = {{{', '.join([f'{m:.8f}f' for m in median])}}};")
print(f"float iqrs[39]    = {{{', '.join([f'{s:.8f}f' for s in iqr])}}};")