double SimpleRsi(int h, int period) {
   double gain = 0.0;
   double loss = 0.0;
   for(int i = 0; i < period; i++) {
      double delta = history[h + i].c - history[h + i + 1].c;
      if(delta > 0.0) {
         gain += delta;
      } else if(delta < 0.0) {
         loss -= delta;
      }
   }
   double avg_gain = gain / period;
   double avg_loss = loss / period;
   double rs = avg_gain / (avg_loss + 1e-10);
   return (100.0 - (100.0 / (1.0 + rs)) - 50.0) / 50.0;
}
