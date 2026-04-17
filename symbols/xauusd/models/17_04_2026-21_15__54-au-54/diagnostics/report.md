# Model Diagnostics

## Run
- symbol: XAUUSD
- backend: au-lstm-mha-gap
- feature_profile: minimal
- feature_count: 9
- loss_mode: cross-entropy
- focal_gamma: 2.00

## Shared Config
- seq_len: 36
- target_horizon: 9
- bar_mode: IMBALANCE
- imbalance_min_ticks: 9
- imbalance_ema_span: 9
- feature_atr_period: 9
- target_atr_period: 18
- rv_period: 9
- return_period: 9
- warmup_bars: 9
- label_risk_mode: FIXED
- point_size: 0.00100000
- fixed_move_points: 1080.00
- fixed_move_price: 1.08000000
- label_sl_multiplier: 1.00
- label_tp_multiplier: 1.00
- execution_sl_multiplier: 0.54
- execution_tp_multiplier: 0.54
- use_all_windows: 0
- selected_primary_confidence: 0.5500
- deployed_primary_confidence: 0.5500
- quality_gate_passed: 1
- quality_gate_reason: -

## Bar Stats
- bars: 242525
- ticks_per_bar min=9.00
- ticks_per_bar p50=39.00
- ticks_per_bar p90=109.00
- ticks_per_bar p99=213.00
- ticks_per_bar mean=53.02
- ticks_per_bar max=621.00
- bar_duration_ms min=1203.00
- bar_duration_ms p50=10195.00
- bar_duration_ms p90=30131.00
- bar_duration_ms p99=65367.28
- bar_duration_ms mean=21038.76
- bar_duration_ms max=263070642.00

## Label Counts
- full bars:
  - BUY: 37401
  - SELL: 101987
- train windows:
  - BUY: 7511
  - SELL: 7603
- validation windows:
  - BUY: 1261
  - SELL: 1326
- holdout windows:
  - BUY: 1250
  - SELL: 1266

## Window Usage
- train_available: 169717
- train_used: 18000
- validation_available: 36297
- validation_used: 3000
- holdout_available: 36298
- holdout_used: 3000

## Validation
- selected_trades: 72
- trade_coverage: 0.0278
- selected_trade_precision: 0.5833
- selected_trade_mean_confidence: 0.5597
- mean_confidence_all_predictions: 0.5177

## Holdout
- selected_trades: 56
- trade_coverage: 0.0223
- selected_trade_precision: 0.4643
- selected_trade_mean_confidence: 0.5611
- mean_confidence_all_predictions: 0.5196

## Files
- bars.csv
- validation_predictions.csv
- holdout_predictions.csv
- validation_confusion_matrix.csv
- holdout_confusion_matrix.csv
- active_features.txt
- config.mqh

## Note
- Imbalance bars are variable by design. Lower imbalance thresholds make smaller bars on average.
- In ATR mode, labels use the label_sl_multiplier and label_tp_multiplier settings.
- In fixed mode, labels use DEFAULT_FIXED_MOVE for both stop loss and take profit.
- When use_all_windows is 0, the trainer evenly subsamples down to the configured train/eval caps.
