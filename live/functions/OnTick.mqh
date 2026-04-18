void OnTick() {
   MqlTick ticks[];
   int count = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, last_tick_time + 1, 100000);
   if(count <= 0) {
      return;
   }

   for(int i = 0; i < count; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }

      if(MODEL_USE_FIXED_TIME_BARS != 0) {
         ulong tick_bucket = BarBucket(ticks[i].time_msc);
         int closed_tick_count = 0;
         if(RollFixedTimeBarIfNeeded(tick_bucket, closed_tick_count)) {
            DebugPrint(
               StringFormat(
                  "bar closed mode=FIXED_TIME seconds=%d ticks=%d atr_trade=%.5f close=%.5f",
                  PRIMARY_BAR_SECONDS,
                  closed_tick_count,
                  history[0].atr_trade,
                  history[0].c
               )
            );
            if(history[REQUIRED_HISTORY_INDEX].valid) {
               Predict();
            } else {
               DebugPrint(
                  StringFormat(
                     "history not ready yet: need index %d valid before predicting",
                     REQUIRED_HISTORY_INDEX
                  )
               );
            }
         }

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
            int closed_tick_count = ticks_in_bar;
            CloseBar();
            DebugPrint(
               StringFormat(
                  "bar closed mode=FIXED_TICK ticks=%d atr_trade=%.5f close=%.5f",
                  closed_tick_count,
                  history[0].atr_trade,
                  history[0].c
               )
            );
            if(history[REQUIRED_HISTORY_INDEX].valid) {
               Predict();
            } else {
               DebugPrint(
                  StringFormat(
                     "history not ready yet: need index %d valid before predicting",
                     REQUIRED_HISTORY_INDEX
                  )
               );
            }
         }
         continue;
      }

      ProcessTick(ticks[i], 0);
      last_tick_time = ticks[i].time_msc;

      double observed_abs_theta = 0.0;
      if(ShouldClosePrimaryBar(observed_abs_theta)) {
         int closed_tick_count = ticks_in_bar;
         CloseBar();
         UpdatePrimaryImbalanceThreshold(observed_abs_theta);
         DebugPrint(
            StringFormat(
               "bar closed mode=IMBALANCE ticks=%d theta=%.2f next_threshold=%.2f atr_trade=%.5f close=%.5f",
               closed_tick_count,
               observed_abs_theta,
               primary_expected_abs_theta,
               history[0].atr_trade,
               history[0].c
            )
         );
         if(history[REQUIRED_HISTORY_INDEX].valid) {
            Predict();
         } else {
            DebugPrint(
               StringFormat(
                  "history not ready yet: need index %d valid before predicting",
                  REQUIRED_HISTORY_INDEX
               )
            );
         }
      }
   }
}
