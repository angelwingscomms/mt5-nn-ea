double MinLow(int h, int window) {
   double minv = history[h].l;
   for(int i = 1; i < window; i++) {
      minv = MathMin(minv, history[h + i].l);
   }
   return minv;
}
