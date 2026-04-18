void OnDeinit(const int reason) {
   PrintRunSummary();
   if(onnx_handle != INVALID_HANDLE) {
      OnnxRelease(onnx_handle);
   }
}
