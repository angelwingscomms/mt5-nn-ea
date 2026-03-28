#property script_show_inputs
input int ticks_to_export = 2160000;

void OnStart() {
   ulong start_time = GetTickCount64();
   Print("[INFO] Starting High-Throughput Tick Export...");
   
   MqlTick ticks[];
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, ticks_to_export);
   if(copied <= 0) { Print("❌ Failed to copy ticks."); return; }
   
   int h = FileOpen("bitcoin_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) { Print("❌ Failed to create file."); return; }
   
   FileWrite(h, "time_msc", "bid", "ask"); 
   
   int valid_ticks = 0;
   for(int i = 0; i < copied; i++) {
      // CRITICAL FIX: Strip corrupted server ticks with zero-pricing
      if(ticks[i].bid <= 0.0 || ticks[i].ask <= 0.0) continue;
      
      // CRITICAL FIX: O(1) direct write bypasses string allocation overhead
      FileWrite(h, ticks[i].time_msc, ticks[i].bid, ticks[i].ask);
      valid_ticks++;
   }
   FileClose(h);
   
   PrintFormat("✅ Exported %d valid ticks in %.2f seconds.", valid_ticks, (GetTickCount64()-start_time)/1000.0);
}