void LoadHistory() {
   ulong start_time_msc = (TimeCurrent() - 86400 * 3) * 1000ULL;
   MqlTick ticks[];
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   if(copied <= 0) {
      start_time_msc = (TimeCurrent() - 86400) * 1000ULL;
      copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   }
   if(copied <= 0) {
      return;
   }

   last_tick_time = ticks[0].time_msc - 1;
   for(int i = 0; i < copied; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }

      if(MODEL_USE_FIXED_TIME_BARS != 0) {
         ulong tick_bucket = BarBucket(ticks[i].time_msc);
         int closed_tick_count = 0;
         RollFixedTimeBarIfNeeded(tick_bucket, closed_tick_count);
         ProcessTick(ticks[i], tick_bucket);
         last_tick_time = ticks[i].time_msc;
         continue;
      }

      if(MODEL_USE_FIXED_TICK_BARS != 0) {
         if(!bar_started) {
            StartImbalanceBar(ticks[i]);
         }
         ProcessTick(ticks[i], 0);
         last_tick_time = ticks[i].time_msc;
         if(ticks_in_bar >= PRIMARY_TICK_DENSITY) {
            CloseBar();
         }
         continue;
      }

      ProcessTick(ticks[i], 0);
      last_tick_time = ticks[i].time_msc;

      double observed_abs_theta = 0.0;
      if(ShouldClosePrimaryBar(observed_abs_theta)) {
         CloseBar();
         UpdatePrimaryImbalanceThreshold(observed_abs_theta);
      }
   }
}
