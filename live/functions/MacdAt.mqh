void MacdAt(int h, double &line, double &signal, double &hist) {
   int oldest = MathMin(REQUIRED_HISTORY_INDEX, h + FEATURE_MACD_SLOW_PERIOD + FEATURE_MACD_SIGNAL_PERIOD - 2);
   double fast_alpha = 2.0 / (FEATURE_MACD_FAST_PERIOD + 1.0);
   double slow_alpha = 2.0 / (FEATURE_MACD_SLOW_PERIOD + 1.0);
   double signal_alpha = 2.0 / (FEATURE_MACD_SIGNAL_PERIOD + 1.0);
   double fast_ema = history[oldest].c;
   double slow_ema = history[oldest].c;
   double signal_ema = 0.0;
   bool signal_ready = false;

   for(int i = oldest; i >= h; i--) {
      if(i != oldest) {
         fast_ema = fast_alpha * history[i].c + (1.0 - fast_alpha) * fast_ema;
         slow_ema = slow_alpha * history[i].c + (1.0 - slow_alpha) * slow_ema;
      }
      double current_line = fast_ema - slow_ema;
      if(!signal_ready) {
         signal_ema = current_line;
         signal_ready = true;
      } else {
         signal_ema = signal_alpha * current_line + (1.0 - signal_alpha) * signal_ema;
      }
      if(i == h) {
         line = current_line;
         signal = signal_ema;
         hist = current_line - signal_ema;
         return;
      }
   }

   line = 0.0;
   signal = 0.0;
   hist = 0.0;
}
