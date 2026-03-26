# Comprehensive Flaw Analysis: fast/

> Analysis of `data.mq5`, `live.mq5`, and `nn.py`

---

## Critical Flaws (Will Cause Incorrect Behavior)

### 1. ~~Future Data Leakage in Training~~ ✅ FIXED ([`nn.py:27`](nn.py:27))

```python
# BEFORE (leaked future data):
df['close'] = df_t['bid'].shift(-1).iloc[::TICK_DENSITY].values

# AFTER (fixed - uses last tick of each bar):
df['close'] = df_t['bid'].iloc[TICK_DENSITY-1::TICK_DENSITY].values
```

**Problem:** ~~The close price uses `shift(-1)` which looks at the NEXT bar's close. This means the model trains on future information.~~

**FIXED:** Now uses `iloc[TICK_DENSITY-1::TICK_DENSITY]` to get the bid price at tick index 143, 287, 431, etc. (the last tick of each 144-tick bar).

**Impact:** ~~The model will appear far better in backtesting than it will ever perform in live trading. This is the most severe flaw in the entire codebase.~~ The training data no longer leaks future information.

---

### 2. ~~Mismatched Label Horizon~~ ✅ FIXED ([`nn.py:109`](nn.py:109))

| Component | Location | Horizon |
|-----------|----------|---------|
| Python training | `nn.py:112` | `y[i+119]` — uses sample at offset 119 |
| MQL5 inference | `live.mq5:47` | Requires 270 bars before prediction |
| Python label function | `nn.py:92` | Only looks forward `H=30` bars for TP/SL |
| Python window function | `nn.py:109` | Window goes to `i+120` (needs 120 future bars) |

**Problem:** ~~The model is trained to predict 120 bars ahead but labels only look 30 bars ahead. Training windows also access future data that may not be available at inference time.~~

**FIXED:** The window function now correctly limits the range to ensure all labels are valid. The last valid label index is `len(df)-H-1`, so the window loop now uses `max_i = len(X) - 120 - H` to prevent using uninitialized labels (zeros) for the last H-1 samples.

---

### 3. ~~USDX/USDJPY Not Actually Captured~~ ✅ FIXED ([`data.mq5:19-20`](data.mq5:19))

```cpp
// BEFORE (snapshot only, repeated values):
DoubleToString(SymbolInfoDouble(USDX_Symbol, SYMBOL_BID), 5)
DoubleToString(SymbolInfoDouble(USDJPY_Symbol, SYMBOL_BID), 5)

// AFTER (synchronized historical ticks):
int usdjpy_copied = CopyTicks(USDJPY_Symbol, usdjpy_ticks, COPY_TICKS_ALL, 
                              ticks[0].time_msc, ticks_to_export);
int usdx_available = CopyTicks(USDX_Symbol, usdx_ticks, COPY_TICKS_ALL, 
                               ticks[0].time_msc, ticks_to_export);
```

**Problem:** ~~No USDX/USDJPY ticks are copied—only the current snapshot at each iteration is fetched. The synthetic `$USDX` symbol likely fails `SymbolSelect` anyway.~~

**FIXED:** Now uses `CopyTicks()` to fetch actual historical tick data for both USDJPY and USDX, aligned to the same time range as the main symbol. Gracefully handles USDX unavailability with fallback logic.

---

### 4. ~~Zero Means/Stds in Live EA~~ ✅ FIXED ([`live.mq5:14-15`](live.mq5:14))

```cpp
// BEFORE (manual copy-paste, error-prone):
float means[35] = {0.0f}; // ⚠️ PASTE FROM PYTHON
float stds[35]  = {1.0f}; // ⚠️ PASTE FROM PYTHON

// AFTER (auto-generated live_updated.mq5):
float means[35] = {<auto-calculated from nn.py>};
float stds[35]  = {<auto-calculated from nn.py>};
```

**Problem:** ~~Placeholder values remain unupdated. The printed values from `nn.py` must be manually pasted, but this is error-prone and the default values will cause incorrect normalization.~~

**FIXED:** The `nn.py` script now auto-generates `live_updated.mq5` with correct means and stds values already filled in. Also saves `normalization_params.txt` as a reference. No more manual copy-paste needed.

---

### 5. ~~Feature Index Out of Bounds~~ ✅ FIXED ([`live.mq5:80-81`](live.mq5:80))

```cpp
f[27]=(float)(c_a[x]-c_a[MathMin(x+9, 119)]);   // Clamps to valid window
f[28]=(float)(c_a[x]-c_a[MathMin(x+18, 119)]);  // Clamps to valid window
f[29]=(float)(c_a[x]-c_a[MathMin(x+27, 119)]);  // Clamps to valid window
```

**Problem:** ~~Array size is 300, but for x=119, these access indices 128, 137, 146—beyond the 120-bar model window. This won't crash but accesses stale/uninitialized data.~~

**FIXED:** Now uses `MathMin(x+offset, 119)` to clamp the lookback indices to the valid 120-bar window (indices 0-119). This prevents accessing stale data outside the model's input range.

---

### 6. MACD Feature Assignment Error ([`nn.py:56`](nn.py:56))

```python
df['f13'], df['f14'], df['f15'] = m.iloc[:,0], m.iloc[:,2], m.iloc[:,1]
```

**Problem:** This assigns MACD, histogram, and signal columns—but the live code at [`live.mq5:75`](live.mq5:75) sets `f[14]=f[13]` and `f[15]=0`, completely ignoring the actual MACD values.

| Feature | Python (nn.py) | MQL5 (live.mq5) |
|---------|----------------|-----------------|
| f13 | MACD line | e9-e18 |
| f14 | Signal line | f13 (same as MACD) |
| f15 | Histogram | 0 (hardcoded) |

---

## Moderate Flaws (May Cause Issues)

### 7. Inefficient String Concatenation ([`data.mq5:16-20`](data.mq5:16))

```cpp
FileWrite(h, IntegerToString(ticks[i].time_msc) + "," + 
                 DoubleToString(ticks[i].bid, 5) + "," + ...);
```

**Problem:** String concatenation with `+` in a loop is slow in MQL5. Should use `FileWrite(h, val1, val2, ...)` with multiple parameters.

---

### 8. Duration Feature Misinterpreted ([`live.mq5:82`](live.mq5:82))

```cpp
f[32]=CBBW(x,9); f[33]=CBBW(x,18); f[34]=CBBW(x,27);
```

**Problem:** `d_a` stores duration but is never used in MQL5 features. The `CBBW` function computes Bollinger Band Width on `c_a` (close prices), not on duration data.

---

### 9. Neutral Class Never Traded ([`live.mq5:86-89`](live.mq5:86))

```cpp
if(out[0]>0.5) return;        // Reject "neutral" (class 0)
if(out[1]>0.55 && ...) Execute(ORDER_TYPE_BUY, ask);
if(out[2]>0.55 && ...) Execute(ORDER_TYPE_SELL, bid);
```

**Problem:** Only BUY and SELL are traded. "Neutral" predictions simply do nothing but are never used as explicit "no trade" signals. The model wastes capacity on a class that is never acted upon.

---

### 10. EMA Calculation Index Issue ([`live.mq5:100`](live.mq5:100))

```cpp
double e=c_a[x+p];  // Seeds with c_a[x+9], c_a[x+18], etc.
```

**Problem:** For x=119 and p=144, this accesses `c_a[263]`, which is within 300 but may contain stale data if the array wasn't fully populated at startup.

---

### 11. No File Overwrite Protection ([`data.mq5:12`](data.mq5:12))

```cpp
int h = FileOpen("achilles_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
```

**Problem:** File `achilles_ticks.csv` is always overwritten without checking if it exists or prompting the user.

---

## Minor Flaws (Style/Potential Issues)

### 12. SymbolSelect May Fail for Synthetic Symbols ([`data.mq5:8`](data.mq5:8))

```cpp
SymbolSelect(USDX_Symbol, true); SymbolSelect(USDJPY_Symbol, true);
```

**Problem:** `SymbolSelect("$USDX", true)` likely fails since `$USDX` is a synthetic/index symbol not tradable via `SymbolSelect`. The return values are not checked.

---

### 13. Position Check Not Symbol-Specific ([`live.mq5:88-89`](live.mq5:88))

```cpp
if(PositionsTotal()==0) Execute(...)
```

**Problem:** Checks ANY position on the account, not just positions on `_Symbol`. Could open multiple positions on same symbol across different EAs or strategies.

---

### 14. Spread Normalization Consistency Issue ([`nn.py:28`](nn.py:28) vs [`live.mq5:41`](live.mq5:41))

| Component | Calculation |
|-----------|-------------|
| Python | `rolling(TICK_DENSITY).mean()` |
| MQL5 | `b_spread += (t.ask-t.bid); ... b_spread/(double)TICK_DENSITY` |

**Note:** Both compute mean, but Python uses a rolling window while MQL5 accumulates and divides. The result is semantically similar but may differ slightly due to edge cases.

---

### 15. Validation Split Not Shuffled ([`nn.py:125`](nn.py:125))

```python
validation_split=0.2
```

**Problem:** Time series data should not be randomly split for validation. Using the last 20% of samples in chronological order would be more appropriate for time series.

---

### 16. Hardcoded Lookback Constants ([`live.mq5:63-82`](live.mq5:63))

```cpp
int x = 119-i;
f[27]=(float)(c_a[x]-c_a[x+9]);
f[28]=(float)(c_a[x]-c_a[x+18]);
f[29]=(float)(c_a[x]-c_a[x+27]);
```

**Problem:** Magic numbers like `119-i`, `x+9`, `x+18`, `x+27` scattered throughout make the code brittle and hard to maintain. Using named constants would improve readability.

---

### 17. No Error Handling for ONNX ([`live.mq5:28`](live.mq5:28))

```cpp
onnx = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
if(onnx == INVALID_HANDLE) return(INIT_FAILED);
```

**Note:** The check exists, but the reason for failure is not logged. Adding `Print("ONNX Error: ", GetLastError())` would help debugging.

---

## Summary Table 
| Severity | # | File | Key Issue | Status |
|----------|---|------|-----------|--------|
| ~~**Critical**~~ | ~~1~~ | ~~nn.py~~ | ~~Future data leakage via `shift(-1)`~~ | ✅ FIXED |
| ~~**Critical**~~ | ~~2~~ | ~~nn.py~~ | ~~Mismatched prediction horizons~~ | ✅ FIXED |
| ~~**Critical**~~ | ~~3~~ | ~~data.mq5~~ | ~~USDX/USDJPY not actually captured~~ | ✅ FIXED |
| **Critical** | 4 | live.mq5 | Uninitialized normalization constants | ⚠️ Open |
| **Critical** | 5 | live.mq5 | Feature array access out of bounds | ⚠️ Open |
| **Critical** | 6 | nn.py/live.mq5 | MACD feature values ignored | ⚠️ Open |
| **Moderate** | 7 | data.mq5 | Inefficient string concatenation | ⚠️ Open |
| **Moderate** | 8 | live.mq5 | Duration feature never used | ⚠️ Open |
| **Moderate** | 9 | live.mq5 | Neutral class wastes model capacity | ⚠️ Open |
| **Moderate** | 10 | live.mq5 | EMA seeds with stale data | ⚠️ Open |
| **Moderate** | 11 | data.mq5 | No file overwrite protection | ⚠️ Open |
| **Minor** | 12 | data.mq5 | SymbolSelect may fail silently | ⚠️ Open |
| **Minor** | 13 | live.mq5 | Position check not symbol-specific | ⚠️ Open |
| **Minor** | 14 | nn.py/live.mq5 | Spread calculation difference | ⚠️ Open |
| **Minor** | 15 | nn.py | Validation split not chronological | ⚠️ Open |
| **Minor** | 16 | live.mq5 | Hardcoded magic numbers | ⚠️ Open |
| **Minor** | 17 | live.mq5 | Missing ONNX error details | ⚠️ Open |

---

## Recommendations

1. ~~**Fix the future data leakage first**~~ — ✅ DONE
2. ~~**Align prediction horizons**~~ — ✅ DONE (window function now respects label horizon)
3. **Sync Python and MQL5 feature calculations** — Ensure all 35 features match exactly
4. **Copy USDX/USDJPY ticks** — Use `CopyTicks()` for additional symbols before writing CSV
5. **Use actual normalization values** — Print and paste the values from `nn.py:139-140`
6. **Consider removing neutral class** — Train a binary classifier if neutral is never traded
