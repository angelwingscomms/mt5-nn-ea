double RollingStdReturn(int h, int window) {
   double values[RV_PERIOD];
   double mean = 0.0;
   for(int i = 0; i < window; i++) {
      values[i] = LogReturnAt(h + i);
      mean += values[i];
   }
   mean /= window;

   double var = 0.0;
   for(int i = 0; i < window; i++) {
      double diff = values[i] - mean;
      var += diff * diff;
   }
   return MathSqrt(var / window);
}
