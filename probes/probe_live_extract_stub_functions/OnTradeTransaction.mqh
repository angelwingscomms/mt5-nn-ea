void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result) {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.deal == 0) {
      return;
   }
   if(!HistoryDealSelect(trans.deal)) {
      return;
   }
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol) {
      return;
   }
   if((int)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != MAGIC_NUMBER) {
      return;
   }

   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY && entry != DEAL_ENTRY_INOUT) {
      return;
   }

   double pnl =
      HistoryDealGetDouble(trans.deal, DEAL_PROFIT) +
      HistoryDealGetDouble(trans.deal, DEAL_SWAP) +
      HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   realized_pnl += pnl;
   closed_trade_count++;
   if(pnl > 0.0) {
      closed_win_count++;
   } else if(pnl < 0.0) {
      closed_loss_count++;
   }
}
