#property script_show_inputs
input int ticks_to_export = 2160000;

void OnStart() {
   Print("[INFO] Starting Microstructure Tick Export...");
   MqlTick ticks[];
   // ticks_to_export is int, CopyTicks expects uint for count
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, (uint)ticks_to_export);
   
   if(copied <= 0) {
      Print("❌ Error: No ticks copied. Check Symbol name and History.");
      return;
   }
   
   int h = FileOpen("fast/bitcoin_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) return;
   
   FileWrite(h, "time_msc", "bid", "ask", "vol"); 
   
   for(int i = 0; i < copied; i++) {
      if(ticks[i].bid <= 0.0 || ticks[i].ask <= 0.0) continue;
      
      // FIX: Use .volume instead of .tick_volume. 
      // Add fallback to 1.0 if volume is not provided by broker.
      double v = (ticks[i].volume > 0) ? (double)ticks[i].volume : 1.0;
      
      FileWrite(h, ticks[i].time_msc, ticks[i].bid, ticks[i].ask, v);
   }
   FileClose(h);
   PrintFormat("✅ Exported %d ticks with Micro-Volume data.", copied);
}