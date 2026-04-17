double StdClose(int h, int window) {
   double mean = MeanClose(h, window);
   double var = 0.0;
   for(int i = 0; i < window; i++) {
      double diff = history[h + i].c - mean;
      var += diff * diff;
   }
   return MathSqrt(var / window);
}
