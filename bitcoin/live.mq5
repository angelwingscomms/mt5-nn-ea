#include <Trade\Trade.mqh>
#resource "\\Experts\\nn\\bitcoin\\bitcoin_mamba_144.onnx" as uchar model_buffer[]

input int TICK_DENSITY = 54;
input double SL_MULTIPLIER = 5.4;
input double TP_MULTIPLIER = 9;
long onnx_handle = INVALID_HANDLE;
CTrade trade;

// PASTE FROM PYTHON OUTPUT
float medians[15] = {-0.00000439f, 27.00000000f, 268.29100000f, 0.00028073f, 0.00029178f, 0.00140701f, 0.50154799f, 0.00007258f, 0.00006459f, -0.00001585f, 0.00149410f, 0.00000000f, -0.25881905f, 0.00000000f, -0.22252093f};
float iqrs[15] = {0.00130049f, 0.04936111f, 109.56350000f, 0.00043169f, 0.00045235f, 0.00090441f, 0.59345870f, 0.00143933f, 0.00135949f, 0.00045600f, 0.00063614f, 1.41421356f, 1.20710678f, 1.56366296f, 1.52445867f};

struct Bar {
   double o, h, l, c, spread, atr18, macd_ema12, macd_ema26, macd_sig;
   ulong time_msc;
};
Bar history[200];
Bar cur_b;
int ticks_in_bar = 0;

// Shape is now (1, 120, 15) = 1800 floats, but declared as 3D-logical flat array
float input_data[1800];   // filled as [seq][feat] = input_data[seq*15 + feat]
float output_data[3];

static double tr_buf[18];
static int    tr_buf_n = 0;

int OnInit() {
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("[FATAL] OnnxCreateFromBuffer failed: ", GetLastError());
      return(INIT_FAILED);
   }

   const long in_shape[]  = {1, 120, 15};
   const long out_shape[] = {1, 3};
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape) ||
      !OnnxSetOutputShape(onnx_handle, 0, out_shape)) {
      Print("[FATAL] OnnxSetShape failed: ", GetLastError());
      OnnxRelease(onnx_handle);
      onnx_handle = INVALID_HANDLE;
      return(INIT_FAILED);
   }

   // Reset static indicator state on each EA start
   tr_buf_n = 0;
   ArrayInitialize(tr_buf, 0);

   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   if(onnx_handle != INVALID_HANDLE) OnnxRelease(onnx_handle);
}

void OnTick() {
   MqlTick t;
   if(!SymbolInfoTick(_Symbol, t)) return;

   if(ticks_in_bar == 0) {
      cur_b.o = t.bid; cur_b.h = t.bid; cur_b.l = t.bid;
      cur_b.spread = 0; cur_b.time_msc = t.time_msc;
   }
   cur_b.h = MathMax(cur_b.h, t.bid);
   cur_b.l = MathMin(cur_b.l, t.bid);
   cur_b.c = t.bid;
   cur_b.spread += (t.ask - t.bid);
   ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      cur_b.spread /= TICK_DENSITY;
      UpdateIndicators(cur_b);
      for(int i = 199; i > 0; i--) history[i] = history[i-1];
      history[0] = cur_b;
      ticks_in_bar = 0;
      if(history[120].c > 0) Predict();
   }
}

void UpdateIndicators(Bar &b) {
   Bar p = history[0];
   if(p.c <= 0) {
      b.macd_ema12 = b.c; b.macd_ema26 = b.c; b.macd_sig = 0;
      double tr0 = b.h - b.l;
      tr_buf[0] = tr0; tr_buf_n = 1;
      b.atr18 = tr0;
      return;
   }
   double tr = MathMax(b.h - b.l, MathMax(MathAbs(b.h - p.c), MathAbs(b.l - p.c)));
   if(tr_buf_n < 18) {
      tr_buf[tr_buf_n++] = tr;
      double sum = 0;
      for(int k = 0; k < tr_buf_n; k++) sum += tr_buf[k];
      b.atr18 = sum / tr_buf_n;
   } else {
      b.atr18 = (tr - p.atr18) / 18.0 + p.atr18;
   }
   b.macd_ema12 = (b.c - p.macd_ema12) * (2.0 / 13.0) + p.macd_ema12;
   b.macd_ema26 = (b.c - p.macd_ema26) * (2.0 / 27.0) + p.macd_ema26;
   double macd_raw = b.macd_ema12 - b.macd_ema26;
   b.macd_sig = (macd_raw - p.macd_sig) * (2.0 / 10.0) + p.macd_sig;
}

void Predict() {
   for(int i = 0; i < 120; i++) {
      int h = 119 - i;   // oldest bar at i=0, newest at i=119 — matches Python sequence order
      float f[15];
      double cl = history[h].c;
      double utc_h = (double)((history[h].time_msc / 3600000) % 24);
      double utc_d = (double)(((history[h].time_msc / 86400000) + 3) % 7);

      f[0]  = (float)MathLog(cl / history[h+1].c);
      f[1]  = (float)history[h].spread;
      f[2]  = (float)((history[h].time_msc - history[h+1].time_msc) / 1000.0);
      f[3]  = (float)((history[h].h - MathMax(history[h].o, cl)) / cl);
      f[4]  = (float)((MathMin(history[h].o, cl) - history[h].l) / cl);
      f[5]  = (float)((history[h].h - history[h].l) / cl);
      f[6]  = (float)((cl - history[h].l) / (history[h].h - history[h].l + 1e-8));
      double macd = history[h].macd_ema12 - history[h].macd_ema26;
      f[7]  = (float)(macd / cl);
      f[8]  = (float)(history[h].macd_sig / cl);
      f[9]  = (float)((macd - history[h].macd_sig) / cl);
      f[10] = (float)(history[h].atr18 / cl);
      f[11] = (float)MathSin(2 * M_PI * utc_h / 24.0);
      f[12] = (float)MathCos(2 * M_PI * utc_h / 24.0);
      f[13] = (float)MathSin(2 * M_PI * utc_d / 7.0);
      f[14] = (float)MathCos(2 * M_PI * utc_d / 7.0);

      for(int k = 0; k < 15; k++) {
         float scaled = (f[k] - medians[k]) / iqrs[k];
         input_data[i * 15 + k] = MathMax(-10.0f, MathMin(10.0f, scaled));
      }
   }

   if(OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      int sig = ArrayMaximum(output_data);
      if(sig > 0 && output_data[sig] > 0.72) Execute(sig);
   }
}

void Execute(int sig) {
   if(PositionSelect(_Symbol)) return;
   double p  = (sig == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (sig == 1) ? (p - history[0].atr18 * SL_MULTIPLIER) : (p + history[0].atr18 * SL_MULTIPLIER);
   double tp = (sig == 1) ? (p + history[0].atr18 * TP_MULTIPLIER) : (p - history[0].atr18 * TP_MULTIPLIER);

   double min_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(MathAbs(p - sl) < min_dist || MathAbs(tp - p) < min_dist) {
      Print("[WARN] Stop/TP too close to price, skipping trade.");
      return;
   }
   trade.PositionOpen(_Symbol, (sig == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL), 0.72, p, sl, tp);
}
