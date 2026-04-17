double MaxHigh(int h, int window) {
   double maxv = history[h].h;
   for(int i = 1; i < window; i++) {
      maxv = MathMax(maxv, history[h + i].h);
   }
   return maxv;
}
