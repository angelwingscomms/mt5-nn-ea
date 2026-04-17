void Softmax(const float &logits[], float &probs[]) {
   double max_logit = MathMax(logits[0], MathMax(logits[1], logits[2]));
   double e0 = MathExp(logits[0] - max_logit);
   double e1 = MathExp(logits[1] - max_logit);
   double e2 = MathExp(logits[2] - max_logit);
   double sum = e0 + e1 + e2;
   probs[0] = (float)(e0 / sum);
   probs[1] = (float)(e1 / sum);
   probs[2] = (float)(e2 / sum);
}
