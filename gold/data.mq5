#property script_show_inputs

input int days_to_export = 60;
input string output_file = "gold_market_ticks.csv";
input string gold_symbol = "XAUUSD";
input string usdx_symbol = "$USDX";
input string usdjpy_symbol = "USDJPY";

void ExportSymbol(string symbol, long start_time, long end_time, int file_handle) {
   MqlTick ticks[];
   int copied = CopyTicksRange(symbol, ticks, COPY_TICKS_ALL, start_time, end_time);
   if(copied <= 0) {
      PrintFormat("CopyTicksRange failed for %s. err=%d", symbol, GetLastError());
      return;
   }

   for(int i = 0; i < copied; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }
      FileWrite(file_handle, symbol, ticks[i].time_msc, ticks[i].bid, ticks[i].ask);
   }
}

void OnStart() {
   int file_handle = FileOpen(output_file, FILE_WRITE | FILE_CSV | FILE_ANSI, ",");
   if(file_handle == INVALID_HANDLE) {
      PrintFormat("Cannot open %s. err=%d", output_file, GetLastError());
      return;
   }

   FileWrite(file_handle, "symbol", "time_msc", "bid", "ask");

   long end_time = TimeCurrent() * 1000LL;
   long start_time = end_time - (long)days_to_export * 24LL * 3600LL * 1000LL;
   ExportSymbol(gold_symbol, start_time, end_time, file_handle);
   ExportSymbol(usdx_symbol, start_time, end_time, file_handle);
   ExportSymbol(usdjpy_symbol, start_time, end_time, file_handle);

   FileClose(file_handle);
}
