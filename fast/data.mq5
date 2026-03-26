#property script_show_inputs // Show settings window
input int ticks_to_export = 2160000; // Total ticks (~5 days of Gold)
input string USDX_Symbol = "$USDX"; // Name of USD Index
input string USDJPY_Symbol = "USDJPY"; // Name of USDJPY

void OnStart() { // Main script function
   MqlTick ticks[], usdx_ticks[], usdjpy_ticks[]; // Arrays to hold tick data
   
   // Enable symbols and check if they're available
   bool usdx_available = SymbolSelect(USDX_Symbol, true);
   bool usdjpy_available = SymbolSelect(USDJPY_Symbol, true);
   
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, ticks_to_export); // Get main symbol ticks
   if(copied <= 0) { Print("❌ Failed to copy ticks"); return; } // Error check
   
   // Get tick data for auxiliary symbols if available
   int usdx_copied = 0, usdjpy_copied = 0;
   if(usdx_available) {
      usdx_copied = CopyTicks(USDX_Symbol, usdx_ticks, COPY_TICKS_ALL, 0, ticks_to_export);
      if(usdx_copied <= 0) { Print("⚠️ USDX ticks not available, using placeholder"); usdx_available = false; }
   }
   if(usdjpy_available) {
      usdjpy_copied = CopyTicks(USDJPY_Symbol, usdjpy_ticks, COPY_TICKS_ALL, 0, ticks_to_export);
      if(usdjpy_copied <= 0) { Print("⚠️ USDJPY ticks not available, using placeholder"); usdjpy_available = false; }
   }
   
   int h = FileOpen("achilles_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ","); // Create file
   FileWrite(h, "time_msc,bid,ask,usdx,usdjpy"); // Write CSV header
   
   int usdx_idx = 0, usdjpy_idx = 0; // Indices for auxiliary tick arrays
   
   for(int i=0; i<copied; i++) { // Loop through every tick
      ulong t = ticks[i].time_msc; // Current tick timestamp
      
      // Find matching USDX tick (closest timestamp <= current tick)
      double usdx_bid = 0.0;
      if(usdx_available && usdx_copied > 0) {
         while(usdx_idx < usdx_copied - 1 && usdx_ticks[usdx_idx].time_msc <= t) usdx_idx++;
         if(usdx_idx > 0 && usdx_ticks[usdx_idx].time_msc > t) usdx_idx--;
         usdx_bid = usdx_ticks[usdx_idx].bid;
      }
      
      // Find matching USDJPY tick (closest timestamp <= current tick)
      double usdjpy_bid = 0.0;
      if(usdjpy_available && usdjpy_copied > 0) {
         while(usdjpy_idx < usdjpy_copied - 1 && usdjpy_ticks[usdjpy_idx].time_msc <= t) usdjpy_idx++;
         if(usdjpy_idx > 0 && usdjpy_ticks[usdjpy_idx].time_msc > t) usdjpy_idx--;
         usdjpy_bid = usdjpy_ticks[usdjpy_idx].bid;
      }
      
      FileWrite(h, IntegerToString(ticks[i].time_msc) + "," + // Time in milliseconds
                   DoubleToString(ticks[i].bid, 5) + "," + // Current Bid
                   DoubleToString(ticks[i].ask, 5) + "," + // Current Ask
                   DoubleToString(usdx_bid, 5) + "," + // USDX bid (matched by time)
                   DoubleToString(usdjpy_bid, 5)); // USDJPY bid (matched by time)
   }
   FileClose(h); // Close file
   Print("✅ Exported ", copied, " ticks to MQL5\\Files\\achilles_ticks.csv"); // Success message
   if(usdx_available) Print("   USDX: ", usdx_copied, " ticks matched");
   if(usdjpy_available) Print("   USDJPY: ", usdjpy_copied, " ticks matched");
}
