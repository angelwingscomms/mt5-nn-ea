#property script_show_inputs
input int days_to_export = 7;
input string USDX_Symbol = "$USDX";
input string USDJPY_Symbol = "USDJPY";

void OnStart() {
   datetime end = TimeCurrent(), start = end - (days_to_export * 86400);
   MqlTick t_main[], t_usdx[], t_usdjpy[];
   SymbolSelect(USDX_Symbol, true); SymbolSelect(USDJPY_Symbol, true);
   
   int c_main = CopyTicksRange(_Symbol, t_main, COPY_TICKS_ALL, start*1000, end*1000);
   int c_usdx = CopyTicksRange(USDX_Symbol, t_usdx, COPY_TICKS_ALL, start*1000, end*1000);
   int c_usdjpy = CopyTicksRange(USDJPY_Symbol, t_usdjpy, COPY_TICKS_ALL, start*1000, end*1000);

   if(c_main <= 0 || c_usdx <= 0 || c_usdjpy <= 0) { Print("❌ Sync Error"); return; }

   int h = FileOpen("achilles_sync.csv", FILE_WRITE|FILE_CSV|FILE_ANSI, ",");
   FileWrite(h, "time_msc,bid,ask,usdx,usdjpy");

   int p_usdx = 0, p_usdjpy = 0;
   for(int i=0; i<c_main; i++) {
      while(p_usdx + 1 < c_usdx && t_usdx[p_usdx+1].time_msc <= t_main[i].time_msc) p_usdx++;
      while(p_usdjpy+1 < c_usdjpy && t_usdjpy[p_usdjpy+1].time_msc <= t_main[i].time_msc) p_usdjpy++;

      FileWrite(h, (string)t_main[i].time_msc, DoubleToString(t_main[i].bid, 5), DoubleToString(t_main[i].ask, 5),
                   DoubleToString(t_usdx[p_usdx].bid, 5), DoubleToString(t_usdjpy[p_usdjpy].bid, 5));
   }
   FileClose(h);
   Print("✅ Exported ", c_main, " synced rows.");
}