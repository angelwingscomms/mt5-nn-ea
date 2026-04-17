string SignalName(int signal) {
   #ifdef USE_NO_HOLD
      if(signal == 0) {
         return "BUY";
      }
      return "SELL";
   #else
      if(signal == 1) {
         return "BUY";
      }
      if(signal == 2) {
         return "SELL";
      }
      return "HOLD";
   #endif
}
