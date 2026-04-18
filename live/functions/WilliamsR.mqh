double WilliamsR(int h, int period) {
   double high = MaxHigh(h, period);
   double low = MinLow(h, period);
   return -100.0 * (high - history[h].c) / (high - low + 1e-10);
}
