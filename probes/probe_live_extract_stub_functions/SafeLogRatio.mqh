double SafeLogRatio(double num, double den) {
   return MathLog((num + 1e-10) / (den + 1e-10));
}
