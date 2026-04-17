double StochK(int h, int period) {
   double high = MaxHigh(h, period);
   double low = MinLow(h, period);
   return (history[h].c - low) / (high - low + 1e-10);
}
