# Model Diagnostics

## Run
- symbol: XAUUSD
- backend: gold-legacy-lstm-attention
- feature_profile: minimal
- feature_count: 9
- loss_mode: cross-entropy
- focal_gamma: 2.00

## Shared Config
- seq_len: 9
- target_horizon: 3
- bar_mode: FIXED_TICK
- primary_tick_density: 27
- feature_atr_period: 9
- target_atr_period: 9
- rv_period: 9
- return_period: 9
- warmup_bars: 9
- label_risk_mode: FIXED
- point_size: 0.00100000
- fixed_move_points: 1440.00
- fixed_move_price: 1.44000000
- label_sl_multiplier: 0.54
- label_tp_multiplier: 0.54
- execution_sl_multiplier: 5.40
- execution_tp_multiplier: 5.40
- use_all_windows: 0
- selected_primary_confidence: 0.5000
- deployed_primary_confidence: 0.5000
- quality_gate_passed: 0
- quality_gate_reason: validation selected-trade precision 0.4407 < required 0.5000

## Bar Stats
- bars: 476292
- ticks_per_bar min=21.00
- ticks_per_bar p50=27.00
- ticks_per_bar p90=27.00
- ticks_per_bar p99=27.00
- ticks_per_bar mean=27.00
- ticks_per_bar max=27.00
- bar_duration_ms min=2628.00
- bar_duration_ms p50=6314.00
- bar_duration_ms p90=10248.00
- bar_duration_ms p99=17206.00
- bar_duration_ms mean=10585.74
- bar_duration_ms max=263050557.00

## Label Counts
- full bars:
  - HOLD: 283275
  - BUY: 96797
  - SELL: 96211
- train windows:
  - HOLD: 8612
  - BUY: 2927
  - SELL: 2861
- validation windows:
  - HOLD: 795
  - BUY: 325
  - SELL: 320
- holdout windows:
  - HOLD: 920
  - BUY: 266
  - SELL: 254

## Window Usage
- train_available: 333387
- train_used: 14400
- validation_available: 71422
- validation_used: 1440
- holdout_available: 71423
- holdout_used: 1440

## Validation
- selected_trades: 59
- trade_coverage: 0.0410
- selected_trade_precision: 0.4407
- selected_trade_mean_confidence: 0.5183
- mean_confidence_all_predictions: 0.4402

## Holdout
- selected_trades: 44
- trade_coverage: 0.0306
- selected_trade_precision: 0.3636
- selected_trade_mean_confidence: 0.5203
- mean_confidence_all_predictions: 0.4291

## Files
- bars.csv
- validation_predictions.csv
- holdout_predictions.csv
- validation_confusion_matrix.csv
- holdout_confusion_matrix.csv
- active_features.txt
- config.mqh

## Note
- Fixed-tick bars use PRIMARY_TICK_DENSITY in au.config to set ticks per bar.
- In ATR mode, labels use the stricter label_sl_multiplier and label_tp_multiplier values, so a BUY/SELL label means price reached the target before making more than a tiny adverse move.
- In fixed mode, labels use the same DEFAULT_FIXED_MOVE value in symbol points for both stop loss and take profit.
- When use_all_windows is 0, the trainer evenly subsamples window endpoints down to the max_train_windows and max_eval_windows caps to keep runs fast.
