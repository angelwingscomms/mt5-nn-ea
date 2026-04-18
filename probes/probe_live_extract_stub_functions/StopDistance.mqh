double StopDistance() {
   if(R) {
      return FIXED_MOVE;
   }
   return history[0].atr_trade * SL_MULTIPLIER;
}
