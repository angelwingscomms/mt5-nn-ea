double TrueRangeAt(int h) {
   Bar bar = history[h];
   if(h + 1 > REQUIRED_HISTORY_INDEX) {
      return bar.h - bar.l;
   }
   double prev_close = history[h + 1].c;
   return MathMax(bar.h - bar.l, MathMax(MathAbs(bar.h - prev_close), MathAbs(bar.l - prev_close)));
}
