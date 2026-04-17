void ProcessTick(MqlTick &tick, ulong bar_bucket) {
   if(tick.bid <= 0.0) {
      return;
   }

   if(!bar_started) {
      if(MODEL_USE_FIXED_TIME_BARS != 0) {
         StartBar(tick, bar_bucket);
      } else {
         StartImbalanceBar(tick);
      }
   }

   int tick_sign = UpdateTickSign(tick.bid);
   current_bar.h = MathMax(current_bar.h, tick.bid);
   current_bar.l = MathMin(current_bar.l, tick.bid);
   current_bar.c = tick.bid;
   current_bar.spread = tick.ask - tick.bid;
   current_bar.time_close_msc = tick.time_msc;
   current_bar.usdx_bid = ResolveAuxBid(USDX_SYMBOL, usdx_available, last_usdx_bid, tick.bid);
   current_bar.usdjpy_bid = ResolveAuxBid(USDJPY_SYMBOL, usdjpy_available, last_usdjpy_bid, tick.bid);
   ticks_in_bar++;
   tick_imbalance_sum += tick_sign;
   spread_sum += current_bar.spread;
}
