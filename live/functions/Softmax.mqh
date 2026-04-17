void Softmax(const float &logits[], float &probs[]) {
   #ifdef USE_NO_HOLD
      double max_logit = MathMax(logits[0], logits[1]);
      double e0 = MathExp(logits[0] - max_logit);
      double e1 = MathExp(logits[1] - max_logit);
      double sum = e0 + e1;
      probs[0] = (float)(e0 / sum);
      probs[1] = (float)(e1 / sum);
      DebugPrint(StringFormat("binary-softmax e0=%.4f e1=%.4f sum=%.4f probs=[%.4f, %.4f]", e0, e1, sum, probs[0], probs[1]));
   #else
      double max_logit = MathMax(logits[0], MathMax(logits[1], logits[2]));
      double e0 = MathExp(logits[0] - max_logit);
      double e1 = MathExp(logits[1] - max_logit);
      double e2 = MathExp(logits[2] - max_logit);
      double sum = e0 + e1 + e2;
      probs[0] = (float)(e0 / sum);
      probs[1] = (float)(e1 / sum);
      probs[2] = (float)(e2 / sum);
   #endif
}
