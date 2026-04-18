void UpdateIndicators(Bar &bar) {
   Bar prev = history[0];
   double tr = (warmup_count == 0)
      ? (bar.h - bar.l)
      : MathMax(bar.h - bar.l, MathMax(MathAbs(bar.h - prev.c), MathAbs(bar.l - prev.c)));
   int next_count = warmup_count + 1;

   if(next_count <= FEATURE_ATR_PERIOD) {
      warmup_sum_feature += tr;
      bar.atr_feature = warmup_sum_feature / next_count;
   } else {
      double prev_atr_feature = (prev.atr_feature > 0.0 ? prev.atr_feature : tr);
      bar.atr_feature = prev_atr_feature + (tr - prev_atr_feature) / FEATURE_ATR_PERIOD;
   }

   if(next_count <= TARGET_ATR_PERIOD) {
      warmup_sum_trade += tr;
      bar.atr_trade = warmup_sum_trade / next_count;
   } else {
      double prev_atr_trade = (prev.atr_trade > 0.0 ? prev.atr_trade : tr);
      bar.atr_trade = prev_atr_trade + (tr - prev_atr_trade) / TARGET_ATR_PERIOD;
   }

   warmup_count = next_count;
   bar.valid = (warmup_count >= WARMUP_BARS);
}
