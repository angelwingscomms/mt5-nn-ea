double StdSpreadRel(int h, int window) {
   double mean = MeanSpreadRel(h, window);
   double var = 0.0;
   for(int i = 0; i < window; i++) {
      double close = history[h + i].c;
      double spread_rel = history[h + i].spread / (close + 1e-10);
      double diff = spread_rel - mean;
      var += diff * diff;
   }
   return MathSqrt(var / window);
}
