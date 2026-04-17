double SimpleAtr(int h, int period) {
   double sum = 0.0;
   for(int i = 0; i < period; i++) {
      sum += TrueRangeAt(h + i);
   }
   return sum / period;
}
