void CloseBar() {
   current_bar.tick_imbalance = tick_imbalance_sum / MathMax(1, ticks_in_bar);
   current_bar.tick_count = ticks_in_bar;
   UpdateIndicators(current_bar);

   for(int i = HISTORY_SIZE - 1; i > 0; i--) {
      history[i] = history[i - 1];
   }
   history[0] = current_bar;

   ticks_in_bar = 0;
   tick_imbalance_sum = 0.0;
   current_bar_bucket = 0;
   bar_started = false;
}
