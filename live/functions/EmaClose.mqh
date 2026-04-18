double EmaClose(int h, int period) {
   int oldest = MathMin(REQUIRED_HISTORY_INDEX, h + period - 1);
   double alpha = 2.0 / (period + 1.0);
   double ema = history[oldest].c;
   for(int i = oldest - 1; i >= h; i--) {
      ema = alpha * history[i].c + (1.0 - alpha) * ema;
   }
   return ema;
}
