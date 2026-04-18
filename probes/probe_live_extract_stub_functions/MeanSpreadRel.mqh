double MeanSpreadRel(int h, int window) {
   double sum = 0.0;
   for(int i = 0; i < window; i++) {
      double close = history[h + i].c;
      double spread_rel = history[h + i].spread / (close + 1e-10);
      sum += spread_rel;
   }
   return sum / window;
}
