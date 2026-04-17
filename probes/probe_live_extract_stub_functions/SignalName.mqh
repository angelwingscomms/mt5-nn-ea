string SignalName(int signal) {
   if(signal == 1) {
      return "BUY";
   }
   if(signal == 2) {
      return "SELL";
   }
   return "HOLD";
}
