void Execute(int signal) {
   if(PositionSelect(_Symbol)) {
      position_skip_count++;
      DebugPrint("skip trade: a position is already open on this symbol");
      return;
   }

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(bid <= 0.0 || ask <= 0.0) {
      trade_open_failed_count++;
      DebugPrint(StringFormat("skip trade: invalid bid/ask bid=%.5f ask=%.5f", bid, ask));
      return;
   }

    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    double trigger_price = (signal == 1) ? bid : ask;
    double price = (signal == 1) ? ask : bid;
    double sl_distance = StopDistance();
    double tp_distance = TargetDistance();
    if(sl_distance <= 0.0 || tp_distance <= 0.0) {
       trade_open_failed_count++;
       DebugPrint(
          StringFormat(
             "skip trade: invalid risk distances sl_distance=%.5f tp_distance=%.5f",
             sl_distance,
             tp_distance
          )
       );
       return;
    }
    double sl = (signal == 1)
       ? (trigger_price - sl_distance)
       : (trigger_price + sl_distance);
    double tp = (signal == 1)
       ? (trigger_price + tp_distance)
       : (trigger_price - tp_distance);
    price = NormalizeDouble(price, digits);
    sl = NormalizeDouble(sl, digits);
    tp = NormalizeDouble(tp, digits);

    double min_stop_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
    double freeze_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL) * point;
    double min_dist = MathMax(min_stop_dist, freeze_dist);
   double sl_gap = (signal == 1) ? (trigger_price - sl) : (sl - trigger_price);
   double tp_gap = (signal == 1) ? (tp - trigger_price) : (trigger_price - tp);
   if(sl_gap < min_dist || tp_gap < min_dist) {
      stops_too_close_skip_count++;
      DebugPrint(
         StringFormat(
            "skip trade: stops too close bid=%.5f ask=%.5f price=%.5f trigger=%.5f sl=%.5f tp=%.5f sl_gap=%.5f tp_gap=%.5f min_dist=%.5f",
            bid,
            ask,
            price,
            trigger_price,
            sl,
            tp,
            sl_gap,
            tp_gap,
            min_dist
         )
      );
      return;
   }

   double volume = CalculateTradeVolume(signal, price, sl);
   DebugPrint(
      StringFormat(
         "risk_pct=%.3f lot_cap=%.2f use_risk_pct=%s use_broker_min_lot=%s",
         RISK_PERCENT,
         LOT_SIZE_CAP,
         (USE_RISK_PERCENT_INPUT ? "true" : "false"),
         (USE_BROKER_MIN_LOT ? "true" : "false")
      )
   );
   if(volume <= 0.0) {
      volume_skip_count++;
      DebugPrint(
         StringFormat(
            "skip trade: no valid volume price=%.5f sl=%.5f risk_pct=%.3f lot_cap=%.2f",
            price,
            sl,
            RISK_PERCENT,
            LOT_SIZE_CAP
         )
      );
      return;
   }

   double sl_pct_change = (sl - price) / price * 100.0;
   double tp_pct_change = (tp - price) / price * 100.0;
   DebugPrint(
      StringFormat(
         "Intent to place trade: volume=%.2f sl=%.5f tp=%.5f sl_pct_change=%.3f%% tp_pct_change=%.3f%%",
         volume,
         sl,
         tp,
         sl_pct_change,
         tp_pct_change
      )
   );

   bool opened = trade.PositionOpen(_Symbol, (signal == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL), volume, price, sl, tp);
   if(opened) {
      trades_opened_count++;
      DebugPrint(
         StringFormat(
            "trade opened %s lot=%.2f price=%.5f sl=%.5f tp=%.5f",
            SignalName(signal),
            volume,
            price,
            sl,
            tp
         )
      );
   } else {
      trade_open_failed_count++;
      DebugPrint(
         StringFormat(
            "trade open failed %s retcode=%d last_error=%d",
            SignalName(signal),
            trade.ResultRetcode(),
            GetLastError()
         )
      );
   }
}
