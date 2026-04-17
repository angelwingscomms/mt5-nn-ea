double StochD(int h, int period) {
   double sum = 0.0;
   for(int i = 0; i < period; i++) {
      sum += StochK(h + i, FEATURE_STOCH_PERIOD);
   }
   return sum / period;
}
