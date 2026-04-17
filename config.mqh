// =============================================================================
// ROOT CONFIG — AU preset for training/testing
//
// This is the repo's primary training config. It is referenced by:
//   - `python nn.py` (picks this as the active config via .active_config)
//   - `python test.py` (loads this for backtesting)
//   - `python export_data.py` (uses SYMBOL from here)
//
// Architecture: "au" (LSTM -> MultiHeadAttention -> GlobalAveragePooling -> Dense)
// The actual architecture hyperparameters live in symbols/xauusd/config/gold.config
// via ARCHITECTURE_CONFIG. This root config supplies everything else: features,
// bars, targets, training, and system settings.
//
// Quick-reference hierarchy:
//   1. Model Identity       — name, symbol, data path, and architecture source
//   2. Feature Sets         — pre-built packs; individual feature toggles override
//   3. Bar Construction     — fixed-tick bars (27 ticks per bar)
//   4. Feature Periods      — lookback windows for all indicator calculations
//   5. Target & Labels      — fixed 1440-point targets, horizon 3
//   6. Trade Sizing         — lot size, SL/TP multipliers, broker limits
//   7. Architecture          — LSTM + Attention (inherited from gold.config)
//   8. Training             — epochs, batch, loss, windows, patience
//   9. System               — device, compile, bars, search, thresholds
// =============================================================================


// =============================================================================
// SECTION 1: MODEL IDENTITY
// =============================================================================

// Points to an architecture preset. All architecture-specific #defines
// (LSTM hidden size, attention dims, dropout, etc.) are loaded from there.
// This lets you swap architectures (gold, fusion, lstm, bilstm) without
// duplicating all the feature/bar/target settings here.
// This root config supplies everything except the neural-net architecture itself.
#define ARCHITECTURE_CONFIG "symbols/xauusd/config/gold.config"

// Path to the raw tick CSV exported from MT5.
// Must match SYMBOL. Export with: python export_data.py --symbol xauusd
#define DATA_FILE "data/XAUUSD/ticks.csv"

// Base name for the archived model folder and ONNX file.
// Archive lands in: symbols/xauusd/models/<date>-<time>__<MODEL_NAME>/
#define MODEL_NAME "au"

// MT5 symbol this model trades. Must match the ticks in DATA_FILE.
#define SYMBOL "XAUUSD"


// =============================================================================
// SECTION 2: FEATURE SETS + INDIVIDUAL TOGGLES
// =============================================================================
// This config uses INDIVIDUAL FEATURE TOGGLES (both preset packs are false).
// When USE_MAIN_FEATURE_SET = false and USE_MINIMAL_FEATURE_SET = false,
// every feature has its own #define FOO true/false switch.
// This gives maximum control — you can disable any single feature.
//
// The individual toggles (lines 22–69) enable all ~40 features, equivalent
// to USE_MAIN_FEATURE_SET = true but with the ability to selectively disable.
// ============================================================================
// PRE-BUILT FEATURE PACKS — only one can be active at a time.
// Both are false here because individual toggles are used instead.
//
// MAIN FEATURE SET: the full 40-feature notebook pack.
// Includes: returns, RSI, MACD, Bollinger, Donchian, ATR ratios, tick imbalance,
// SMA crossovers, spread Z-score, stochastic, SMA gaps, RV, and more.
// When enabled, individual FEATURE_* toggles are ignored (pack loaded wholesale).
#define USE_MAIN_FEATURE_SET false

// MINIMAL FEATURE SET: a compact 9-feature set for fast smoke-tests.
// Enables: ATR-relative, close-in-range, high/low relative to prev, RET1,
// RETURN_N, RV, spread-rel, tick-imbalance.
#define USE_MINIMAL_FEATURE_SET false

// GOLD CONTEXT: include USDX and USDJPY return features as market-context inputs.
// Adds 2 features (FEATURE_USDX_RET1, FEATURE_USDJPY_RET1).
// Useful for XAUUSD because gold is dollar-denominated and inversely correlated
// with the US dollar index.
#define USE_GOLD_CONTEXT true
// ============================================================================

/* INDIVIDUAL FEATURE TOGGLES (lines 22–69) ***********************************
  Each #define FOO true enables that specific feature.
  All are true here — equivalent to USE_MAIN_FEATURE_SET = true, but with
  the ability to disable individual features for ablation experiments.

  FEATURE_GROUPS:
    ATR:       FEATURE_ATR_RATIO_20, FEATURE_ATR_REL
    Bollinger: FEATURE_BOLLINGER_POS_20, FEATURE_BOLLINGER_WIDTH_20
    Donchian:  FEATURE_DONCHIAN_POS_9, FEATURE_DONCHIAN_POS_20,
               FEATURE_DONCHIAN_WIDTH_9, FEATURE_DONCHIAN_WIDTH_20
    Candle:    FEATURE_BODY_REL, FEATURE_HIGH_REL_PREV, FEATURE_LOW_REL_PREV,
               FEATURE_LOWER_WICK_REL, FEATURE_OPEN_REL_PREV,
               FEATURE_RANGE_REL, FEATURE_UPPER_WICK_REL,
               FEATURE_CLOSE_IN_RANGE
    Returns:   FEATURE_RET1, FEATURE_RET_2, FEATURE_RET_3, FEATURE_RET_6,
               FEATURE_RET_12, FEATURE_RET_20, FEATURE_RETURN_N
    RSI:       FEATURE_RSI_6, FEATURE_RSI_14
    RV:        FEATURE_RV, FEATURE_RV_18
    SMA:       FEATURE_CLOSE_REL_SMA_3, FEATURE_CLOSE_REL_SMA_9,
               FEATURE_CLOSE_REL_SMA_20, FEATURE_SMA_3_9_GAP,
               FEATURE_SMA_5_20_GAP, FEATURE_SMA_9_20_GAP,
               FEATURE_SMA_SLOPE_9, FEATURE_SMA_SLOPE_20
    Spread:    FEATURE_SPREAD_REL, FEATURE_SPREAD_Z_9
    Stochastic:FEATURE_STOCH_K_9, FEATURE_STOCH_D_3, FEATURE_STOCH_GAP
    Volume:    FEATURE_TICK_COUNT_CHG, FEATURE_TICK_COUNT_REL_9,
               FEATURE_TICK_COUNT_Z_9, FEATURE_TICK_IMBALANCE,
               FEATURE_TICK_IMBALANCE_SMA_5, FEATURE_TICK_IMBALANCE_SMA_9
    Macro:     FEATURE_USDX_RET1, FEATURE_USDJPY_RET1

  WHAT EACH FEATURE MEANS (key ones):
    ATR_REL:         current ATR / SMA(ATR, 20). >1 = more volatile than usual.
    BOLLINGER_POS:   where close sits within Bollinger Bands (0 = lower band,
                     0.5 = middle, 1 = upper band).
    BOLLINGER_WIDTH: (upper - lower band) / ATR. Normalized volatility.
    DONCHIAN_POS:    (close - donchian_low) / (donchian_high - donchian_low).
                     0 = at channel low, 1 = at channel high.
    DONCHIAN_WIDTH:  channel_range / ATR. Normalized channel width.
    BODY_REL:        candle body size / ATR. Large body = strong directional bar.
    CLOSE_IN_RANGE:  (close - low) / (high - low). 0 = close at low, 1 = at high.
    LOWER_WICK_REL:  lower wick / ATR. Long lower wick = buying pressure rejected.
    UPPER_WICK_REL:  upper wick / ATR. Long upper wick = selling pressure rejected.
    RET_N:           percent return over N bars. Negative = down, positive = up.
    RETURN_N:        log-return over RETURN_PERIOD (9) bars.
    RSI:             0 = oversold, 100 = overbought. RSI 6 is fast/noisy, 14 is smooth.
    RV:              Realized Volatility = std(log returns). Measures directional turbulence.
    SMA_GAP:         (SMA_fast - SMA_slow) / ATR. Positive = short > long = bullish.
    SMA_SLOPE:       change in SMA over SMA_SLOPE_SHIFT bars / ATR. Trend direction/speed.
    SPREAD_REL:      spread / ATR. Large spread = thin market, illiquid.
    SPREAD_Z_9:      z-score of spread over last 9 bars. >2 = unusually wide spread.
    STOCH_K:         Stochastic %K (0–100). Fast, raw.
    STOCH_D:         Stochastic %D = SMA(STOCH_K, 3). Smoothed signal line.
    STOCH_GAP:       gap between %K and %D / ATR. Signals crossover strength.
    TICK_COUNT_CHG:  change in tick volume vs previous bar.
    TICK_COUNT_REL:  tick count / SMA(tick_count, 9). >1 = busier than usual.
    TICK_COUNT_Z:    z-score of tick count over last 9 bars.
    TICK_IMBALANCE:  (buys - sells) / (buys + sells) for current bar. Range [-1, +1].
                     +1 = all buys, -1 = all sells, 0 = perfectly balanced.
    TICK_IMBALANCE_SMA_5:  SMA of imbalance over 5 bars. Fast trend of imbalance.
    TICK_IMBALANCE_SMA_9:  SMA of imbalance over 9 bars. Slow trend of imbalance.
    USDX_RET1:       1-bar return of USDX (DXY). Gold is inversely correlated.
    USDJPY_RET1:     1-bar return of USDJPY. Another USD proxy for gold context.

*******************************************************************************/

#define FEATURE_ATR_RATIO_20 true
#define FEATURE_ATR_REL true
#define FEATURE_BOLLINGER_POS_20 true
#define FEATURE_BOLLINGER_WIDTH_20 true
#define FEATURE_BODY_REL true
#define FEATURE_CLOSE_IN_RANGE true
#define FEATURE_CLOSE_REL_SMA_20 true
#define FEATURE_CLOSE_REL_SMA_3 true
#define FEATURE_CLOSE_REL_SMA_9 true
#define FEATURE_DONCHIAN_POS_20 true
#define FEATURE_DONCHIAN_POS_9 true
#define FEATURE_DONCHIAN_WIDTH_20 true
#define FEATURE_DONCHIAN_WIDTH_9 true
#define FEATURE_HIGH_REL_PREV true
#define FEATURE_LOWER_WICK_REL true
#define FEATURE_LOW_REL_PREV true
#define FEATURE_OPEN_REL_PREV true
#define FEATURE_RANGE_REL true
#define FEATURE_RET1 true
#define FEATURE_RET_12 true
#define FEATURE_RET_2 true
#define FEATURE_RET_20 true
#define FEATURE_RET_3 true
#define FEATURE_RET_6 true
#define FEATURE_RETURN_N true
#define FEATURE_RSI_14 true
#define FEATURE_RSI_6 true
#define FEATURE_RV true
#define FEATURE_RV_18 true
#define FEATURE_SMA_3_9_GAP true
#define FEATURE_SMA_5_20_GAP true
#define FEATURE_SMA_9_20_GAP true
#define FEATURE_SMA_SLOPE_20 true
#define FEATURE_SMA_SLOPE_9 true
#define FEATURE_SPREAD_REL true
#define FEATURE_SPREAD_Z_9 true
#define FEATURE_STOCH_D_3 true
#define FEATURE_STOCH_GAP true
#define FEATURE_STOCH_K_9 true
#define FEATURE_TICK_COUNT_CHG true
#define FEATURE_TICK_COUNT_REL_9 true
#define FEATURE_TICK_COUNT_Z_9 true
#define FEATURE_TICK_IMBALANCE true
#define FEATURE_TICK_IMBALANCE_SMA_5 true
#define FEATURE_TICK_IMBALANCE_SMA_9 true
#define FEATURE_UPPER_WICK_REL true
#define FEATURE_USDJPY_RET1 true
#define FEATURE_USDX_RET1 true


// =============================================================================
// SECTION 3: BAR CONSTRUCTION
// =============================================================================
// Raw ticks are grouped into OHLCV "bars" before features are computed.
// The system supports three bar modes:
//   - FIXED TICK BARS  (used here): every bar has exactly N ticks, regardless
//     of price movement. Simple, predictable, but ignores market microstructure.
//   - IMBALANCE BARS: bars close when directional pressure accumulates past a
//     threshold. More bars during trends, fewer during chop.
//   - FIXED TIME BARS: every bar has a fixed time duration.
//
// This config uses FIXED TICK BARS with 27 ticks per bar (PRIMARY_TICK_DENSITY 27).
// Imbalance bar parameters are still present (for cross-compatibility) but are
// ignored because USE_FIXED_TICK_BARS = true.
/* FIXED TICK BARS vs IMBALANCE BARS ******************************************

  FIXED TICK BARS (this config):
    - Every bar closes after exactly PRIMARY_TICK_DENSITY ticks.
    - Bars ignore whether the market is trending or choppy.
    - In slow markets, bars are full of ticks; in fast markets, bars arrive quickly.
    - Simple to reason about: 144 bars = 144 * 27 = 3,888 ticks of history.
    - Good for: stable, liquid markets; when you want predictable bar counts.

  IMBALANCE BARS (au.config uses these):
    - Bar closes when |buys - sells| exceeds a threshold.
    - Threshold adapts via EMA of recent bar imbalances.
    - More bars form during directional moves, fewer during consolidation.
    - Better at capturing regime changes — the bar structure itself encodes momentum.
    - Good for: choppy/volatile markets; when bar quality matters more than count.

  IMBALANCE PARAMETERS (present but unused when USE_FIXED_TICK_BARS = true):

    IMBALANCE_EMA_SPAN = 3
    ------------------------
    EMA smoothing window for adaptive imbalance threshold.
    Higher = smoother threshold, lower = more responsive.

    IMBALANCE_MIN_TICKS = 3
    ------------------------
    Floor on imbalance magnitude. Bar needs at least |3| imbalance to close.
    With USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD = true, effective floor = 1.

    PRIMARY_BAR_SECONDS = 9
    ------------------------
    Force-close any open bar after 9 seconds if no threshold met.
    Safety valve — rarely triggers with fixed tick bars since bars always close
    after exactly 27 ticks.

    USE_IMBALANCE_EMA_THRESHOLD = true
    USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD = true
    -----------------------------------------------
    These adapt the imbalance threshold but are bypassed when
    USE_FIXED_TICK_BARS = true.

    USE_SECOND_BARS = false
    ------------------------
    false = only primary bars. true = also build time-based secondary bars.

*******************************************************************************/

#define IMBALANCE_EMA_SPAN 3
#define IMBALANCE_MIN_TICKS 3
#define PRIMARY_BAR_SECONDS 9
#define PRIMARY_TICK_DENSITY 27
#define USE_FIXED_TICK_BARS true
#define USE_IMBALANCE_EMA_THRESHOLD true
#define USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD true
#define USE_SECOND_BARS false


// =============================================================================
// SECTION 4: FEATURE PERIODS
// =============================================================================
// All indicators use these lookback windows. Periods are tuned for XAUUSD:
//   - Fast (2–9): micro-momentum, short-term reversals
//   - Medium (12–20): swing-level, mean reversion zones
//   - Long (27–144): trend, macro regime
// These override any defaults in the architecture config (gold.config).
/* MAIN INDICATOR PERIODS ******************************************************

  FEATURE_ATR_PERIOD = 9
  ----------------------
  ATR (Average True Range) lookback for the main ATR feature.
  ATR = max(high-last_close, high-low, last_close-low) averaged over 9 bars.
  Measures typical XAUUSD movement per bar.

  FEATURE_ATR_RATIO_PERIOD = 20
  -----------------------------
  ATR ratio = ATR(9) / ATR(20). >1 = more volatile now than the 20-bar average.

  FEATURE_BOLLINGER_PERIOD = 20
  -----------------------------
  Standard deviation window for Bollinger Bands. Classic academic setting.
  Band distance = 2 * stddev(close, 20).

  FEATURE_DONCHIAN_FAST_PERIOD = 9
  FEATURE_DONCHIAN_SLOW_PERIOD = 20
  ---------------------------------
  Donchian Channel windows: highest high and lowest low over N bars.
  Fast = 9 bars (short-term extremes), Slow = 20 bars (medium-term extremes).

  FEATURE_RET_2_PERIOD = 2   → return over 2 bars (micro-momentum)
  FEATURE_RET_3_PERIOD = 3   → return over 3 bars
  FEATURE_RET_6_PERIOD = 6   → return over 6 bars
  FEATURE_RET_12_PERIOD = 12 → return over 12 bars
  FEATURE_RET_20_PERIOD = 20 → return over 20 bars (swing bias)

  FEATURE_RSI_FAST_PERIOD = 6
  FEATURE_RSI_SLOW_PERIOD = 14
  -----------------------------
  RSI windows. RSI = 100 - (100 / (1 + RS)), where RS = avg gain / avg loss.
  RSI 6 = fast, reactive, noisy. RSI 14 = classic, smoother.

  FEATURE_RV_LONG_PERIOD = 18
  ---------------------------
  Realized Volatility: stddev of log-returns over 18 bars.
  Unlike ATR (which is max-range based), RV captures directional turbulence.

  FEATURE_SMA_FAST_PERIOD = 3
  FEATURE_SMA_MID_PERIOD = 9
  FEATURE_SMA_SLOW_PERIOD = 20
  -------------------------------
  Simple Moving Average windows. Used for SMA gaps, price-relative, and slope.

  FEATURE_SMA_SLOPE_SHIFT = 3
  ---------------------------
  Before computing SMA slope, shift the SMA series by 3 bars.
  This smooths out the slope signal and avoids reacting to every tiny wiggle.

  FEATURE_SMA_TREND_FAST_PERIOD = 5
  ----------------------------------
  A dedicated 5-bar SMA for the trend-direction feature
  (e.g., "is price above or below its 5-bar SMA?").

  FEATURE_SPREAD_Z_PERIOD = 9
  ---------------------------
  Z-score window for spread normalization. Detects unusually wide/narrow spreads.

  FEATURE_STOCH_PERIOD = 9
  FEATURE_STOCH_SMOOTH_PERIOD = 3
  -------------------------------
  Stochastic %K window = 9 bars. %D = SMA(%K, 3).
  %K = (close - lowest_low_9) / (highest_high_9 - lowest_low_9) * 100.

  FEATURE_TICK_COUNT_PERIOD = 9
  FEATURE_TICK_IMBALANCE_FAST_PERIOD = 5
  FEATURE_TICK_IMBALANCE_SLOW_PERIOD = 9
  ------------------------------------
  Volume-related lookback windows. 9 for tick count, 5/9 for imbalance SMAs.

  RETURN_PERIOD = 9
  RV_PERIOD = 9
  ----------------
  Default lookback for RETURN_N and RV features (not individually named above).

  FEATURE_MAIN_SHORT_PERIOD = 9
  FEATURE_MAIN_MEDIUM_PERIOD = 18
  FEATURE_MAIN_LONG_PERIOD = 27
  FEATURE_MAIN_XLONG_PERIOD = 54
  FEATURE_MAIN_XXLONG_PERIOD = 144
  ----------------------------------
  Multi-timeframe SMA sequence for the main feature pack.
  9/18/27/54/144 is a geometric progression (~2x each step).
  Each captures a different trend horizon simultaneously.

  FEATURE_MACD_FAST_PERIOD = 12
  FEATURE_MACD_SLOW_PERIOD = 26
  FEATURE_MACD_SIGNAL_PERIOD = 9
  ----------------------------------
  MACD = EMA(close, 12) - EMA(close, 26).
  Signal = EMA(MACD, 9). Classic settings from Gerald Appel's original paper.

*******************************************************************************/

#define FEATURE_ATR_PERIOD 9
#define FEATURE_ATR_RATIO_PERIOD 20
#define FEATURE_BOLLINGER_PERIOD 20
#define FEATURE_DONCHIAN_FAST_PERIOD 9
#define FEATURE_DONCHIAN_SLOW_PERIOD 20
#define FEATURE_RET_12_PERIOD 12
#define FEATURE_RET_20_PERIOD 20
#define FEATURE_RET_2_PERIOD 2
#define FEATURE_RET_3_PERIOD 3
#define FEATURE_RET_6_PERIOD 6
#define FEATURE_RSI_FAST_PERIOD 6
#define FEATURE_RSI_SLOW_PERIOD 14
#define FEATURE_RV_LONG_PERIOD 18
#define FEATURE_SMA_FAST_PERIOD 3
#define FEATURE_SMA_MID_PERIOD 9
#define FEATURE_SMA_SLOPE_SHIFT 3
#define FEATURE_SMA_SLOW_PERIOD 20
#define FEATURE_SMA_TREND_FAST_PERIOD 5
#define FEATURE_SPREAD_Z_PERIOD 9
#define FEATURE_STOCH_PERIOD 9
#define FEATURE_STOCH_SMOOTH_PERIOD 3
#define FEATURE_TICK_COUNT_PERIOD 9
#define FEATURE_TICK_IMBALANCE_FAST_PERIOD 5
#define FEATURE_TICK_IMBALANCE_SLOW_PERIOD 9
#define FEATURE_MAIN_SHORT_PERIOD 9
#define FEATURE_MAIN_MEDIUM_PERIOD 18
#define FEATURE_MAIN_LONG_PERIOD 27
#define FEATURE_MAIN_XLONG_PERIOD 54
#define FEATURE_MAIN_XXLONG_PERIOD 144
#define FEATURE_MACD_FAST_PERIOD 12
#define FEATURE_MACD_SLOW_PERIOD 26
#define FEATURE_MACD_SIGNAL_PERIOD 9
#define RETURN_PERIOD 9
#define RV_PERIOD 9


// =============================================================================
// SECTION 5: TARGET & LABELS
// =============================================================================
// How training labels (buy / sell / hold) are constructed.
// This config uses FIXED targets, not ATR-based targets.
/* LABEL PARAMETERS ************************************************************

  DEFAULT_FIXED_MOVE = 1440
  ---------------------------
  Point size for FIXED TARGETS mode. 1440 points on XAUUSD ≈ $1.44 at 5-decimal.
  Used for both label computation and as the live SL/TP base when
  USE_FIXED_TARGETS = true.

  LABEL_SL_MULTIPLIER = 0.54
  LABEL_TP_MULTIPLIER = 0.54
  -----------------------------
  Training label multipliers. Applied to DEFAULT_FIXED_MOVE:
    SL = 1440 * 0.54 = 777.6 points
    TP = 1440 * 0.54 = 777.6 points
  
  Equal SL and TP (both 0.54) makes the label symmetric.
  0.54 is tight — appropriate for the short 3-bar horizon.

  SEQ_LEN = 144
  -------------
  Context window: how many bars the model sees as input.
  144 bars * 27 ticks/bar = 3,888 ticks of history.
  More bars = richer context but higher memory and compute cost.

  TARGET_ATR_PERIOD = 9
  ----------------------
  ATR lookback used ONLY for computing the target SL/TP distances.
  Separated from FEATURE_ATR_PERIOD (9) for independent tuning.
  Here it matches FEATURE_ATR_PERIOD = 9 for simplicity.

  TARGET_HORIZON = 3
  ------------------
  How many bars ahead the model must predict.
  The label is computed at bar 3's close by checking which boundary was hit first:
    BUY:  TP hit at bar 3 before SL
    SELL: SL hit at bar 3 before TP
    HOLD: Neither SL nor TP hit by bar 3 close
  
  Short horizon (3): fast reactions, more trades, more noise.
  Long horizon (30): patient signals, fewer trades, bigger trends needed.

  USE_FIXED_TARGETS = true
  -------------------------
  true  = FIXED targets. SL = 1440 * 0.54 = 777.6 pts, TP = 777.6 pts.
          These are constant regardless of market volatility.
  false = ATR-based targets. SL = ATR(14) * LABEL_SL_MULTIPLIER.
          Adapts to market conditions. (au.config uses this mode.)

  IMPORTANT: USE_FIXED_TARGETS affects ONLY label computation.
             Live trade execution uses DEFAULT_SL_MULTIPLIER / DEFAULT_TP_MULTIPLIER
             (SECTION 6) and the confidence search at runtime.

*******************************************************************************/

#define DEFAULT_FIXED_MOVE 1440
#define LABEL_SL_MULTIPLIER 0.54
#define LABEL_TP_MULTIPLIER 0.54
#define SEQ_LEN 144
#define TARGET_ATR_PERIOD 9
#define TARGET_HORIZON 3
#define USE_FIXED_TARGETS true


// =============================================================================
// SECTION 6: TRADE SIZING
// =============================================================================
// Parameters for live trade execution. These control how the EA interprets
// model predictions and sizes positions at runtime.
/* TRADE SIZING PARAMETERS *****************************************************

  DEFAULT_BROKER_MIN_LOT_SIZE = 0.01
  -----------------------------------
  The broker's minimum allowed lot size. Any computed lot below this is floored
  to 0.01 when USE_BROKER_MIN_LOT_SIZE = true.

  DEFAULT_LOT_SIZE = 0.54
  ----------------------
  Fixed lot size per trade when USE_RISK_PERCENT = false.
  0.54 lots on XAUUSD micro ≈ $5.40 notional per 0.01 lot at $2000/oz.
  This is ignored when USE_RISK_PERCENT = true.

  DEFAULT_LOT_SIZE_CAP = 0.54
  ---------------------------
  Maximum allowed lot size per trade. Prevents runaway sizing on winning streaks.
  Trades that exceed this are capped to this value.
  Set equal to DEFAULT_LOT_SIZE here to enforce a hard lot ceiling.

  USE_LOT_SIZE_CAP = true
  ------------------------
  true  = enforce DEFAULT_LOT_SIZE_CAP as the hard ceiling. [current]
  false = allow any lot size the broker accepts.

  DEFAULT_RISK_PERCENT = 0.00
  ---------------------------
  Fraction of account equity risked per trade (0.00 = disabled).
  0.01 = 1% risk per trade. When enabled, lot size = equity * risk_pct / SL_points.
  Disabled here (0.00) — fixed lot size always used.

  USE_RISK_PERCENT = false
  ------------------------
  false = use fixed lot size (DEFAULT_LOT_SIZE). [current]
  true  = compute lot dynamically from account equity and SL distance.

  DEFAULT_SL_MULTIPLIER = 5.4
  DEFAULT_TP_MULTIPLIER = 5.4
  -----------------------------
  Default SL and TP multipliers for LIVE trading.
  Used when the confidence search produces no valid SL/TP at runtime.
  These are multipliers on DEFAULT_FIXED_MOVE (since USE_FIXED_TARGETS = true):
    SL = 1440 * 5.4 = 7,776 points
    TP = 1440 * 5.4 = 7,776 points
  
  NOTE: These are DIFFERENT from LABEL_SL/TP_MULTIPLIER (SECTION 5).
        Label multipliers control what the model learns.
        Default multipliers control how trades are executed if the
        confidence search finds no valid parameters.

  USE_BROKER_MIN_LOT_SIZE = false
  ---------------------------------
  false = always use DEFAULT_LOT_SIZE exactly. [current]
  true  = floor lot sizes to broker minimum (DEFAULT_BROKER_MIN_LOT_SIZE).

*******************************************************************************/

#define DEFAULT_BROKER_MIN_LOT_SIZE 0.01
#define DEFAULT_LOT_SIZE 0.54
#define DEFAULT_LOT_SIZE_CAP 0.54
#define DEFAULT_RISK_PERCENT 0.00
#define DEFAULT_SL_MULTIPLIER 5.4
#define DEFAULT_TP_MULTIPLIER 5.4
#define USE_BROKER_MIN_LOT_SIZE false
#define USE_LOT_SIZE_CAP true
#define USE_RISK_PERCENT false


// =============================================================================
// SECTION 7: ARCHITECTURE
// =============================================================================
// Neural network architecture hyperparameters.
// This root config provides shared settings. Architecture-specific values
// (LSTM, Attention, TCN, etc.) are loaded from ARCHITECTURE_CONFIG = gold.config.
#define ATTENTION_DIM 128
#define ATTENTION_DROPOUT 0.10
#define ATTENTION_HEADS 4
#define ATTENTION_LAYERS 2

#define CHRONOS_BOLT_MODEL "amazon/chronos-bolt-tiny"

#define SEQUENCE_DROPOUT 0.10
#define SEQUENCE_HIDDEN_SIZE 64
#define SEQUENCE_LAYERS 2

#define TCN_KERNEL_SIZE 3
#define TCN_LEVELS 4

#define USE_MULTIHEAD_ATTENTION true


// =============================================================================
// SECTION 8: TRAINING
// =============================================================================
// All hyperparameters for training the model. Separated from architecture
// so they can be tuned independently of the model structure.
/* TRAINING PARAMETERS *********************************************************

  DEFAULT_EPOCHS = 6
  -------------------
  Maximum training epochs. This is a SHORT run (6 epochs) — likely intended
  for smoke-testing or quick iteration rather than full training.
  For production runs, increase to 54+ and rely on DEFAULT_PATIENCE for early stopping.

  DEFAULT_BATCH_SIZE = 54
  -----------------------
  Number of sequences per training step. 54 is a compromise between
  gradient stability (larger) and GPU memory (smaller).
  Must fit in DEVICE memory. "cpu" here means RAM.

  DEFAULT_LOSS_MODE = "cross-entropy"
  ----------------------------------
  Loss function for training:
    "cross-entropy" = standard classification loss. Model outputs logits
                      for buy/sell/hold and cross-entropy penalizes wrong probabilities.
                      Lower = better fit. Best for discrete directional signals.
    "auto"           = system picks the best loss for the architecture.
                      See SECTION 9 for the override (LOSS_MODE = "auto").

  DEFAULT_MAX_TRAIN_WINDOWS = 14400
  DEFAULT_MAX_EVAL_WINDOWS = 1440
  ----------------------------------
  Maximum number of sliding windows to use for training and evaluation.
  Windows are non-overlapping or stratified samples from the dataset.
  14,400 train / 1,440 eval = 90/10 split by window count.

  DEFAULT_PATIENCE = 6
  --------------------
  Epochs to wait for improvement before early stopping.
  If eval loss doesn't improve for 6 consecutive epochs, training halts.
  Combined with 6 max epochs, this is a tight budget — suitable for testing.
  For real training: patience 12+, epochs 54+.

  CONFIDENCE_SEARCH_MIN = 0.40
  CONFIDENCE_SEARCH_MAX = 0.99
  CONFIDENCE_SEARCH_STEPS = 60
  --------------------------------
  At inference time, the EA runs a grid search over confidence thresholds to
  find the optimal SL/TP distances. It tests 60 values from 0.40 to 0.99.
  Higher confidence = more selective (fewer trades, higher conviction).
  Lower confidence = more trades, more noise.
  0.40 minimum prevents the model from acting on near-random predictions.

  FOCAL_GAMMA = 2.0
  -----------------
  Focal loss gamma. Focal loss down-weights easy examples so the model
  focuses on hard/misclassified cases. Gamma = 2.0 is the standard default.
  Only used when LOSS_MODE = "auto" (which picks focal loss by default).

  DEFAULT_LOSS_MODE = "cross-entropy" (active here, overrides focal loss).

  LEARNING_RATE = 0.0
  WEIGHT_DECAY = 0.0
  USE_CUSTOM_LEARNING_RATE = false
  USE_CUSTOM_WEIGHT_DECAY = false
  ---------------------------------
  These are all zero/disabled here, meaning the system uses its own
  internal default learning rate and weight decay. Effectively the same as
  setting USE_CUSTOM_* = true with the system's recommended values.

  MINIROCKET_FEATURES = 10080
  ---------------------------
  Number of random convolutional features to generate when MiniRocket is used
  as a feature extractor (not used by the AU architecture here).

  MIN_SELECTED_TRADES = 12
  MIN_TRADE_PRECISION = 0.50
  ---------------------------
  Minimum trades and precision for a model to be considered valid.
  If fewer than 12 trades occurred during eval, the model is marked as invalid.
  Trade precision (win rate / random baseline) must exceed 0.50 (50%) or the
  model is rejected. Prevents models that overfit to noise.

*******************************************************************************/

#define CONFIDENCE_SEARCH_MAX 0.99
#define CONFIDENCE_SEARCH_MIN 0.40
#define CONFIDENCE_SEARCH_STEPS 60
#define DEFAULT_BATCH_SIZE 54
#define DEFAULT_EPOCHS 6
#define DEFAULT_LOSS_MODE "cross-entropy"
#define DEFAULT_MAX_EVAL_WINDOWS 1440
#define DEFAULT_MAX_TRAIN_WINDOWS 14400
#define DEFAULT_PATIENCE 6
#define FOCAL_GAMMA 2.0
#define LEARNING_RATE 0.0
#define LOSS_MODE "auto"
#define MINIROCKET_FEATURES 10080
#define MIN_SELECTED_TRADES 12
#define MIN_TRADE_PRECISION 0.50
#define WEIGHT_DECAY 0.0


// =============================================================================
// SECTION 9: SYSTEM
// =============================================================================
// Runtime environment, device, compilation, and miscellaneous flags.
/* SYSTEM PARAMETERS ************************************************************

  DEVICE = "cpu"
  -----------
  Compute device. "cpu" here — all training runs on CPU.
  Could be "cuda" if a GPU is available and torch is built with CUDA support.
  Switching to CUDA would massively speed up training for large models.

  MAX_BARS = 0
  ------------
  Maximum bars to process. 0 = no limit (process entire dataset).
  Set to a positive integer (e.g., 10000) to cap processing for debugging.

  METAEDITOR_PATH = ""
  ------------------
  Path to MetaEditor64.exe for live compilation. Empty = do not auto-compile
  the MQL5 expert after ONNX export. Compilation must be done manually.
  Set to a real path (e.g., "C:/Program Files/MT5/metaeditor64.exe") to
  enable auto-compile after training.

  SKIP_LIVE_COMPILE = false
  ------------------------
  false = attempt to compile live.mq5 with MetaEditor after ONNX export. [current]
  true  = skip compilation entirely. Faster export but manual compile needed.
  Requires METAEDITOR_PATH to be set to a valid path.

  USE_MAX_BARS = false
  --------------------
  false = no bar cap (process all bars). [current]
  true  = cap bars at MAX_BARS.

  USE_ALL_WINDOWS = false
  -----------------------
  false = sample windows randomly up to MAX_TRAIN_WINDOWS. [current]
  true  = use every possible window (exhaustively). Slower but thorough.

  USE_NO_HOLD = false
  -------------------
  false = 3-class labels: BUY, SELL, HOLD. [current]
  true  = same 3-class labels.
  When false, the "HOLD" class still exists but the model is trained without
  the explicit no-hold constraint (behavior may vary by loss mode).
  Set to true when you want the model to explicitly learn to abstain.

*******************************************************************************/

#define DEVICE "cpu"
#define MAX_BARS 0
#define METAEDITOR_PATH ""
#define SKIP_LIVE_COMPILE false
#define USE_ALL_WINDOWS false
#define USE_CHRONOS_AUTO_CONTEXT false
#define USE_CHRONOS_ENSEMBLE_CONTEXTS false
#define USE_CHRONOS_PATCH_ALIGNED_CONTEXT false
#define USE_CUSTOM_LEARNING_RATE false
#define USE_CUSTOM_WEIGHT_DECAY false
#define USE_MAX_BARS false
#define USE_NO_HOLD false
