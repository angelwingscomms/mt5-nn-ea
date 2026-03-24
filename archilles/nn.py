import pandas as pd
import numpy as np
import tensorflow as tf
import os
import subprocess

# Disable GPU to prevent local CUDA memory crashes. 
# (Remove this line if you have a properly configured NVIDIA GPU + CUDA).
os.environ['CUDA_VISIBLE_DEVICES'] = '-1' 

local_dir = './'
csv_path = os.path.join(local_dir, 'achilles.csv')
onnx_path = os.path.join(local_dir, 'model_achilles.onnx')

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"❌ FATAL ERROR: Cannot find '{csv_path}'. Run your MQL5 Data Gatherer first!")

print("Loading data...")
df = pd.read_csv(csv_path)
df.dropna(inplace=True)

# ==============================================================================
# 1. NO DATA LEAKAGE: Chronological Split BEFORE Scaling
# ==============================================================================
split_index = int(len(df) * 0.8)
train_df = df.iloc[:split_index].copy()
val_df = df.iloc[split_index:].copy()

features =[f'f{i}' for i in range(35)]

# Calculate Scalers ONLY on Training Data
X_train_raw = train_df[features].values
mean = X_train_raw.mean(axis=0)
std = X_train_raw.std(axis=0)
std[std == 0] = 1e-8 # Prevent division by zero

# Apply the strict training scalers to both sets
train_scaled = (X_train_raw - mean) / std
val_scaled = (val_df[features].values - mean) / std

print("\n=== ⚠️ COPY THESE SCALER PARAMS INTO YOUR MQL5 EA ⚠️ ===")
print(f"float means[35] = {{{', '.join([f'{m:.6f}f' for m in mean])}}};")
print(f"float stds[35] = {{{', '.join([f'{s:.6f}f' for s in std])}}};")
print("========================================================\n")

# ==============================================================================
# 2. NO SURVIVORSHIP BIAS: Multi-Class Categorization (0=Chop, 1=Buy, 2=Sell)
# ==============================================================================
def create_sequences(data_scaled, df_labels):
    X_seq, y_final = [],[]
    labels_buy = df_labels['label_buy'].values
    labels_sell = df_labels['label_sell'].values

    for i in range(len(data_scaled) - 120):
        buy_outcome = labels_buy[i + 119]
        sell_outcome = labels_sell[i + 119]

        if buy_outcome == 1 and sell_outcome == 0:
            target = 1  # Buy Won, Sell Lost
        elif sell_outcome == 1 and buy_outcome == 0:
            target = 2  # Sell Won, Buy Lost
        else:
            target = 0  # Both lost (choppy), or both won (whipsaw). DO NOT TRADE.

        X_seq.append(data_scaled[i : i+120])
        y_final.append(target)
        
    return np.array(X_seq), np.array(y_final)

print("Building strict chronological sequences...")
X_train_seq, y_train = create_sequences(train_scaled, train_df)
X_val_seq, y_val = create_sequences(val_scaled, val_df)

print(f"Training on {len(X_train_seq)} sequences | Validating on {len(X_val_seq)} sequences.")
print(f"Class distribution (Train): Chop: {np.sum(y_train==0)}, Buy Win: {np.sum(y_train==1)}, Sell Win: {np.sum(y_train==2)}")

# ==============================================================================
# 3. ACHILLES ARCHITECTURE (Updated for 3 Outputs)
# ==============================================================================
model = tf.keras.Sequential([
    tf.keras.layers.LSTM(35, input_shape=(120, 35), return_sequences=True, unroll=False, activation='tanh', recurrent_activation='sigmoid'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.LSTM(20, unroll=False, activation='tanh', recurrent_activation='sigmoid'),
    tf.keras.layers.Dense(3, activation='softmax') # 3 Outputs!
])

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.fit(X_train_seq, y_train, epochs=50, batch_size=64, validation_data=(X_val_seq, y_val))

# ==============================================================================
# 4. EXPORT TO ONNX
# ==============================================================================
print("\nExporting model...")
tmp_model_path = os.path.join(local_dir, "tmp_model")
model.export(tmp_model_path)

command =[
    "python", "-m", "tf2onnx.convert",
    "--saved-model", tmp_model_path,
    "--output", onnx_path,
    "--opset", "13"
]

result = subprocess.run(command, capture_output=True, text=True)
if result.returncode == 0:
    print(f"✅ SUCCESSFULLY SAVED: {onnx_path}")
    print("Move this file to your MetaTrader 5 \\MQL5\\Files\\ directory.")
else:
    print("❌ ONNX CONVERSION FAILED. Error:")
    print(result.stderr)