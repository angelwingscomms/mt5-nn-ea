bool ShouldClosePrimaryBar(double &observed_abs_theta) {
   if(ticks_in_bar < IMBALANCE_MIN_TICKS) {
      observed_abs_theta = 0.0;
      return false;
   }

   observed_abs_theta = MathAbs(tick_imbalance_sum);
   double threshold = USE_IMBALANCE_EMA_THRESHOLD
      ? primary_expected_abs_theta
      : (
         USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD
         ? MathMax(2.0, (double)MathMax(2, IMBALANCE_MIN_TICKS / 3))
         : MathMax(2.0, (double)IMBALANCE_MIN_TICKS)
      );
   return (observed_abs_theta >= threshold);
}
