double ResolveImbalanceThresholdBase() {
   if(USE_IMBALANCE_EMA_THRESHOLD || !USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD) {
      return MathMax(2.0, (double)IMBALANCE_MIN_TICKS);
   }
   return MathMax(2.0, (double)MathMax(2, IMBALANCE_MIN_TICKS / 3));
}
