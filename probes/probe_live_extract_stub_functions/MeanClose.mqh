double MeanClose(int h, int window) {
   double sum = 0.0;
   for(int i = 0; i < window; i++) {
      sum += history[h + i].c;
   }
   return sum / window;
}
