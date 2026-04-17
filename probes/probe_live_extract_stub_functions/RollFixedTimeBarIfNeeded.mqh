bool RollFixedTimeBarIfNeeded(ulong next_bar_bucket, int &closed_tick_count) {
   closed_tick_count = 0;
   if(!bar_started || next_bar_bucket == current_bar_bucket) {
      return false;
   }

   closed_tick_count = ticks_in_bar;
   CloseBar();
   return true;
}
