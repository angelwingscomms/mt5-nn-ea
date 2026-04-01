#include <Trade\Trade.mqh>
#include "gold_model_config.mqh"

#resource "\\Experts\\nn\\gold\\gold_mamba.onnx" as uchar model_buffer[]

#define SEQ_LEN 120
#define SYMBOL_COUNT 3
#define GOLD_FEATURE_COUNT 13
#define AUX_FEATURE_COUNT 5
#define REQUIRED_HISTORY_INDEX 136
#define HISTORY_SIZE (REQUIRED_HISTORY_INDEX + 1)
#define INPUT_BUFFER_SIZE (SEQ_LEN * MODEL_FEATURE_COUNT)

input double SL_MULTIPLIER = 5.4;
input double TP_MULTIPLIER = 9.0;
input double LOT_SIZE = 0.01;
input int MAGIC_NUMBER = 777777;
input string USDX_SYMBOL = "USDX";
input string USDJPY_SYMBOL = "USDJPY";

long onnx_handle = INVALID_HANDLE;
CTrade trade;

struct Bar {
   double o;
   double h;
   double l;
   double c;
   double spread;
   double tick_imbalance;
   double atr14;
   ulong time_msc;
   bool valid;
};

Bar history[SYMBOL_COUNT][HISTORY_SIZE];
Bar current_bar[SYMBOL_COUNT];
int ticks_in_bar[SYMBOL_COUNT];
bool bar_started[SYMBOL_COUNT];
ulong last_tick_time[SYMBOL_COUNT];
double tick_imbalance_sum[SYMBOL_COUNT];
double last_bid[SYMBOL_COUNT];
int last_sign[SYMBOL_COUNT];
double primary_expected_abs_theta = 60.0;
int warmup_count[SYMBOL_COUNT];
double warmup_sum[SYMBOL_COUNT];
float input_data[INPUT_BUFFER_SIZE];
float output_data[3];

string SymbolForIndex(int s);
int UpdateTickSign(int s, double bid);
void ProcessTick(int s, MqlTick &tick);
void ProcessSymbolSnapshotToTime(int s, ulong end_time_msc);
void UpdateIndicators(int s, Bar &bar);
bool ShouldClosePrimaryBar(double &observed_abs_theta);
void UpdatePrimaryImbalanceThreshold(double observed_abs_theta);
void CloseBar();
void LoadHistory();
float ScaleAndClip(float value, int feature_index);
double SafeLogRatio(double num, double den);
double LogReturnAt(int s, int h);
double ReturnOverBars(int s, int h, int bars);
double RollingStdReturn(int s, int h, int window);
void ExtractGoldFeatures(int h, float &features[]);
void ExtractAuxFeatures(int s, int h, float &features[]);
void Softmax(const float &logits[], float &probs[]);
void Predict();
void Execute(int signal);

int OnInit() {
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("[FATAL] OnnxCreateFromBuffer failed: ", GetLastError());
      return INIT_FAILED;
   }

   long input_shape[3];
   long output_shape[2];
   input_shape[0] = 1;
   input_shape[1] = SEQ_LEN;
   input_shape[2] = MODEL_FEATURE_COUNT;
   output_shape[0] = 1;
   output_shape[1] = 3;
   if(!OnnxSetInputShape(onnx_handle, 0, input_shape) || !OnnxSetOutputShape(onnx_handle, 0, output_shape)) {
      Print("[FATAL] OnnxSetShape failed: ", GetLastError());
      OnnxRelease(onnx_handle);
      onnx_handle = INVALID_HANDLE;
      return INIT_FAILED;
   }

   ArrayInitialize(ticks_in_bar, 0);
   ArrayInitialize(bar_started, false);
   ArrayInitialize(last_tick_time, 0);
   ArrayInitialize(tick_imbalance_sum, 0.0);
   ArrayInitialize(last_bid, 0.0);
   ArrayInitialize(last_sign, 1);
   ArrayInitialize(warmup_count, 0);
   ArrayInitialize(warmup_sum, 0.0);
   ArrayInitialize(input_data, 0.0f);

   for(int s = 0; s < SYMBOL_COUNT; s++) {
      for(int i = 0; i < HISTORY_SIZE; i++) {
         history[s][i].valid = false;
      }

      string symbol = SymbolForIndex(s);
      SymbolSelect(symbol, true);
      MqlTick tick;
      if(SymbolInfoTick(symbol, tick)) {
         last_tick_time[s] = tick.time_msc;
      } else {
         last_tick_time[s] = TimeCurrent() * 1000ULL;
      }
   }

   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   primary_expected_abs_theta = MathMax(2.0, (double)MathMax(2, IMBALANCE_MIN_TICKS / 3));
   LoadHistory();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   if(onnx_handle != INVALID_HANDLE) {
      OnnxRelease(onnx_handle);
   }
}

string SymbolForIndex(int s) {
   if(s == 0) {
      return _Symbol;
   }
   if(s == 1) {
      return USDX_SYMBOL;
   }
   return USDJPY_SYMBOL;
}

int UpdateTickSign(int s, double bid) {
   int sign = last_sign[s];
   if(last_bid[s] <= 0.0) {
      sign = 1;
   } else {
      double diff = bid - last_bid[s];
      if(diff > 0.0) {
         sign = 1;
      } else if(diff < 0.0) {
         sign = -1;
      }
   }

   last_bid[s] = bid;
   last_sign[s] = sign;
   return sign;
}

void ProcessTick(int s, MqlTick &tick) {
   if(tick.bid <= 0.0) {
      return;
   }

   if(!bar_started[s]) {
      current_bar[s].o = tick.bid;
      current_bar[s].h = tick.bid;
      current_bar[s].l = tick.bid;
      current_bar[s].c = tick.bid;
      current_bar[s].spread = tick.ask - tick.bid;
      current_bar[s].tick_imbalance = 0.0;
      current_bar[s].time_msc = tick.time_msc;
      ticks_in_bar[s] = 0;
      tick_imbalance_sum[s] = 0.0;
      bar_started[s] = true;
   }

   int tick_sign = UpdateTickSign(s, tick.bid);
   current_bar[s].h = MathMax(current_bar[s].h, tick.bid);
   current_bar[s].l = MathMin(current_bar[s].l, tick.bid);
   current_bar[s].c = tick.bid;
   current_bar[s].spread = tick.ask - tick.bid;
   ticks_in_bar[s]++;
   tick_imbalance_sum[s] += tick_sign;
}

void ProcessSymbolSnapshotToTime(int s, ulong end_time_msc) {
   if(last_tick_time[s] >= end_time_msc) {
      return;
   }

   MqlTick ticks[];
   int count = CopyTicksRange(SymbolForIndex(s), ticks, COPY_TICKS_ALL, last_tick_time[s] + 1, end_time_msc);
   if(count <= 0) {
      last_tick_time[s] = end_time_msc;
      return;
   }

   for(int i = 0; i < count; i++) {
      if(ticks[i].bid > 0.0) {
         ProcessTick(s, ticks[i]);
      }
   }

   last_tick_time[s] = end_time_msc;
}

void UpdateIndicators(int s, Bar &bar) {
   Bar prev = history[s][0];
   double tr = (warmup_count[s] == 0)
      ? (bar.h - bar.l)
      : MathMax(bar.h - bar.l, MathMax(MathAbs(bar.h - prev.c), MathAbs(bar.l - prev.c)));

   if(warmup_count[s] < 14) {
      warmup_sum[s] += tr;
      warmup_count[s]++;
      bar.atr14 = warmup_sum[s] / warmup_count[s];
   } else {
      double prev_atr = (prev.atr14 > 0.0 ? prev.atr14 : tr);
      bar.atr14 = prev_atr + (tr - prev_atr) / 14.0;
      warmup_count[s]++;
   }

   bar.valid = (warmup_count[s] >= 16);
}

bool ShouldClosePrimaryBar(double &observed_abs_theta) {
   if(ticks_in_bar[0] < IMBALANCE_MIN_TICKS) {
      observed_abs_theta = 0.0;
      return false;
   }

   observed_abs_theta = MathAbs(tick_imbalance_sum[0]);
   return (observed_abs_theta >= primary_expected_abs_theta);
}

void UpdatePrimaryImbalanceThreshold(double observed_abs_theta) {
   if(observed_abs_theta <= 0.0) {
      return;
   }

   double alpha = 2.0 / (MathMax(1, IMBALANCE_EMA_SPAN) + 1.0);
   double observed = MathMax(2.0, observed_abs_theta);
   primary_expected_abs_theta = (1.0 - alpha) * primary_expected_abs_theta + alpha * observed;
}

void CloseBar() {
   for(int s = 0; s < SYMBOL_COUNT; s++) {
      if(ticks_in_bar[s] == 0) {
         string symbol = SymbolForIndex(s);
         if(history[s][0].valid || history[s][0].c > 0.0) {
            double prev_close = history[s][0].c;
            current_bar[s].o = prev_close;
            current_bar[s].h = prev_close;
            current_bar[s].l = prev_close;
            current_bar[s].c = prev_close;
            current_bar[s].spread = history[s][0].spread;
            current_bar[s].tick_imbalance = 0.0;
         } else {
            MqlTick fallback;
            if(SymbolInfoTick(symbol, fallback) && fallback.bid > 0.0) {
               current_bar[s].o = fallback.bid;
               current_bar[s].h = fallback.bid;
               current_bar[s].l = fallback.bid;
               current_bar[s].c = fallback.bid;
               current_bar[s].spread = fallback.ask - fallback.bid;
               current_bar[s].tick_imbalance = 0.0;
            } else {
               current_bar[s].o = 0.0;
               current_bar[s].h = 0.0;
               current_bar[s].l = 0.0;
               current_bar[s].c = 0.0;
               current_bar[s].spread = 0.0;
               current_bar[s].tick_imbalance = 0.0;
            }
         }
         current_bar[s].time_msc = current_bar[0].time_msc;
      } else {
         current_bar[s].tick_imbalance = tick_imbalance_sum[s] / ticks_in_bar[s];
      }

      UpdateIndicators(s, current_bar[s]);

      for(int i = HISTORY_SIZE - 1; i > 0; i--) {
         history[s][i] = history[s][i - 1];
      }
      history[s][0] = current_bar[s];

      ticks_in_bar[s] = 0;
      tick_imbalance_sum[s] = 0.0;
      bar_started[s] = false;
   }
}

void OnTick() {
   MqlTick ticks[];
   int count = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, last_tick_time[0] + 1, 100000);
   if(count <= 0) {
      return;
   }

   for(int i = 0; i < count; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }

      ProcessTick(0, ticks[i]);
      last_tick_time[0] = ticks[i].time_msc;

      double observed_abs_theta = 0.0;
      if(ShouldClosePrimaryBar(observed_abs_theta)) {
         ProcessSymbolSnapshotToTime(1, last_tick_time[0]);
         ProcessSymbolSnapshotToTime(2, last_tick_time[0]);
         CloseBar();
         UpdatePrimaryImbalanceThreshold(observed_abs_theta);

         if(
            history[0][REQUIRED_HISTORY_INDEX].valid &&
            history[1][REQUIRED_HISTORY_INDEX].valid &&
            history[2][REQUIRED_HISTORY_INDEX].valid
         ) {
            Predict();
         }
      }
   }
}

void LoadHistory() {
   ulong start_time_msc = (TimeCurrent() - 86400 * 3) * 1000ULL;
   MqlTick ticks[];
   int copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   if(copied <= 0) {
      start_time_msc = (TimeCurrent() - 86400) * 1000ULL;
      copied = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   }
   if(copied <= 0) {
      return;
   }

   last_tick_time[0] = ticks[0].time_msc - 1;
   last_tick_time[1] = ticks[0].time_msc - 1;
   last_tick_time[2] = ticks[0].time_msc - 1;

   for(int i = 0; i < copied; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }

      ProcessTick(0, ticks[i]);
      last_tick_time[0] = ticks[i].time_msc;

      double observed_abs_theta = 0.0;
      if(ShouldClosePrimaryBar(observed_abs_theta)) {
         ProcessSymbolSnapshotToTime(1, last_tick_time[0]);
         ProcessSymbolSnapshotToTime(2, last_tick_time[0]);
         CloseBar();
         UpdatePrimaryImbalanceThreshold(observed_abs_theta);
      }
   }
}

float ScaleAndClip(float value, int feature_index) {
   float iqr = (iqrs[feature_index] > 1e-6f ? iqrs[feature_index] : 1.0f);
   float scaled = (value - medians[feature_index]) / iqr;
   return MathMax(-10.0f, MathMin(10.0f, scaled));
}

double SafeLogRatio(double num, double den) {
   return MathLog((num + 1e-10) / (den + 1e-10));
}

double LogReturnAt(int s, int h) {
   return SafeLogRatio(history[s][h].c, history[s][h + 1].c);
}

double ReturnOverBars(int s, int h, int bars) {
   return SafeLogRatio(history[s][h].c, history[s][h + bars].c);
}

double RollingStdReturn(int s, int h, int window) {
   double values[16];
   double mean = 0.0;
   for(int i = 0; i < window; i++) {
      values[i] = LogReturnAt(s, h + i);
      mean += values[i];
   }
   mean /= window;

   double var = 0.0;
   for(int i = 0; i < window; i++) {
      double diff = values[i] - mean;
      var += diff * diff;
   }
   return MathSqrt(var / window);
}

void ExtractGoldFeatures(int h, float &features[]) {
   Bar bar = history[0][h];
   Bar prev = history[0][h + 1];
   double close = bar.c;
   double hour = (double)((bar.time_msc / 3600000ULL) % 24);

   features[0] = ScaleAndClip((float)LogReturnAt(0, h), 0);
   features[1] = ScaleAndClip((float)SafeLogRatio(bar.h, prev.c), 1);
   features[2] = ScaleAndClip((float)SafeLogRatio(bar.l, prev.c), 2);
   features[3] = ScaleAndClip((float)(bar.spread / (close + 1e-10)), 3);
   features[4] = ScaleAndClip((float)((double)(bar.time_msc - prev.time_msc) / 1000.0), 4);
   features[5] = ScaleAndClip((float)((close - bar.l) / (bar.h - bar.l + 1e-8)), 5);
   features[6] = ScaleAndClip((float)(bar.atr14 / (close + 1e-10)), 6);
   features[7] = ScaleAndClip((float)RollingStdReturn(0, h, 4), 7);
   features[8] = ScaleAndClip((float)RollingStdReturn(0, h, 16), 8);
   features[9] = ScaleAndClip((float)ReturnOverBars(0, h, 8), 9);
   features[10] = ScaleAndClip((float)bar.tick_imbalance, 10);
   features[11] = ScaleAndClip((float)MathSin(2.0 * M_PI * hour / 24.0), 11);
   features[12] = ScaleAndClip((float)MathCos(2.0 * M_PI * hour / 24.0), 12);
}

void ExtractAuxFeatures(int s, int h, float &features[]) {
   Bar bar = history[s][h];
   double close = bar.c;
   int base = (s == 1 ? GOLD_FEATURE_COUNT : GOLD_FEATURE_COUNT + AUX_FEATURE_COUNT);

   features[0] = ScaleAndClip((float)LogReturnAt(s, h), base + 0);
   features[1] = ScaleAndClip((float)LogReturnAt(s, h + 1), base + 1);
   features[2] = ScaleAndClip((float)((close - bar.l) / (bar.h - bar.l + 1e-8)), base + 2);
   features[3] = ScaleAndClip((float)(bar.atr14 / (close + 1e-10)), base + 3);
   features[4] = ScaleAndClip((float)ReturnOverBars(s, h, 8), base + 4);
}

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

void Predict() {
   for(int i = 0; i < SEQ_LEN; i++) {
      int h = SEQ_LEN - 1 - i;
      int offset = i * MODEL_FEATURE_COUNT;
      float gold_features[GOLD_FEATURE_COUNT];
      float usdx_features[AUX_FEATURE_COUNT];
      float usdjpy_features[AUX_FEATURE_COUNT];

      ExtractGoldFeatures(h, gold_features);
      ExtractAuxFeatures(1, h, usdx_features);
      ExtractAuxFeatures(2, h, usdjpy_features);

      for(int k = 0; k < GOLD_FEATURE_COUNT; k++) {
         input_data[offset + k] = gold_features[k];
      }
      for(int k = 0; k < AUX_FEATURE_COUNT; k++) {
         input_data[offset + GOLD_FEATURE_COUNT + k] = usdx_features[k];
         input_data[offset + GOLD_FEATURE_COUNT + AUX_FEATURE_COUNT + k] = usdjpy_features[k];
      }
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      return;
   }

   float probs[3];
   Softmax(output_data, probs);

   int signal = ArrayMaximum(probs);
   if(signal <= 0) {
      return;
   }
   if(probs[signal] < PRIMARY_CONFIDENCE) {
      return;
   }

   Execute(signal);
}

void Execute(int signal) {
   if(PositionSelect(_Symbol)) {
      return;
   }

   double price = (signal == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (signal == 1) ? (price - history[0][0].atr14 * SL_MULTIPLIER) : (price + history[0][0].atr14 * SL_MULTIPLIER);
   double tp = (signal == 1) ? (price + history[0][0].atr14 * TP_MULTIPLIER) : (price - history[0][0].atr14 * TP_MULTIPLIER);

   double min_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(MathAbs(price - sl) < min_dist || MathAbs(tp - price) < min_dist) {
      return;
   }

   trade.PositionOpen(_Symbol, (signal == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL), LOT_SIZE, price, sl, tp);
}
