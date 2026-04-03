#include <Trade\Trade.mqh>
#include "gold_shared_config.mqh"
#include "gold_model_config.mqh"

#resource "\\Experts\\nn\\gold\\gold_mamba.onnx" as uchar model_buffer[]

#ifndef MODEL_USE_ATR_RISK
#define MODEL_USE_ATR_RISK 1
#endif

#define INPUT_BUFFER_SIZE (SEQ_LEN * MODEL_FEATURE_COUNT)
#define HISTORY_SIZE (REQUIRED_HISTORY_INDEX + 1)
#define PRIMARY_BAR_MILLISECONDS ((ulong)PRIMARY_BAR_SECONDS * 1000)

input bool R = (MODEL_USE_ATR_RISK == 0);
input double FIXED_MOVE = DEFAULT_FIXED_MOVE;
input double SL_MULTIPLIER = DEFAULT_SL_MULTIPLIER;
input double TP_MULTIPLIER = DEFAULT_TP_MULTIPLIER;
input double LOT_SIZE = DEFAULT_LOT_SIZE;
input int MAGIC_NUMBER = 777777;
input bool DEBUG_LOG = true;

long onnx_handle = INVALID_HANDLE;
CTrade trade;

struct Bar {
   double o;
   double h;
   double l;
   double c;
   double spread;
   double tick_imbalance;
   double atr_feature;
   double atr_trade;
   ulong time_msc;
   bool valid;
};

Bar history[HISTORY_SIZE];
Bar current_bar;
int ticks_in_bar = 0;
bool bar_started = false;
ulong current_bar_bucket = 0;
ulong last_tick_time = 0;
double tick_imbalance_sum = 0.0;
double last_bid = 0.0;
int last_sign = 1;
int warmup_count = 0;
double warmup_sum_feature = 0.0;
double warmup_sum_trade = 0.0;
float input_data[INPUT_BUFFER_SIZE];
float output_data[3];
int prediction_count = 0;
int hold_skip_count = 0;
int confidence_skip_count = 0;
int position_skip_count = 0;
int stops_too_close_skip_count = 0;
int trade_open_failed_count = 0;
int trades_opened_count = 0;
int closed_trade_count = 0;
int closed_win_count = 0;
int closed_loss_count = 0;
double realized_pnl = 0.0;

int UpdateTickSign(double bid);
ulong BarBucket(ulong time_msc);
ulong BarOpenTime(ulong bar_bucket);
void StartBar(MqlTick &tick, ulong bar_bucket);
bool RollBarIfNeeded(ulong next_bar_bucket, int &closed_tick_count);
void ProcessTick(MqlTick &tick, ulong bar_bucket);
void UpdateIndicators(Bar &bar);
void CloseBar();
void LoadHistory();
float ScaleAndClip(float value, int feature_index);
double SafeLogRatio(double num, double den);
double LogReturnAt(int h);
double ReturnOverBars(int h, int bars);
double RollingStdReturn(int h, int window);
void ExtractFeatures(int h, float &features[]);
void Softmax(const float &logits[], float &probs[]);
void Predict();
void Execute(int signal);
void DebugPrint(string message);
string SignalName(int signal);
double StopDistance();
double TargetDistance();
void PrintRunSummary();

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

   for(int i = 0; i < HISTORY_SIZE; i++) {
      history[i].valid = false;
   }

   ArrayInitialize(input_data, 0.0f);
   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   DebugPrint(
      StringFormat(
         "init seq=%d horizon=%d history=%d bar_seconds=%d risk_mode=%s fixed_move=%.2f sl=%.2f tp=%.2f lot=%.2f primary_conf=%.2f",
         SEQ_LEN,
         TARGET_HORIZON,
         REQUIRED_HISTORY_INDEX,
         PRIMARY_BAR_SECONDS,
         (R ? "FIXED" : "ATR"),
         FIXED_MOVE,
         SL_MULTIPLIER,
         TP_MULTIPLIER,
         LOT_SIZE,
         PRIMARY_CONFIDENCE
      )
   );

   MqlTick tick;
   if(SymbolInfoTick(_Symbol, tick)) {
      last_tick_time = tick.time_msc;
   } else {
      last_tick_time = TimeCurrent() * 1000ULL;
   }

   LoadHistory();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   PrintRunSummary();
   if(onnx_handle != INVALID_HANDLE) {
      OnnxRelease(onnx_handle);
   }
}

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result) {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.deal == 0) {
      return;
   }
   if(!HistoryDealSelect(trans.deal)) {
      return;
   }
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol) {
      return;
   }
   if((int)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != MAGIC_NUMBER) {
      return;
   }

   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY && entry != DEAL_ENTRY_INOUT) {
      return;
   }

   double pnl =
      HistoryDealGetDouble(trans.deal, DEAL_PROFIT) +
      HistoryDealGetDouble(trans.deal, DEAL_SWAP) +
      HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
   realized_pnl += pnl;
   closed_trade_count++;
   if(pnl > 0.0) {
      closed_win_count++;
   } else if(pnl < 0.0) {
      closed_loss_count++;
   }
}

void DebugPrint(string message) {
   if(DEBUG_LOG) {
      Print("[DEBUG] ", message);
   }
}

string SignalName(int signal) {
   if(signal == 1) {
      return "BUY";
   }
   if(signal == 2) {
      return "SELL";
   }
   return "HOLD";
}

ulong BarBucket(ulong time_msc) {
   return time_msc / PRIMARY_BAR_MILLISECONDS;
}

ulong BarOpenTime(ulong bar_bucket) {
   return bar_bucket * PRIMARY_BAR_MILLISECONDS;
}

void StartBar(MqlTick &tick, ulong bar_bucket) {
   current_bar.o = tick.bid;
   current_bar.h = tick.bid;
   current_bar.l = tick.bid;
   current_bar.c = tick.bid;
   current_bar.spread = tick.ask - tick.bid;
   current_bar.tick_imbalance = 0.0;
   current_bar.atr_feature = 0.0;
   current_bar.atr_trade = 0.0;
   current_bar.time_msc = BarOpenTime(bar_bucket);
   current_bar.valid = false;
   ticks_in_bar = 0;
   tick_imbalance_sum = 0.0;
   current_bar_bucket = bar_bucket;
   bar_started = true;
}

bool RollBarIfNeeded(ulong next_bar_bucket, int &closed_tick_count) {
   closed_tick_count = 0;
   if(!bar_started || next_bar_bucket == current_bar_bucket) {
      return false;
   }

   closed_tick_count = ticks_in_bar;
   CloseBar();
   return true;
}

double StopDistance() {
   if(R) {
      return FIXED_MOVE;
   }
   return history[0].atr_trade * SL_MULTIPLIER;
}

double TargetDistance() {
   if(R) {
      return FIXED_MOVE;
   }
   return history[0].atr_trade * TP_MULTIPLIER;
}

void PrintRunSummary() {
   Print(
      StringFormat(
         "[SUMMARY] risk_mode=%s fixed_move=%.2f predictions=%d hold_skips=%d confidence_skips=%d position_skips=%d stops_too_close=%d open_failures=%d trades_opened=%d trades_closed=%d wins=%d losses=%d realized_pnl=%.2f balance=%.2f",
         (R ? "FIXED" : "ATR"),
         FIXED_MOVE,
         prediction_count,
         hold_skip_count,
         confidence_skip_count,
         position_skip_count,
         stops_too_close_skip_count,
         trade_open_failed_count,
         trades_opened_count,
         closed_trade_count,
         closed_win_count,
         closed_loss_count,
         realized_pnl,
         AccountInfoDouble(ACCOUNT_BALANCE)
      )
   );
}

int UpdateTickSign(double bid) {
   int sign = last_sign;
   if(last_bid <= 0.0) {
      sign = 1;
   } else {
      double diff = bid - last_bid;
      if(diff > 0.0) {
         sign = 1;
      } else if(diff < 0.0) {
         sign = -1;
      }
   }

   last_bid = bid;
   last_sign = sign;
   return sign;
}

void ProcessTick(MqlTick &tick, ulong bar_bucket) {
   if(tick.bid <= 0.0) {
      return;
   }

   if(!bar_started) {
      StartBar(tick, bar_bucket);
   }

   int tick_sign = UpdateTickSign(tick.bid);
   current_bar.h = MathMax(current_bar.h, tick.bid);
   current_bar.l = MathMin(current_bar.l, tick.bid);
   current_bar.c = tick.bid;
   current_bar.spread = tick.ask - tick.bid;
   ticks_in_bar++;
   tick_imbalance_sum += tick_sign;
}

void UpdateIndicators(Bar &bar) {
   Bar prev = history[0];
   double tr = (warmup_count == 0)
      ? (bar.h - bar.l)
      : MathMax(bar.h - bar.l, MathMax(MathAbs(bar.h - prev.c), MathAbs(bar.l - prev.c)));
   int next_count = warmup_count + 1;

   if(next_count <= FEATURE_ATR_PERIOD) {
      warmup_sum_feature += tr;
      bar.atr_feature = warmup_sum_feature / next_count;
   } else {
      double prev_atr_feature = (prev.atr_feature > 0.0 ? prev.atr_feature : tr);
      bar.atr_feature = prev_atr_feature + (tr - prev_atr_feature) / FEATURE_ATR_PERIOD;
   }

   if(next_count <= TARGET_ATR_PERIOD) {
      warmup_sum_trade += tr;
      bar.atr_trade = warmup_sum_trade / next_count;
   } else {
      double prev_atr_trade = (prev.atr_trade > 0.0 ? prev.atr_trade : tr);
      bar.atr_trade = prev_atr_trade + (tr - prev_atr_trade) / TARGET_ATR_PERIOD;
   }

   warmup_count = next_count;
   bar.valid = (warmup_count >= WARMUP_BARS);
}

void CloseBar() {
   current_bar.tick_imbalance = tick_imbalance_sum / MathMax(1, ticks_in_bar);
   UpdateIndicators(current_bar);

   for(int i = HISTORY_SIZE - 1; i > 0; i--) {
      history[i] = history[i - 1];
   }
   history[0] = current_bar;

   ticks_in_bar = 0;
   tick_imbalance_sum = 0.0;
   current_bar_bucket = 0;
   bar_started = false;
}

void OnTick() {
   MqlTick ticks[];
   int count = CopyTicks(_Symbol, ticks, COPY_TICKS_ALL, last_tick_time + 1, 100000);
   if(count <= 0) {
      return;
   }

   for(int i = 0; i < count; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }

      ulong tick_bucket = BarBucket(ticks[i].time_msc);
      int closed_tick_count = 0;
      if(RollBarIfNeeded(tick_bucket, closed_tick_count)) {
         DebugPrint(
            StringFormat(
               "bar closed seconds=%d ticks=%d atr_trade=%.5f close=%.5f",
               PRIMARY_BAR_SECONDS,
               closed_tick_count,
               history[0].atr_trade,
               history[0].c
            )
         );
         if(history[REQUIRED_HISTORY_INDEX].valid) {
            Predict();
         } else {
            DebugPrint(
               StringFormat(
                  "history not ready yet: need index %d valid before predicting",
                  REQUIRED_HISTORY_INDEX
               )
            );
         }
      }

      ProcessTick(ticks[i], tick_bucket);
      last_tick_time = ticks[i].time_msc;
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

   last_tick_time = ticks[0].time_msc - 1;
   for(int i = 0; i < copied; i++) {
      if(ticks[i].bid <= 0.0) {
         continue;
      }

      ulong tick_bucket = BarBucket(ticks[i].time_msc);
      int closed_tick_count = 0;
      RollBarIfNeeded(tick_bucket, closed_tick_count);
      ProcessTick(ticks[i], tick_bucket);
      last_tick_time = ticks[i].time_msc;
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

double LogReturnAt(int h) {
   return SafeLogRatio(history[h].c, history[h + 1].c);
}

double ReturnOverBars(int h, int bars) {
   return SafeLogRatio(history[h].c, history[h + bars].c);
}

double RollingStdReturn(int h, int window) {
   double values[RV_PERIOD];
   double mean = 0.0;
   for(int i = 0; i < window; i++) {
      values[i] = LogReturnAt(h + i);
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

void ExtractFeatures(int h, float &features[]) {
   Bar bar = history[h];
   Bar prev = history[h + 1];
   double close = bar.c;

   features[FEATURE_IDX_RET1] = ScaleAndClip((float)LogReturnAt(h), FEATURE_IDX_RET1);
   features[FEATURE_IDX_HIGH_REL_PREV] = ScaleAndClip((float)SafeLogRatio(bar.h, prev.c), FEATURE_IDX_HIGH_REL_PREV);
   features[FEATURE_IDX_LOW_REL_PREV] = ScaleAndClip((float)SafeLogRatio(bar.l, prev.c), FEATURE_IDX_LOW_REL_PREV);
   features[FEATURE_IDX_SPREAD_REL] = ScaleAndClip((float)(bar.spread / (close + 1e-10)), FEATURE_IDX_SPREAD_REL);
   features[FEATURE_IDX_CLOSE_IN_RANGE] = ScaleAndClip(
      (float)((close - bar.l) / (bar.h - bar.l + 1e-8)),
      FEATURE_IDX_CLOSE_IN_RANGE
   );
   features[FEATURE_IDX_ATR_REL] = ScaleAndClip((float)(bar.atr_feature / (close + 1e-10)), FEATURE_IDX_ATR_REL);
   features[FEATURE_IDX_RV] = ScaleAndClip((float)RollingStdReturn(h, RV_PERIOD), FEATURE_IDX_RV);
   features[FEATURE_IDX_RETURN_N] = ScaleAndClip((float)ReturnOverBars(h, RETURN_PERIOD), FEATURE_IDX_RETURN_N);
   features[FEATURE_IDX_TICK_IMBALANCE] = ScaleAndClip((float)bar.tick_imbalance, FEATURE_IDX_TICK_IMBALANCE);
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

   float probs[3];
   Softmax(output_data, probs);
   int signal = ArrayMaximum(probs);
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

void Execute(int signal) {
   if(PositionSelect(_Symbol)) {
      position_skip_count++;
      DebugPrint("skip trade: a position is already open on this symbol");
      return;
   }

   double price = (signal == 1) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl_distance = StopDistance();
   double tp_distance = TargetDistance();
   if(sl_distance <= 0.0 || tp_distance <= 0.0) {
      trade_open_failed_count++;
      DebugPrint(
         StringFormat(
            "skip trade: invalid risk distances sl_distance=%.5f tp_distance=%.5f",
            sl_distance,
            tp_distance
         )
      );
      return;
   }
   double sl = (signal == 1)
      ? (price - sl_distance)
      : (price + sl_distance);
   double tp = (signal == 1)
      ? (price + tp_distance)
      : (price - tp_distance);

   double min_dist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(MathAbs(price - sl) < min_dist || MathAbs(tp - price) < min_dist) {
      stops_too_close_skip_count++;
      DebugPrint(
         StringFormat(
            "skip trade: stops too close price=%.5f sl=%.5f tp=%.5f min_dist=%.5f",
            price,
            sl,
            tp,
            min_dist
         )
      );
      return;
   }

   bool opened = trade.PositionOpen(_Symbol, (signal == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL), LOT_SIZE, price, sl, tp);
   if(opened) {
      trades_opened_count++;
      DebugPrint(
         StringFormat(
            "trade opened %s lot=%.2f price=%.5f sl=%.5f tp=%.5f",
            SignalName(signal),
            LOT_SIZE,
            price,
            sl,
            tp
         )
      );
   } else {
      trade_open_failed_count++;
      DebugPrint(
         StringFormat(
            "trade open failed %s retcode=%d last_error=%d",
            SignalName(signal),
            trade.ResultRetcode(),
            GetLastError()
         )
      );
   }
}
