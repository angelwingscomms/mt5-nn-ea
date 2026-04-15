// Single source of truth for values shared by nn.py, live.mq5, data.mq5, and test.py.
#define SYMBOL "XAUUSD"

// === Basic Config ===
#define SEQ_LEN 54
#define TARGET_HORIZON 3

// === Feature Layout ===
#define MODEL_FEATURE_COUNT 9
#define FEATURE_IDX_RET1 0
#define FEATURE_IDX_HIGH_REL_PREV 1
#define FEATURE_IDX_LOW_REL_PREV 2
#define FEATURE_IDX_SPREAD_REL 3
#define FEATURE_IDX_CLOSE_IN_RANGE 4
#define FEATURE_IDX_ATR_REL 5
#define FEATURE_IDX_RV 6
#define FEATURE_IDX_RETURN_N 7
#define FEATURE_IDX_TICK_IMBALANCE 8

// === Period Settings ===
#define FEATURE_ATR_PERIOD 9
#define RV_PERIOD 9
#define RETURN_PERIOD 9
#define TARGET_ATR_PERIOD 9

// === History ===
#define MAX_FEATURE_LOOKBACK 22
#define REQUIRED_HISTORY_INDEX (SEQ_LEN + MAX_FEATURE_LOOKBACK - 1)
#define WARMUP_BARS 22

// === Bar Mode ===
#define IMBALANCE_EMA_SPAN 3
#define IMBALANCE_MIN_TICKS 3
// Fixed-time bars are optional and only used when nn.py runs with -i.
#define PRIMARY_BAR_SECONDS 9
// Fixed-tick bars are optional and only used when nn.py runs with --use-fixed-tick-bars or -gold.
#define PRIMARY_TICK_DENSITY 27

// === Risk ===
#define DEFAULT_FIXED_MOVE 144
#define DEFAULT_RISK_PERCENT 0.00

// === Training Labels ===
#define LABEL_SL_MULTIPLIER 5.4
#define LABEL_TP_MULTIPLIER 5.4

// === Live Execution ===
#define DEFAULT_LOT_MIN 0.54
#define DEFAULT_LOT_SIZE 0.54
#define DEFAULT_SL_MULTIPLIER 5.4
#define DEFAULT_TP_MULTIPLIER 5.4

// === Trainer ===
#define DEFAULT_BATCH_SIZE 54
#define DEFAULT_EPOCHS 144
#define DEFAULT_LOSS_MODE "cross-entropy"
#define DEFAULT_MAX_EVAL_WINDOWS 1440
#define DEFAULT_MAX_TRAIN_WINDOWS 14400
#define DEFAULT_PATIENCE 144
#define USE_ALL_WINDOWS 0