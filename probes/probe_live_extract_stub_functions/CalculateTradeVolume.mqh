double CalculateTradeVolume(int signal, double price, double sl) {
   if(!USE_RISK_PERCENT_INPUT) {
      return NormalizeVolume(LOT_SIZE);
   }

   double risk_amount = AccountInfoDouble(ACCOUNT_BALANCE) * (RISK_PERCENT / 100.0);
   if(risk_amount <= 0.0) {
      return 0.0;
   }

   double one_lot_pnl = 0.0;
   ENUM_ORDER_TYPE order_type = (signal == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(order_type, _Symbol, 1.0, price, sl, one_lot_pnl)) {
      DebugPrint(
         StringFormat(
            "skip trade: OrderCalcProfit failed retcode=%d last_error=%d",
            trade.ResultRetcode(),
            GetLastError()
         )
      );
      return 0.0;
   }

   double one_lot_loss = MathAbs(one_lot_pnl);
   if(one_lot_loss <= 0.0) {
      return 0.0;
   }

   double volume = risk_amount / one_lot_loss;
   if(USE_LOT_SIZE_CAP_INPUT) {
      double manual_cap = NormalizeVolume(LOT_SIZE_CAP);
      if(manual_cap > 0.0) {
         volume = MathMin(volume, manual_cap);
      }
   }
   return NormalizeVolume(volume);
}
