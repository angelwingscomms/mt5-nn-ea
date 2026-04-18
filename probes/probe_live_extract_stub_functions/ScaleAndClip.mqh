float ScaleAndClip(float value, int feature_index) {
   float iqr = (iqrs[feature_index] > 1e-6f ? iqrs[feature_index] : 1.0f);
   float scaled = (value - medians[feature_index]) / iqr;
   return MathMax(-10.0f, MathMin(10.0f, scaled));
}
