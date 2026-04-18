void UpdatePrimaryImbalanceThreshold(double observed_abs_theta) {
   if(observed_abs_theta <= 0.0 || !USE_IMBALANCE_EMA_THRESHOLD) {
      return;
   }

   double alpha = 2.0 / (MathMax(1, IMBALANCE_EMA_SPAN) + 1.0);
   double observed = MathMax(2.0, observed_abs_theta);
   primary_expected_abs_theta = (1.0 - alpha) * primary_expected_abs_theta + alpha * observed;
}
