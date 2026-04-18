# Model Diagnostics

## Run
- symbol: XAUUSD
- backend: au-lstm-mha-gap
- feature_profile: main
- feature_count: 40
- loss_mode: cross-entropy
- focal_gamma: 2.00

## Shared Config
- seq_len: 36
- target_horizon: 1
- bar_mode: FIXED_TIME
- primary_bar_seconds: 54
- feature_atr_period: 9
- target_atr_period: 14
- rv_period: 9
- return_period: 9
- warmup_bars: 144
- label_risk_mode: FIXED
- point_size: 0.00100000
- fixed_move_points: 1080.00
- fixed_move_price: 1.08000000
- label_sl_multiplier: 1.00
- label_tp_multiplier: 1.00
- execution_sl_multiplier: 0.54
- execution_tp_multiplier: 0.54
- use_all_windows: 0
- selected_primary_confidence: 0.4700
- deployed_primary_confidence: 0.4700
- quality_gate_passed: 0
- quality_gate_reason: validation selected-trade precision 0.4000 < required 0.5000

## Bar Stats
- bars: 65479
- ticks_per_bar min=1.00
- ticks_per_bar p50=203.00
- ticks_per_bar p90=263.00
- ticks_per_bar p99=281.00
- ticks_per_bar mean=196.40
- ticks_per_bar max=296.00
- bar_duration_ms min=0.00
- bar_duration_ms p50=53676.00
- bar_duration_ms p90=53880.00
- bar_duration_ms p99=53962.00
- bar_duration_ms mean=53475.76
- bar_duration_ms max=53998.00

## Label Counts
- full bars:
  - HOLD: 26996
  - BUY: 19245
  - SELL: 19094
- train windows:
  - HOLD: 7727
  - BUY: 5162
  - SELL: 5111
- validation windows:
  - HOLD: 1083
  - BUY: 938
  - SELL: 979
- holdout windows:
  - HOLD: 1200
  - BUY: 909
  - SELL: 891

## Window Usage
- train_available: 45698
- train_used: 18000
- validation_available: 9728
- validation_used: 3000
- holdout_available: 9729
- holdout_used: 3000

## Validation
- selected_trades: 15
- trade_coverage: 0.0050
- selected_trade_precision: 0.4000
- selected_trade_mean_confidence: 0.4732
- mean_confidence_all_predictions: 0.4123

## Holdout
- selected_trades: 1
- trade_coverage: 0.0003
- selected_trade_precision: 1.0000
- selected_trade_mean_confidence: 0.4726
- mean_confidence_all_predictions: 0.3973

## Files
- bars.csv
- validation_predictions.csv
- holdout_predictions.csv
- validation_confusion_matrix.csv
- holdout_confusion_matrix.csv
- active_features.txt
- config.mqh

## Note
- Bars are fixed-duration time buckets aligned to epoch time. Change PRIMARY_BAR_SECONDS in au.config to retune them.
- In ATR mode, labels use the label_sl_multiplier and label_tp_multiplier settings.
- In fixed mode, labels use DEFAULT_FIXED_MOVE for both stop loss and take profit.
- When use_all_windows is 0, the trainer evenly subsamples down to the configured train/eval caps.
