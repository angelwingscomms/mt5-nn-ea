// live.mq5 - GOLD Mamba EA
//
// Feature block layout (mirrors gold/nn.py exactly):
//   FEATURE_SET=1 (rich):
//     indices  0-12 -> GOLD   : ret1, high_rel_prev, low_rel_prev, spread_rel,
//                               duration_s, close_in_range, atr14_rel, rv4,
//                               rv16, ret8, tick_imbalance, hour_sin, hour_cos
//     indices 13-17 -> USDX   : ret1, ret1_lag1, close_in_range, atr14_rel, ret8
//     indices 18-22 -> USDJPY : ret1, ret1_lag1, close_in_range, atr14_rel, ret8
//   FEATURE_SET=0 (raw):
//     indices 0-2 -> XAUUSD  : bid, ask, time
//     indices 3-5 -> USDX    : bid, ask, time
//     indices 6-8 -> USDJPY  : bid, ask, time

#include <Trade\Trade.mqh>
#resource "\\Experts\\nn\\gold\\gold_mamba.onnx" as uchar model_buffer[]

#define SEQ_LEN 120
#define MAX_GOLD_FEATURE_COUNT 13
#define MAX_AUX_FEATURE_COUNT 5
#define RAW_SYMBOL_FEATURE_COUNT 3
#define MAX_TOTAL_FEATURE_COUNT 23
#define INPUT_BUFFER_SIZE 2760
#define HISTORY_SIZE 200
#define REQUIRED_HISTORY_INDEX 136
#define META_EXTRA_FEATURE_COUNT 4
#define META_FEATURE_COUNT 10
#define LOG_STREAK_INTERVAL 25

#include "gold_model_config.mqh"

input double SL_MULTIPLIER      = 5.4;
input double TP_MULTIPLIER      = 9.0;
input double LOT_SIZE           = 0.01;
input int    MAGIC_NUMBER       = 777777;

input string USDX_SYMBOL        = "USDX";
input string USDJPY_SYMBOL      = "USDJPY";

long   onnx_handle = INVALID_HANDLE;
CTrade trade;

struct Bar {
   double o, h, l, c, spread, tick_imbalance;
   double atr14;
   ulong  time_msc;
   bool   valid;
};

Bar history[3][HISTORY_SIZE];
Bar cur_b[3];
int ticks_in_bar[3];
bool bar_started[3];
ulong last_tick_time[3];
double tick_imbalance_sum[3];
double last_bid[3];
int    last_sign[3];
double primary_expected_abs_theta = 60.0;

int    warmup_count[3];
double warmup_sum[3];
int    tick_copy_error_streak[3];
int    empty_copy_streak[3];
int    main_tick_copy_error_streak = 0;
int    onnx_error_streak = 0;

float input_data[INPUT_BUFFER_SIZE];
float output_data[3];

string SymbolForIdx(int s);
string FormatTimeMsc(ulong time_msc);
void LogCopyFailure(string symbol, string context, ulong from_time_msc, ulong to_time_msc, int error_code, int streak);
void LogRecovery(string subject, int streak);
void LogEmptyTickRange(int s, ulong end_time_msc);
int UpdateTickSign(int s, double bid);
void ProcessTick(int s, MqlTick &t);
void ProcessSymbolSnapshotToTime(int s, ulong end_time_msc);
void UpdateIndicators(int s, Bar &b);
bool ShouldClosePrimaryBar(double &observed_abs_theta);
void UpdatePrimaryImbalanceThreshold(double observed_abs_theta);
void CloseBar();
void LoadHistory();
float ScaleAndClip(float value, int feature_index);
double SafeLogRatio(double num, double den);
double LogReturnAt(int s, int h);
double ReturnOverBars(int s, int h, int bars);
double RollingStdReturn(int s, int h, int window);
bool UseRichFeatures();
double TimeOfDaySeconds(ulong time_msc);
void ExtractGoldFeatures(int h, float &f[]);
void ExtractAuxFeatures(int s, int h, float &f[]);
void ExtractRawSymbolFeatures(int s, int h, float &f[]);
void CalibratedSoftmax(const float &logits[], double temperature, float &probs[]);
float MetaProbability(const float &meta_features[]);
void BuildMetaFeatures(const float &probs[], float &meta_features[]);
void Predict();
void Execute(int sig);

int OnInit() {
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("[FATAL] OnnxCreateFromBuffer failed: ", GetLastError());
      return INIT_FAILED;
   }

   long in_shape[3];
   long out_shape[2];
   in_shape[0] = 1;
   in_shape[1] = SEQ_LEN;
   in_shape[2] = MODEL_FEATURE_COUNT;
   out_shape[0] = 1;
   out_shape[1] = 3;
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape) ||
      !OnnxSetOutputShape(onnx_handle, 0, out_shape)) {
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
   ArrayInitialize(warmup_sum, 0);
   ArrayInitialize(tick_copy_error_streak, 0);
   ArrayInitialize(empty_copy_streak, 0);
   ArrayInitialize(input_data, 0.0f);

   for(int s = 0; s < 3; s++) {
      for(int b = 0; b < HISTORY_SIZE; b++) {
         history[s][b].valid = false;
      }
   }

   for(int s = 0; s < 3; s++) {
      string symbol = SymbolForIdx(s);
      ResetLastError();
      if(!SymbolSelect(symbol, true)) {
         PrintFormat("[WARN] SymbolSelect(%s) failed during init: err=%d", symbol, GetLastError());
      }

      MqlTick t;
      ResetLastError();
      if(SymbolInfoTick(symbol, t)) {
         last_tick_time[s] = t.time_msc;
      } else {
         last_tick_time[s] = TimeCurrent() * 1000ULL;
         PrintFormat(
            "[WARN] SymbolInfoTick(%s) failed during init: err=%d. Falling back to current server time.",
            symbol,
            GetLastError()
         );
      }
   }

   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   primary_expected_abs_theta = MathMax(2.0, (double)MathMax(2, IMBALANCE_MIN_TICKS / 3));
   Print("[INFO] EA initialised. Symbols: XAUUSD | ", USDX_SYMBOL, " | ", USDJPY_SYMBOL);
   LoadHistory();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   if(onnx_handle != INVALID_HANDLE) {
      OnnxRelease(onnx_handle);
   }
}

string SymbolForIdx(int s) {
   if(s == 0) {
      return _Symbol;
   }
   if(s == 1) {
      return USDX_SYMBOL;
   }
   return USDJPY_SYMBOL;
}

string FormatTimeMsc(ulong time_msc) {
   datetime ts = (datetime)(time_msc / 1000ULL);
   return TimeToString(ts, TIME_DATE | TIME_SECONDS) + StringFormat(".%03d", (int)(time_msc % 1000ULL));
}

void LogCopyFailure(string symbol, string context, ulong from_time_msc, ulong to_time_msc, int error_code, int streak) {
   if(streak == 1 || (streak % LOG_STREAK_INTERVAL) == 0) {
      PrintFormat(
         "[ERROR] %s failed for %s. from=%s to=%s err=%d streak=%d",
         context,
         symbol,
         FormatTimeMsc(from_time_msc),
         FormatTimeMsc(to_time_msc),
         error_code,
         streak
      );
   }
}

void LogRecovery(string subject, int streak) {
   if(streak > 0) {
      PrintFormat("[INFO] %s recovered after %d consecutive issues.", subject, streak);
   }
}

void LogEmptyTickRange(int s, ulong end_time_msc) {
   int streak = empty_copy_streak[s];
   if(streak == 1 || (streak % LOG_STREAK_INTERVAL) == 0) {
      PrintFormat(
         "[WARN] No new ticks copied for %s up to %s. Current logic will backfill from previous data or latest snapshot. streak=%d",
         SymbolForIdx(s),
         FormatTimeMsc(end_time_msc),
         streak
      );
   }
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

void ProcessTick(int s, MqlTick &t) {
   if(t.bid <= 0.0) {
      return;
   }

   if(!bar_started[s]) {
      cur_b[s].o = t.bid;
      cur_b[s].h = t.bid;
      cur_b[s].l = t.bid;
      cur_b[s].c = t.bid;
      cur_b[s].spread = 0.0;
      cur_b[s].tick_imbalance = 0.0;
      cur_b[s].time_msc = t.time_msc;
      ticks_in_bar[s] = 0;
      tick_imbalance_sum[s] = 0.0;
      bar_started[s] = true;
   }

   int tick_sign = UpdateTickSign(s, t.bid);
   cur_b[s].h = MathMax(cur_b[s].h, t.bid);
   cur_b[s].l = MathMin(cur_b[s].l, t.bid);
   cur_b[s].c = t.bid;
   cur_b[s].spread = t.ask - t.bid;
   ticks_in_bar[s]++;
   tick_imbalance_sum[s] += tick_sign;
}

void ProcessSymbolSnapshotToTime(int s, ulong end_time_msc) {
   if(last_tick_time[s] >= end_time_msc) {
      return;
   }

   MqlTick ticks[];
   ResetLastError();
   int count = CopyTicksRange(SymbolForIdx(s), ticks, COPY_TICKS_ALL, last_tick_time[s] + 1, end_time_msc);
   int err = GetLastError();

   if(count < 0) {
      tick_copy_error_streak[s]++;
      LogCopyFailure(SymbolForIdx(s), "CopyTicksRange", last_tick_time[s] + 1, end_time_msc, err, tick_copy_error_streak[s]);
      last_tick_time[s] = end_time_msc;
      return;
   }

   LogRecovery("Tick copy for " + SymbolForIdx(s), tick_copy_error_streak[s]);
   tick_copy_error_streak[s] = 0;

   if(count == 0) {
      empty_copy_streak[s]++;
      LogEmptyTickRange(s, end_time_msc);
      last_tick_time[s] = end_time_msc;
      return;
   }

   if(empty_copy_streak[s] > 0) {
      PrintFormat(
         "[INFO] Tick stream for %s recovered after %d empty aligned bars.",
         SymbolForIdx(s),
         empty_copy_streak[s]
      );
      empty_copy_streak[s] = 0;
   }

   for(int i = 0; i < count; i++) {
      if(ticks[i].bid > 0.0) {
         ProcessTick(s, ticks[i]);
      }
   }

   last_tick_time[s] = end_time_msc;
}

void UpdateIndicators(int s, Bar &b) {
   Bar p = history[s][0];
   double tr = (warmup_count[s] == 0)
      ? (b.h - b.l)
      : MathMax(b.h - b.l, MathMax(MathAbs(b.h - p.c), MathAbs(b.l - p.c)));

   if(warmup_count[s] < 14) {
      warmup_sum[s] += tr;
      warmup_count[s]++;
      b.atr14 = warmup_sum[s] / warmup_count[s];
   } else {
      double prev_atr = (p.atr14 > 0.0 ? p.atr14 : tr);
      b.atr14 = (tr - prev_atr) / 14.0 + prev_atr;
      warmup_count[s]++;
   }

   b.valid = (warmup_count[s] >= 16);
}

bool ShouldClosePrimaryBar(double &observed_abs_theta) {
   observed_abs_theta = 0.0;

   if(BAR_MODE == 0) {
      return (ticks_in_bar[0] >= TICK_DENSITY);
   }

   if(ticks_in_bar[0] < IMBALANCE_MIN_TICKS) {
      return false;
   }

   observed_abs_theta = MathAbs(tick_imbalance_sum[0]);
   return (observed_abs_theta >= primary_expected_abs_theta);
}

void UpdatePrimaryImbalanceThreshold(double observed_abs_theta) {
   if(BAR_MODE == 0 || observed_abs_theta <= 0.0) {
      return;
   }

   double alpha = 2.0 / (MathMax(1, IMBALANCE_EMA_SPAN) + 1.0);
   double observed = MathMax(2.0, observed_abs_theta);
   primary_expected_abs_theta = (1.0 - alpha) * primary_expected_abs_theta + alpha * observed;
}

void CloseBar() {
   for(int s = 0; s < 3; s++) {
      if(ticks_in_bar[s] == 0) {
         string symbol = SymbolForIdx(s);
         string bar_time = FormatTimeMsc(cur_b[0].time_msc);

         if(history[s][0].valid || history[s][0].c > 0.0) {
            double prev_c = history[s][0].c;
            cur_b[s].o = prev_c;
            cur_b[s].h = prev_c;
            cur_b[s].l = prev_c;
            cur_b[s].c = prev_c;
            cur_b[s].spread = history[s][0].spread;
            cur_b[s].tick_imbalance = 0.0;
            if(s > 0 && (empty_copy_streak[s] == 1 || (empty_copy_streak[s] % LOG_STREAK_INTERVAL) == 0)) {
               PrintFormat(
                  "[WARN] Closing synthetic %s bar at %s using previous close %.5f and spread %.5f.",
                  symbol,
                  bar_time,
                  prev_c,
                  history[s][0].spread
               );
            }
         } else {
            MqlTick fallback;
            ResetLastError();
            if(SymbolInfoTick(symbol, fallback) && fallback.bid > 0.0) {
               cur_b[s].o = fallback.bid;
               cur_b[s].h = fallback.bid;
               cur_b[s].l = fallback.bid;
               cur_b[s].c = fallback.bid;
               cur_b[s].spread = fallback.ask - fallback.bid;
               cur_b[s].tick_imbalance = 0.0;
               PrintFormat(
                  "[WARN] Closing synthetic %s bar at %s using snapshot bid/ask %.5f/%.5f because no aligned ticks were available.",
                  symbol,
                  bar_time,
                  fallback.bid,
                  fallback.ask
               );
            } else {
               PrintFormat(
                  "[ERROR] Unable to build %s bar at %s: no aligned ticks, no previous bar, and SymbolInfoTick failed (err=%d).",
                  symbol,
                  bar_time,
                  GetLastError()
               );
            }
         }

         cur_b[s].time_msc = cur_b[0].time_msc;
      } else {
         cur_b[s].tick_imbalance = tick_imbalance_sum[s] / ticks_in_bar[s];
      }

      UpdateIndicators(s, cur_b[s]);

      for(int i = HISTORY_SIZE - 1; i > 0; i--) {
         history[s][i] = history[s][i - 1];
      }
      history[s][0] = cur_b[s];

      ticks_in_bar[s] = 0;
      tick_imbalance_sum[s] = 0.0;
      bar_started[s] = false;
   }
}

void OnTick() {
   MqlTick gold_ticks[];
   ResetLastError();
   int count = CopyTicks(_Symbol, gold_ticks, COPY_TICKS_ALL, last_tick_time[0] + 1, 100000);
   int err = GetLastError();
   if(count < 0) {
      main_tick_copy_error_streak++;
      LogCopyFailure(_Symbol, "CopyTicks", last_tick_time[0] + 1, last_tick_time[0] + 1, err, main_tick_copy_error_streak);
      return;
   }

   LogRecovery("Main symbol tick copy", main_tick_copy_error_streak);
   main_tick_copy_error_streak = 0;

   if(count == 0) {
      return;
   }

   for(int i = 0; i < count; i++) {
      if(gold_ticks[i].bid <= 0.0) {
         continue;
      }

      ProcessTick(0, gold_ticks[i]);
      last_tick_time[0] = gold_ticks[i].time_msc;

      double observed_abs_theta = 0.0;
      if(ShouldClosePrimaryBar(observed_abs_theta)) {
         ProcessSymbolSnapshotToTime(1, last_tick_time[0]);
         ProcessSymbolSnapshotToTime(2, last_tick_time[0]);
         CloseBar();
         UpdatePrimaryImbalanceThreshold(observed_abs_theta);

         if(history[0][REQUIRED_HISTORY_INDEX].valid &&
            history[1][REQUIRED_HISTORY_INDEX].valid &&
            history[2][REQUIRED_HISTORY_INDEX].valid) {
            Predict();
         }
      }
   }
}

void LoadHistory() {
   Print("[INFO] Pre-loading history...");

   ulong start_time_msc = (TimeCurrent() - 86400 * 3) * 1000ULL;
   MqlTick hist_ticks[];
   ResetLastError();
   int copied = CopyTicks(_Symbol, hist_ticks, COPY_TICKS_ALL, start_time_msc, 250000);
   int err = GetLastError();

   if(copied <= 0) {
      PrintFormat(
         "[WARN] Failed to load history ticks for %s from %s. copied=%d err=%d. Trying 1 day...",
         _Symbol,
         FormatTimeMsc(start_time_msc),
         copied,
         err
      );
      start_time_msc = (TimeCurrent() - 86400) * 1000ULL;
      ResetLastError();
      copied = CopyTicks(_Symbol, hist_ticks, COPY_TICKS_ALL, start_time_msc, 250000);
      err = GetLastError();
   }

   if(copied <= 0) {
      PrintFormat(
         "[ERROR] No history ticks found for %s. copied=%d err=%d start=%s",
         _Symbol,
         copied,
         err,
         FormatTimeMsc(start_time_msc)
      );
      return;
   }

   last_tick_time[0] = hist_ticks[0].time_msc - 1;
   last_tick_time[1] = hist_ticks[0].time_msc - 1;
   last_tick_time[2] = hist_ticks[0].time_msc - 1;

   for(int i = 0; i < copied; i++) {
      if(hist_ticks[i].bid <= 0.0) {
         continue;
      }

      ProcessTick(0, hist_ticks[i]);
      last_tick_time[0] = hist_ticks[i].time_msc;

      double observed_abs_theta = 0.0;
      if(ShouldClosePrimaryBar(observed_abs_theta)) {
         ProcessSymbolSnapshotToTime(1, last_tick_time[0]);
         ProcessSymbolSnapshotToTime(2, last_tick_time[0]);
         CloseBar();
         UpdatePrimaryImbalanceThreshold(observed_abs_theta);
      }
   }

   Print("[INFO] History loaded. Buffer status: ", history[0][REQUIRED_HISTORY_INDEX].valid ? "VALID" : "INCOMPLETE");
}

float ScaleAndClip(float value, int feature_index) {
   float iqr = (iqrs[feature_index] > 1e-6f ? iqrs[feature_index] : 1.0f);
   float raw = (value - medians[feature_index]) / iqr;
   return MathMax(-10.0f, MathMin(10.0f, raw));
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
   if(window <= 1) {
      return 0.0;
   }

   double vals[32];
   double mean = 0.0;
   for(int i = 0; i < window; i++) {
      vals[i] = LogReturnAt(s, h + i);
      mean += vals[i];
   }
   mean /= window;

   double var = 0.0;
   for(int i = 0; i < window; i++) {
      double diff = vals[i] - mean;
      var += diff * diff;
   }
   return MathSqrt(var / window);
}

bool UseRichFeatures() {
   return FEATURE_SET != 0;
}

double TimeOfDaySeconds(ulong time_msc) {
   return (double)((time_msc / 1000ULL) % 86400ULL);
}

void ExtractGoldFeatures(int h, float &f[]) {
   Bar b = history[0][h];
   Bar bp = history[0][h + 1];
   double cl = b.c;
   double broker_h = (double)((b.time_msc / 3600000ULL) % 24);

   f[0]  = ScaleAndClip((float)LogReturnAt(0, h), 0);
   f[1]  = ScaleAndClip((float)SafeLogRatio(b.h, bp.c), 1);
   f[2]  = ScaleAndClip((float)SafeLogRatio(b.l, bp.c), 2);
   f[3]  = ScaleAndClip((float)(b.spread / (cl + 1e-10)), 3);
   f[4]  = ScaleAndClip((float)((double)(b.time_msc - bp.time_msc) / 1000.0), 4);
   f[5]  = ScaleAndClip((float)((cl - b.l) / (b.h - b.l + 1e-8)), 5);
   f[6]  = ScaleAndClip((float)(b.atr14 / (cl + 1e-10)), 6);
   f[7]  = ScaleAndClip((float)RollingStdReturn(0, h, 4), 7);
   f[8]  = ScaleAndClip((float)RollingStdReturn(0, h, 16), 8);
   f[9]  = ScaleAndClip((float)ReturnOverBars(0, h, 8), 9);
   f[10] = ScaleAndClip((float)b.tick_imbalance, 10);
   f[11] = ScaleAndClip((float)MathSin(2.0 * M_PI * broker_h / 24.0), 11);
   f[12] = ScaleAndClip((float)MathCos(2.0 * M_PI * broker_h / 24.0), 12);
}

void ExtractAuxFeatures(int s, int h, float &f[]) {
   Bar b = history[s][h];
   double cl = b.c;
   int base = (s == 1 ? 13 : 18);

   f[0] = ScaleAndClip((float)LogReturnAt(s, h), base + 0);
   f[1] = ScaleAndClip((float)LogReturnAt(s, h + 1), base + 1);
   f[2] = ScaleAndClip((float)((cl - b.l) / (b.h - b.l + 1e-8)), base + 2);
   f[3] = ScaleAndClip((float)(b.atr14 / (cl + 1e-10)), base + 3);
   f[4] = ScaleAndClip((float)ReturnOverBars(s, h, 8), base + 4);
}

void ExtractRawSymbolFeatures(int s, int h, float &f[]) {
   Bar b = history[s][h];
   int base = s * RAW_SYMBOL_FEATURE_COUNT;

   f[0] = ScaleAndClip((float)b.c, base + 0);
   f[1] = ScaleAndClip((float)(b.c + b.spread), base + 1);
   f[2] = ScaleAndClip((float)TimeOfDaySeconds(b.time_msc), base + 2);
}

void CalibratedSoftmax(const float &logits[], double temperature, float &probs[]) {
   double temp = MathMax(temperature, 1e-3);
   double scaled0 = logits[0] / temp;
   double scaled1 = logits[1] / temp;
   double scaled2 = logits[2] / temp;
   double max_logit = MathMax(scaled0, MathMax(scaled1, scaled2));

   double e0 = MathExp(scaled0 - max_logit);
   double e1 = MathExp(scaled1 - max_logit);
   double e2 = MathExp(scaled2 - max_logit);
   double sum = e0 + e1 + e2;

   probs[0] = (float)(e0 / sum);
   probs[1] = (float)(e1 / sum);
   probs[2] = (float)(e2 / sum);
}

float MetaProbability(const float &meta_features[]) {
   double z = meta_bias;
   for(int i = 0; i < META_FEATURE_COUNT; i++) {
      z += meta_weights[i] * meta_features[i];
   }
   return (float)(1.0 / (1.0 + MathExp(-z)));
}

void BuildMetaFeatures(const float &probs[], float &meta_features[]) {
   float top1 = MathMax(probs[0], MathMax(probs[1], probs[2]));
   float top2 = 0.0f;
   if(top1 == probs[0]) {
      top2 = MathMax(probs[1], probs[2]);
   } else if(top1 == probs[1]) {
      top2 = MathMax(probs[0], probs[2]);
   } else {
      top2 = MathMax(probs[0], probs[1]);
   }

   float entropy = 0.0f;
   for(int i = 0; i < 3; i++) {
      float p = MathMax(probs[i], 1e-6f);
      entropy -= p * (float)MathLog(p);
   }

   int last_offset = (SEQ_LEN - 1) * MODEL_FEATURE_COUNT;
   meta_features[0] = probs[0];
   meta_features[1] = probs[1];
   meta_features[2] = probs[2];
   meta_features[3] = top1;
   meta_features[4] = top1 - top2;
   meta_features[5] = entropy;
   for(int i = 0; i < META_EXTRA_FEATURE_COUNT; i++) {
      int feature_index = meta_input_indices[i];
      if(feature_index >= 0 && feature_index < MODEL_FEATURE_COUNT) {
         meta_features[6 + i] = input_data[last_offset + feature_index];
      } else {
         meta_features[6 + i] = 0.0f;
      }
   }
}

void Predict() {
   bool rich_features = UseRichFeatures();
   for(int i = 0; i < SEQ_LEN; i++) {
      int h = SEQ_LEN - 1 - i;
      int offset = i * MODEL_FEATURE_COUNT;
      if(rich_features) {
         float gold_f[MAX_GOLD_FEATURE_COUNT];
         float aux_usdx[MAX_AUX_FEATURE_COUNT];
         float aux_usdjpy[MAX_AUX_FEATURE_COUNT];

         ExtractGoldFeatures(h, gold_f);
         ExtractAuxFeatures(1, h, aux_usdx);
         ExtractAuxFeatures(2, h, aux_usdjpy);

         for(int k = 0; k < MAX_GOLD_FEATURE_COUNT; k++) {
            input_data[offset + k] = gold_f[k];
         }
         for(int k = 0; k < MAX_AUX_FEATURE_COUNT; k++) {
            input_data[offset + MAX_GOLD_FEATURE_COUNT + k] = aux_usdx[k];
            input_data[offset + MAX_GOLD_FEATURE_COUNT + MAX_AUX_FEATURE_COUNT + k] = aux_usdjpy[k];
         }
      } else {
         float raw_gold[RAW_SYMBOL_FEATURE_COUNT];
         float raw_usdx[RAW_SYMBOL_FEATURE_COUNT];
         float raw_usdjpy[RAW_SYMBOL_FEATURE_COUNT];

         ExtractRawSymbolFeatures(0, h, raw_gold);
         ExtractRawSymbolFeatures(1, h, raw_usdx);
         ExtractRawSymbolFeatures(2, h, raw_usdjpy);

         for(int k = 0; k < RAW_SYMBOL_FEATURE_COUNT; k++) {
            input_data[offset + k] = raw_gold[k];
            input_data[offset + RAW_SYMBOL_FEATURE_COUNT + k] = raw_usdx[k];
            input_data[offset + (2 * RAW_SYMBOL_FEATURE_COUNT) + k] = raw_usdjpy[k];
         }
      }
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      onnx_error_streak++;
      if(onnx_error_streak == 1 || (onnx_error_streak % LOG_STREAK_INTERVAL) == 0) {
         PrintFormat("[ERROR] OnnxRun failed. err=%d streak=%d", GetLastError(), onnx_error_streak);
      }
      return;
   }

   LogRecovery("OnnxRun", onnx_error_streak);
   onnx_error_streak = 0;

   float probs[3];
   float meta_features[META_FEATURE_COUNT];
   CalibratedSoftmax(output_data, TEMPERATURE, probs);

   int sig = ArrayMaximum(probs);
   if(sig <= 0) {
      return;
   }

   if(probs[sig] < PRIMARY_CONFIDENCE) {
      return;
   }

   BuildMetaFeatures(probs, meta_features);
   float meta_prob = MetaProbability(meta_features);
   if(meta_prob < META_THRESHOLD) {
      return;
   }

   Execute(sig);
}

void Execute(int sig) {
   if(PositionSelect(_Symbol)) {
      return;
   }

   double p  = (sig == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = (sig == 1) ? (p - history[0][0].atr14 * SL_MULTIPLIER) : (p + history[0][0].atr14 * SL_MULTIPLIER);
   double tp = (sig == 1) ? (p + history[0][0].atr14 * TP_MULTIPLIER) : (p - history[0][0].atr14 * TP_MULTIPLIER);

   double min_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(MathAbs(p - sl) < min_dist || MathAbs(tp - p) < min_dist) {
      Print("[WARN] Stop/TP too close to price, skipping trade.");
      return;
   }

   trade.PositionOpen(_Symbol, (sig == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL), LOT_SIZE, p, sl, tp);
}
