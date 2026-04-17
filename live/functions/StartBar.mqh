void StartBar(MqlTick &tick, ulong bar_bucket) {
   current_bar.o = tick.bid;
   current_bar.h = tick.bid;
   current_bar.l = tick.bid;
   current_bar.c = tick.bid;
   current_bar.spread = tick.ask - tick.bid;
   current_bar.spread_mean = 0.0;
   current_bar.tick_imbalance = 0.0;
   current_bar.tick_count = 0;
   current_bar.usdx_bid = 0.0;
   current_bar.usdjpy_bid = 0.0;
   current_bar.atr_feature = 0.0;
   current_bar.atr_trade = 0.0;
   current_bar.time_open_msc = tick.time_msc;
   current_bar.time_close_msc = tick.time_msc;
   current_bar.valid = false;
   ticks_in_bar = 0;
   tick_imbalance_sum = 0.0;
   spread_sum = 0.0;
   current_bar_bucket = bar_bucket;
   bar_started = true;
}
