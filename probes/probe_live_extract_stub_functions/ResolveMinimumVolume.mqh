double ResolveMinimumVolume() {
   double fallback_min_volume = BROKER_MIN_LOT_SIZE;
   if(fallback_min_volume <= 0.0) {
      Print("[WARN] BROKER_MIN_LOT_SIZE is <= 0. Falling back to 0.01 lots.");
      fallback_min_volume = 0.01;
   }

   if(!USE_BROKER_MIN_LOT) {
      return fallback_min_volume;
   }

   double broker_min_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(broker_min_volume > 0.0) {
      return broker_min_volume;
   }

   Print(
      StringFormat(
         "[WARN] SYMBOL_VOLUME_MIN lookup failed or returned %.8f. Falling back to %.8f.",
         broker_min_volume,
         fallback_min_volume
      )
   );
   return fallback_min_volume;
}
