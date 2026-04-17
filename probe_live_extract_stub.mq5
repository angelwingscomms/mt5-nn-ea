#include <Trade\Trade.mqh>
// @active-model-reference begin
#define ACTIVE_MODEL_SYMBOL "XAUUSD"
#define ACTIVE_MODEL_VERSION "16_04_2026-09_42__55-xau-default-fail"
#include "symbols/xauusd/models/16_04_2026-09_42__55-xau-default-fail/config.mqh"
#resource "symbols/xauusd/models/16_04_2026-09_42__55-xau-default-fail/model.onnx" as uchar model_buffer[]
// @active-model-reference end

#ifndef MODEL_USE_ATR_RISK
#define MODEL_USE_ATR_RISK 1
#endif

#ifndef MODEL_USE_FIXED_TIME_BARS
#define MODEL_USE_FIXED_TIME_BARS 0
#endif

#ifndef MODEL_USE_FIXED_TICK_BARS
#define MODEL_USE_FIXED_TICK_BARS 0
#endif

#define INPUT_BUFFER_SIZE (SEQ_LEN * MODEL_FEATURE_COUNT)
#define HISTORY_SIZE (REQUIRED_HISTORY_INDEX + 1)
#define PRIMARY_BAR_MILLISECONDS ((ulong)PRIMARY_BAR_SECONDS * 1000)

input bool R = (MODEL_USE_ATR_RISK == 0);
input double FIXED_MOVE = DEFAULT_FIXED_MOVE;
input double SL_MULTIPLIER = DEFAULT_SL_MULTIPLIER;
input double TP_MULTIPLIER = DEFAULT_TP_MULTIPLIER;
input double LOT_SIZE = DEFAULT_LOT_SIZE;
input double LOT_SIZE_CAP = DEFAULT_LOT_SIZE_CAP;
input double RISK_PERCENT = DEFAULT_RISK_PERCENT;
input double BROKER_MIN_LOT_SIZE = DEFAULT_BROKER_MIN_LOT_SIZE;
input bool USE_BROKER_MIN_LOT = USE_BROKER_MIN_LOT_SIZE;
input bool USE_LOT_SIZE_CAP_INPUT = USE_LOT_SIZE_CAP;
input bool USE_RISK_PERCENT_INPUT = USE_RISK_PERCENT;
input int MAGIC_NUMBER = 777777;
input bool DEBUG_LOG = true;
input string USDX_SYMBOL = "$USDX";
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
   int tick_count;
   double usdx_bid;
   double usdjpy_bid;
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
bool usdx_available = false;
bool usdjpy_available = false;
double last_usdx_bid = 0.0;
double last_usdjpy_bid = 0.0;
double primary_expected_abs_theta = 60.0;
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
int volume_skip_count = 0;
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
void StartImbalanceBar(MqlTick &tick);
bool RollFixedTimeBarIfNeeded(ulong next_bar_bucket, int &closed_tick_count);
void ProcessTick(MqlTick &tick, ulong bar_bucket);
void UpdateIndicators(Bar &bar);
bool ShouldClosePrimaryBar(double &observed_abs_theta);
void UpdatePrimaryImbalanceThreshold(double observed_abs_theta);
void CloseBar();
void LoadHistory();
float ScaleAndClip(float value, int feature_index);
double SafeLogRatio(double num, double den);
double LogReturnAt(int h);
double ReturnOverBars(int h, int bars);
double RollingStdReturn(int h, int window);
double MeanClose(int h, int window);
double StdClose(int h, int window);
double MaxHigh(int h, int window);
double MinLow(int h, int window);
double MeanTickCount(int h, int window);
double StdTickCount(int h, int window);
double MeanTickImbalance(int h, int window);
double MeanSpreadRel(int h, int window);
double StdSpreadRel(int h, int window);
double MeanAtrFeature(int h, int window);
double SimpleRsi(int h, int period);
double StochK(int h, int period);
double StochD(int h, int period);
void ExtractFeatures(int h, float &features[]);
void Softmax(const float &logits[], float &probs[]);
void Predict();
void Execute(int signal);
void DebugPrint(string message);
string SignalName(int signal);
double StopDistance();
double TargetDistance();
double ResolveMinimumVolume();
double NormalizeVolume(double volume);
double CalculateTradeVolume(int signal, double price, double sl);
void PrintRunSummary();
double ResolveAuxBid(string symbol, bool &available, double &last_value, double fallback);


#include "probes/probe_live_extract_stub_functions/OnInit.mqh"
#include "probes/probe_live_extract_stub_functions/OnDeinit.mqh"
#include "probes/probe_live_extract_stub_functions/OnTradeTransaction.mqh"
#include "probes/probe_live_extract_stub_functions/DebugPrint.mqh"
#include "probes/probe_live_extract_stub_functions/SignalName.mqh"
#include "probes/probe_live_extract_stub_functions/BarBucket.mqh"
#include "probes/probe_live_extract_stub_functions/BarOpenTime.mqh"
#include "probes/probe_live_extract_stub_functions/StartBar.mqh"
#include "probes/probe_live_extract_stub_functions/StartImbalanceBar.mqh"
#include "probes/probe_live_extract_stub_functions/RollFixedTimeBarIfNeeded.mqh"
#include "probes/probe_live_extract_stub_functions/StopDistance.mqh"
#include "probes/probe_live_extract_stub_functions/TargetDistance.mqh"
#include "probes/probe_live_extract_stub_functions/ResolveMinimumVolume.mqh"
#include "probes/probe_live_extract_stub_functions/NormalizeVolume.mqh"
#include "probes/probe_live_extract_stub_functions/CalculateTradeVolume.mqh"
#include "probes/probe_live_extract_stub_functions/PrintRunSummary.mqh"
#include "probes/probe_live_extract_stub_functions/UpdateTickSign.mqh"
#include "probes/probe_live_extract_stub_functions/ProcessTick.mqh"
#include "probes/probe_live_extract_stub_functions/ResolveAuxBid.mqh"
#include "probes/probe_live_extract_stub_functions/UpdateIndicators.mqh"
#include "probes/probe_live_extract_stub_functions/ShouldClosePrimaryBar.mqh"
#include "probes/probe_live_extract_stub_functions/UpdatePrimaryImbalanceThreshold.mqh"
#include "probes/probe_live_extract_stub_functions/CloseBar.mqh"
#include "probes/probe_live_extract_stub_functions/OnTick.mqh"
#include "probes/probe_live_extract_stub_functions/LoadHistory.mqh"
#include "probes/probe_live_extract_stub_functions/ScaleAndClip.mqh"
#include "probes/probe_live_extract_stub_functions/SafeLogRatio.mqh"
#include "probes/probe_live_extract_stub_functions/LogReturnAt.mqh"
#include "probes/probe_live_extract_stub_functions/ReturnOverBars.mqh"
#include "probes/probe_live_extract_stub_functions/RollingStdReturn.mqh"
#include "probes/probe_live_extract_stub_functions/MeanClose.mqh"
#include "probes/probe_live_extract_stub_functions/StdClose.mqh"
#include "probes/probe_live_extract_stub_functions/MaxHigh.mqh"
#include "probes/probe_live_extract_stub_functions/MinLow.mqh"
#include "probes/probe_live_extract_stub_functions/MeanTickCount.mqh"
#include "probes/probe_live_extract_stub_functions/StdTickCount.mqh"
#include "probes/probe_live_extract_stub_functions/MeanTickImbalance.mqh"
#include "probes/probe_live_extract_stub_functions/MeanSpreadRel.mqh"
#include "probes/probe_live_extract_stub_functions/StdSpreadRel.mqh"
#include "probes/probe_live_extract_stub_functions/MeanAtrFeature.mqh"
#include "probes/probe_live_extract_stub_functions/SimpleRsi.mqh"
#include "probes/probe_live_extract_stub_functions/StochK.mqh"
#include "probes/probe_live_extract_stub_functions/StochD.mqh"
#include "probes/probe_live_extract_stub_functions/ExtractFeatures.mqh"
#include "probes/probe_live_extract_stub_functions/Softmax.mqh"
#include "probes/probe_live_extract_stub_functions/Predict.mqh"
#include "probes/probe_live_extract_stub_functions/Execute.mqh"
