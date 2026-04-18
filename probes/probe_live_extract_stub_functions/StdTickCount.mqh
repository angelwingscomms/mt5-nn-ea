double StdTickCount(int h, int window) {
   double mean = MeanTickCount(h, window);
   double var = 0.0;
   for(int i = 0; i < window; i++) {
      double diff = history[h + i].tick_count - mean;
      var += diff * diff;
   }
   return MathSqrt(var / window);
}
