void Predict() {
   prediction_count++;
   for(int i = 0; i < SEQ_LEN; i++) {
      int h = SEQ_LEN - 1 - i;
      int offset = i * MODEL_FEATURE_COUNT;
      float features[MODEL_FEATURE_COUNT];
      ExtractFeatures(h, features);
      for(int k = 0; k < MODEL_FEATURE_COUNT; k++) {
         input_data[offset + k] = features[k];
      }
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      DebugPrint(StringFormat("OnnxRun failed err=%d", GetLastError()));
      return;
   }

   #ifdef USE_NO_HOLD
      float probs[2];
   #else
      float probs[3];
   #endif
   #ifdef USE_NO_HOLD
      DebugPrint("binary-mode USE_NO_HOLD=true");
   #else
      DebugPrint("ternary-mode USE_NO_HOLD=false");
   #endif
   Softmax(output_data, probs);
   int signal = ArrayMaximum(probs);
   #ifdef USE_NO_HOLD
      DebugPrint(
         StringFormat(
            "predict probs=[%.4f, %.4f] signal=%s conf=%.4f",
            probs[0],
            probs[1],
            SignalName(signal),
            probs[signal]
         )
      );
      if(signal < 0 || signal > 1) {
         DebugPrint(StringFormat("ERROR: invalid binary signal %d", signal));
         hold_skip_count++;
         return;
      }
   #else
      DebugPrint(
         StringFormat(
            "predict probs=[%.4f, %.4f, %.4f] signal=%s conf=%.4f",
            probs[0],
            probs[1],
            probs[2],
            SignalName(signal),
            probs[signal]
         )
      );
      if(signal <= 0) {
         hold_skip_count++;
         DebugPrint("skip trade: model chose HOLD");
         return;
      }
   #endif
   if(probs[signal] < PRIMARY_CONFIDENCE) {
      confidence_skip_count++;
      DebugPrint(
         StringFormat(
            "skip trade: confidence %.4f below threshold %.4f",
            probs[signal],
            PRIMARY_CONFIDENCE
         )
      );
      return;
   }

   Execute(signal);
}
