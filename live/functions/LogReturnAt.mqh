double LogReturnAt(int h) {
   return SafeLogRatio(history[h].c, history[h + 1].c);
}
