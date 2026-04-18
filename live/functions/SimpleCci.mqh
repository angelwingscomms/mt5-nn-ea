double SimpleCci(int h, int period) {
   double typicals[512];
   double mean = 0.0;
   for(int i = 0; i < period; i++) {
      typicals[i] = TypicalPrice(h + i);
      mean += typicals[i];
   }
   mean /= period;

   double mean_deviation = 0.0;
   for(int i = 0; i < period; i++) {
      mean_deviation += MathAbs(typicals[i] - mean);
   }
   mean_deviation /= period;
   return (typicals[0] - mean) / (0.015 * (mean_deviation + 1e-10));
}
