void PrintRunSummary() {
   Print(
      StringFormat(
         "[SUMMARY] bar_mode=%s risk_mode=%s fixed_move=%.2f risk_pct=%.3f predictions=%d hold_skips=%d confidence_skips=%d position_skips=%d stops_too_close=%d volume_skips=%d open_failures=%d trades_opened=%d trades_closed=%d wins=%d losses=%d realized_pnl=%.2f balance=%.2f",
         (MODEL_USE_FIXED_TICK_BARS != 0 ? "FIXED_TICK" : (MODEL_USE_FIXED_TIME_BARS != 0 ? "FIXED_TIME" : "IMBALANCE")),
         (R ? "FIXED" : "ATR"),
         FIXED_MOVE,
         RISK_PERCENT,
         prediction_count,
         hold_skip_count,
         confidence_skip_count,
         position_skip_count,
         stops_too_close_skip_count,
         volume_skip_count,
         trade_open_failed_count,
         trades_opened_count,
         closed_trade_count,
         closed_win_count,
         closed_loss_count,
         realized_pnl,
         AccountInfoDouble(ACCOUNT_BALANCE)
      )
   );
}
