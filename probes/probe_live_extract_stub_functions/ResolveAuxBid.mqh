double ResolveAuxBid(string symbol, bool &available, double &last_value, double fallback) {
   if(!available) {
      return (last_value > 0.0 ? last_value : fallback);
   }
   MqlTick aux;
   if(SymbolInfoTick(symbol, aux) && aux.bid > 0.0) {
      last_value = aux.bid;
      return aux.bid;
   }
   available = false;
   return (last_value > 0.0 ? last_value : fallback);
}
