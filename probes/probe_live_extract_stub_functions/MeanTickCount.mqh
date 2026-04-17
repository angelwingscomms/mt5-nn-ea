double MeanTickCount(int h, int window) {
   double sum = 0.0;
   for(int i = 0; i < window; i++) {
      sum += history[h + i].tick_count;
   }
   return sum / window;
}
