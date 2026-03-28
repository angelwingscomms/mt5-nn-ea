#property script_show_inputs
input int ticks_to_export = 2160000;
input int days_lookback   = 180;     // Force anchor 6 months into the past
input int chunk_size      = 100000;

void OnStart() {
   Print("[INFO] Initializing Absolute-Chronological Tick Export...");
   ResetLastError();

   int h = FileOpen("fast/bitcoin_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) { 
      Print("❌ FATAL I/O ERROR: Cannot open CSV file."); 
      return; 
   }
   
   FileWrite(h, "time_msc", "bid", "ask", "vol"); 
   
   MqlTick ticks[];
   int total_copied = 0;
   
   // CRITICAL FIX: Establish a strict temporal anchor in the deep past (Safe 64-bit math)
   ulong anchor_msc = ((ulong)TimeCurrent() - ((ulong)days_lookback * 86400ull)) * 1000ull;
   ulong last_time  = anchor_msc;
   
   PrintFormat("[INFO] Temporal Anchor set to %d days ago. Moving strictly forward in time...", days_lookback);
   
   while(total_copied < ticks_to_export) {
      int to_copy = MathMin(chunk_size, ticks_to_export - total_copied);
      
      ulong fetch_start = GetTickCount64();
      int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, last_time, to_copy);
      ulong fetch_time = GetTickCount64() - fetch_start;
      
      if(copied <= 0) {
         PrintFormat("⚠️ Stream exhausted. The broker has no more historical data. Copied: %d | Total: %d", copied, total_copied);
         break;
      }
      
      // Advance pointer strictly forward to the exact millisecond after the last recorded tick
      last_time = ticks[copied-1].time_msc + 1; 
      
      int valid_ticks = 0;
      for(int i = 0; i < copied; i++) {
         if(ticks[i].bid <= 0.0 || ticks[i].ask < ticks[i].bid) continue; // Noise filter
         
         double v = (ticks[i].volume > 0) ? (double)ticks[i].volume : 1.0;
         FileWrite(h, ticks[i].time_msc, ticks[i].bid, ticks[i].ask, v);
         valid_ticks++;
      }
      
      total_copied += copied;
      
      // Real-time telemetry: Watch the date advance chronologically
      double progress = ((double)total_copied / ticks_to_export) * 100.0;
      PrintFormat("[STREAM] %.2f%% | Fetched: %d | Processing Date: %s | Total: %d / %d", 
                  progress, copied, TimeToString(ticks[copied-1].time), total_copied, ticks_to_export);
                  
      // Halt if we slam into the present moment
      if(last_time >= (ulong)TimeCurrent() * 1000ull) {
          Print("[INFO] Temporal pointer reached the present moment. Halting stream.");
          break;
      }
                  
      Sleep(10); // Yield to MT5 Main Thread
   }
   
   FileClose(h);
   PrintFormat("✅ EXPORT COMPLETE. Serialized %d ticks. Proceed to Python tensor generation.", total_copied);
}