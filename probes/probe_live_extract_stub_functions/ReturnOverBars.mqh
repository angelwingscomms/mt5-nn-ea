double ReturnOverBars(int h, int bars) {
   return SafeLogRatio(history[h].c, history[h + bars].c);
}
