ulong BarOpenTime(ulong bar_bucket) {
   return bar_bucket * PRIMARY_BAR_MILLISECONDS;
}
