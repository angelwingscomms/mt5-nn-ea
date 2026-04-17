double NormalizeVolume(double volume) {
   double min_volume = ResolveMinimumVolume();
   double max_volume = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(min_volume <= 0.0 || max_volume <= 0.0) {
      return 0.0;
   }
   if(step <= 0.0) {
      step = min_volume;
   }
   if(volume < min_volume - 1e-12) {
      return 0.0;
   }

   volume = MathMin(volume, max_volume);
   double steps = MathFloor(volume / step + 1e-9);
   double normalized = steps * step;
   if(normalized < min_volume) {
      return 0.0;
   }
   if(normalized > max_volume) {
      normalized = max_volume;
   }
   return NormalizeDouble(normalized, 8);
}
