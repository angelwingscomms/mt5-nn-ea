#property script_show_inputs // Show settings window
input int ticks_to_export = 2160000; // Total ticks (~5 days of Bitcoin)

// Bitcoin Tick Data Exporter - Exports only Bitcoin prices with datetime

//+------------------------------------------------------------------+
//| Logging helper functions                                          |
//+------------------------------------------------------------------+
void LogInfo(string message) {
   Print("[INFO] ", message);
}

void LogSuccess(string message) {
   Print("✅ [SUCCESS] ", message);
}

void LogWarning(string message) {
   Print("⚠️ [WARNING] ", message);
}

void LogError(string message) {
   Print("❌ [ERROR] ", message);
}

void LogProgress(string stage, int current, int total, string extra = "") {
   int percent = (int)((double)current / total * 100);
   Print("📊 [PROGRESS] ", stage, ": ", current, "/", total, " (", percent, "%)", extra);
}

void LogSeparator() {
   Print("═══════════════════════════════════════════════════════════════");
}

//+------------------------------------------------------------------+
//| Main script function                                              |
//+------------------------------------------------------------------+
void OnStart() {
   ulong start_time = GetTickCount64(); // Script start timestamp
   LogSeparator();
   LogInfo("BITCOIN TICK DATA EXPORTER - Starting execution");
   LogSeparator();
   LogInfo(StringFormat("Parameters: ticks_to_export=%d", ticks_to_export));
   LogInfo(StringFormat("Main symbol: %s", _Symbol));
   
   MqlTick ticks[]; // Array to hold tick data
   
   // === TICK DATA COPYING PHASE ===
   LogSeparator();
   LogInfo("Phase 1: Tick Data Acquisition");
   LogInfo(StringFormat("  Copying %d ticks for main symbol '%s'...", ticks_to_export, _Symbol));
   
   ulong copy_start = GetTickCount64();
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, 0, ticks_to_export);
   ulong copy_time = GetTickCount64() - copy_start;
   
   if(copied <= 0) {
      LogError(StringFormat("  Failed to copy ticks for '%s'! Error code: %d", _Symbol, GetLastError()));
      LogError("  Script terminated - no data to export");
      return;
   }
   LogSuccess(StringFormat("  Copied %d ticks for '%s' in %llu ms", copied, _Symbol, copy_time));
   
   // Log tick data time range
   if(copied > 0) {
      datetime first_time = (datetime)(ticks[0].time_msc / 1000);
      datetime last_time = (datetime)(ticks[copied-1].time_msc / 1000);
      LogInfo(StringFormat("  Tick time range: %s to %s", 
                           TimeToString(first_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS),
                           TimeToString(last_time, TIME_DATE|TIME_MINUTES|TIME_SECONDS)));
   }
   
    // === FILE CREATION PHASE ===
    LogSeparator();
    LogInfo("Phase 2: File Creation");
    LogInfo("  Creating output file: fast/bitcoin_ticks.csv");
    LogInfo("  (MQL5 sandbox restricts to MQL5\\Files, run move_ticks.py after export)");
    
    int h = FileOpen("fast/bitcoin_ticks.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   if(h == INVALID_HANDLE) {
      LogError(StringFormat("  Failed to create file! Error code: %d", GetLastError()));
      LogError("  Script terminated - cannot write data");
      return;
   }
   LogSuccess("  File opened successfully");
   
   FileWrite(h, "time_msc,bid,ask"); // Write CSV header (Bitcoin only, no USDX/USDJPY)
   LogInfo("  CSV header written: time_msc,bid,ask");
   
   // === DATA PROCESSING PHASE ===
   LogSeparator();
   LogInfo("Phase 3: Data Processing & Export");
   LogInfo(StringFormat("  Processing %d ticks...", copied));
   
   int progress_interval = copied / 10; // Report progress every 10%
   if(progress_interval < 1000) progress_interval = 1000; // Minimum 1000 ticks between reports
   
   ulong process_start = GetTickCount64();
   
   for(int i = 0; i < copied; i++) {
      // Use StringFormat for efficient string building
      string row = StringFormat("%lld,%.2f,%.2f",
                                ticks[i].time_msc,
                                ticks[i].bid,
                                ticks[i].ask);
      FileWrite(h, row);
      
      // Progress reporting
      if(progress_interval > 0 && (i + 1) % progress_interval == 0) {
         int percent = (int)((double)(i + 1) / copied * 100);
         ulong elapsed = GetTickCount64() - process_start;
         int estimated_remaining = (int)((double)elapsed / (i + 1) * (copied - i - 1) / 1000);
         LogProgress("Export", i + 1, copied, 
                     StringFormat(" | Elapsed: %ds | ETA: %ds", 
                                  (int)(elapsed / 1000), estimated_remaining));
      }
   }
   
   ulong process_time = GetTickCount64() - process_start;
   
   // === FILE FINALIZATION PHASE ===
   LogSeparator();
   LogInfo("Phase 4: File Finalization");
   FileClose(h);
   LogSuccess("  File closed successfully");
   
   // Calculate file size estimate (approximate)
   long file_size_estimate = copied * 30L; // ~30 bytes per row estimate (Bitcoin only)
   LogInfo(StringFormat("  Estimated file size: ~%.2f MB", (double)file_size_estimate / 1024 / 1024));
   
   // === FINAL SUMMARY ===
   LogSeparator();
   LogInfo("EXECUTION SUMMARY");
   LogSeparator();
   
   ulong total_time = GetTickCount64() - start_time;
   
    LogSuccess(StringFormat("Exported %d ticks to fast/bitcoin_ticks.csv", copied));
    LogInfo("  Run 'python fast/move_ticks.py' to move file to project directory");
    LogInfo(StringFormat("  Main symbol (%s): %d ticks", _Symbol, copied));
   
   LogInfo(StringFormat("Processing time: %llu ms (%.2f seconds)", process_time, (double)process_time / 1000));
   LogInfo(StringFormat("Throughput: %.0f ticks/second", (double)copied / (process_time / 1000.0)));
   LogInfo(StringFormat("Total script execution time: %llu ms (%.2f seconds)", total_time, (double)total_time / 1000));
   
   LogSeparator();
   LogSuccess("SCRIPT COMPLETED SUCCESSFULLY");
   LogSeparator();
}
