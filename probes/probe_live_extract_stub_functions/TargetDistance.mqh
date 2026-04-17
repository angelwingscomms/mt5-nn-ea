double TargetDistance() {
   if(R) {
      return FIXED_MOVE;
   }
   return history[0].atr_trade * TP_MULTIPLIER;
}
