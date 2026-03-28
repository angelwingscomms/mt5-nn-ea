//+------------------------------------------------------------------+
//|                                              Live_Bitcoin.mq5     |
//|                                  Copyright 2026, Bitcoin Algo     |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

// 1. RESOURCE & INPUTS
#resource "\\Experts\\nn\\bitcoin\\bitcoin_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      
input double TP_MULTIPLIER = 2.7;      
input double SL_MULTIPLIER = 0.54;     
input int    MAGIC_NUMBER  = 144144;   

// --- SCALING PARAMETERS ---
float medians[33] = {0.00000000f, 27.00000000f, 87.84800000f, 0.00023141f, 0.00023753f, 0.00111235f, 0.50282486f, 50.13602989f, 49.94441432f, 49.98808796f, 0.00118962f, 0.00119550f, 0.00120811f, 0.00000008f, -0.00000390f, 0.00000120f, 0.00000691f, -0.00001362f, -0.00001406f, -0.00000063f, -0.00009099f, -39707.45091325f, -3792.52098882f, 11195.23451692f, -50.34965035f, -50.51903114f, -50.12285012f, -0.00002158f, 0.00000000f, -0.00002834f, 0.00332237f, 0.00459211f, 0.00563987f};
float iqrs[33]    = {0.00098212f, 0.14583333f, 47.63700000f, 0.00034076f, 0.00035548f, 0.00069236f, 0.56733877f, 20.22841795f, 13.83736542f, 11.20782633f, 0.00041950f, 0.00039227f, 0.00037959f, 0.00116635f, 0.00035128f, 0.00110528f, 0.00129523f, 0.00194593f, 0.00244929f, 0.00356923f, 0.00599302f, 92187.79394857f, 55475.79980033f, 44018.00685251f, 53.81116849f, 53.12096968f, 52.74723642f, 0.00303838f, 0.00435999f, 0.00543748f, 0.00247653f, 0.00321723f, 0.00389436f};

// --- GLOBAL HANDLES ---
int hRSI9, hRSI18, hRSI27, hATR9, hATR18, hATR27, hMACD, hEMA9, hEMA18, hEMA27, hEMA54, hEMA144, hCCI9, hCCI18, hCCI27, hWPR9, hWPR18, hWPR27, hBB9, hBB18, hBB27;
long onnx_handle = INVALID_HANDLE;
CTrade trade;

// --- ONNX DATA BUFFERS ---
float input_data[3960]; // 1 * 120 * 33 = 3960 (Bitcoin has 33 features, not 35)
float output_data[3];   // Softmax: [Neutral, Buy, Sell]

// --- TICK BAR STORAGE ---
struct Bar {
   double o, h, l, c, spread;
   long time_start;
};
Bar history[150]; // History buffer for returns and momentum
int ticks_in_bar = 0;
Bar current_bar;

//+------------------------------------------------------------------+
//| Initialization                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) {
      Print("❌ ONNX Handle Error: ", GetLastError());
      return(INIT_FAILED);
   }

   // --- SET FLAT SHAPES (1, 3960) ---
   const long in_shape[] = {1, 3960};
   const long out_shape[] = {1, 3};
   
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape) && GetLastError() != 5805) return(INIT_FAILED);
   if(!OnnxSetOutputShape(onnx_handle, 0, out_shape) && GetLastError() != 5805) return(INIT_FAILED);

   // --- INITIALIZE INDICATORS ---
   hRSI9 = iRSI(_Symbol, PERIOD_CURRENT, 9, PRICE_CLOSE);
   hRSI18 = iRSI(_Symbol, PERIOD_CURRENT, 18, PRICE_CLOSE);
   hRSI27 = iRSI(_Symbol, PERIOD_CURRENT, 27, PRICE_CLOSE);
   hATR9 = iATR(_Symbol, PERIOD_CURRENT, 9);
   hATR18 = iATR(_Symbol, PERIOD_CURRENT, 18);
   hATR27 = iATR(_Symbol, PERIOD_CURRENT, 27);
   hMACD = iMACD(_Symbol, PERIOD_CURRENT, 12, 26, 9, PRICE_CLOSE);
   hEMA9 = iMA(_Symbol, PERIOD_CURRENT, 9, 0, MODE_EMA, PRICE_CLOSE);
   hEMA18 = iMA(_Symbol, PERIOD_CURRENT, 18, 0, MODE_EMA, PRICE_CLOSE);
   hEMA27 = iMA(_Symbol, PERIOD_CURRENT, 27, 0, MODE_EMA, PRICE_CLOSE);
   hEMA54 = iMA(_Symbol, PERIOD_CURRENT, 54, 0, MODE_EMA, PRICE_CLOSE);
   hEMA144 = iMA(_Symbol, PERIOD_CURRENT, 144, 0, MODE_EMA, PRICE_CLOSE);
   hCCI9 = iCCI(_Symbol, PERIOD_CURRENT, 9, PRICE_TYPICAL);
   hCCI18 = iCCI(_Symbol, PERIOD_CURRENT, 18, PRICE_TYPICAL);
   hCCI27 = iCCI(_Symbol, PERIOD_CURRENT, 27, PRICE_TYPICAL);
   hWPR9 = iWPR(_Symbol, PERIOD_CURRENT, 9);
   hWPR18 = iWPR(_Symbol, PERIOD_CURRENT, 18);
   hWPR27 = iWPR(_Symbol, PERIOD_CURRENT, 27);
   hBB9 = iBands(_Symbol, PERIOD_CURRENT, 9, 0, 2.0, PRICE_CLOSE);
   hBB18 = iBands(_Symbol, PERIOD_CURRENT, 18, 0, 2.0, PRICE_CLOSE);
   hBB27 = iBands(_Symbol, PERIOD_CURRENT, 27, 0, 2.0, PRICE_CLOSE);

   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   Print("✅ Bitcoin Online. Flat-Tensor Model Loaded.");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Tick Processing                                                  |
//+------------------------------------------------------------------+
void OnTick() {
   MqlTick t; if(!SymbolInfoTick(_Symbol, t)) return;
   
   if(ticks_in_bar == 0) {
      current_bar.o = t.bid; current_bar.h = t.bid; current_bar.l = t.bid;
      current_bar.spread = 0; current_bar.time_start = t.time_msc;
   }
   
   current_bar.h = MathMax(current_bar.h, t.bid);
   current_bar.l = MathMin(current_bar.l, t.bid);
   current_bar.c = t.bid;
   current_bar.spread += (t.ask - t.bid);
   ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      current_bar.spread /= (double)TICK_DENSITY;
      
      // Shift and save history
      for(int i=149; i>0; i--) history[i] = history[i-1];
      history[0] = current_bar;
      
      ticks_in_bar = 0;
      static int bar_count = 0; bar_count++;
      if(bar_count >= 120) Predict();
   }
}

//+------------------------------------------------------------------+
//| Inference Logic                                                  |
//+------------------------------------------------------------------+
void Predict() {
   double r9[120], r18[120], r27[120], a9[120], a18[120], a27[120], mm[120], ms[120];
   double e9[120], e18[120], e27[120], e54[120], e144[120], c9[120], c18[120], c27[120];
   double w9[120], w18[120], w27[120], b9u[120], b9l[120], b18u[120], b18l[120], b27u[120], b27l[120];

   // Copy indicators (0=newest, 119=oldest)
   if(CopyBuffer(hRSI9,0,0,120,r9) < 120) return;
   CopyBuffer(hRSI18,0,0,120,r18); CopyBuffer(hRSI27,0,0,120,r27);
   CopyBuffer(hATR9,0,0,120,a9); CopyBuffer(hATR18,0,0,120,a18); CopyBuffer(hATR27,0,0,120,a27);
   CopyBuffer(hMACD,0,0,120,mm); CopyBuffer(hMACD,1,0,120,ms);
   CopyBuffer(hEMA9,0,0,120,e9); CopyBuffer(hEMA18,0,0,120,e18); CopyBuffer(hEMA27,0,0,120,e27);
   CopyBuffer(hEMA54,0,0,120,e54); CopyBuffer(hEMA144,0,0,120,e144);
   CopyBuffer(hCCI9,0,0,120,c9); CopyBuffer(hCCI18,0,0,120,c18); CopyBuffer(hCCI27,0,0,120,c27);
   CopyBuffer(hWPR9,0,0,120,w9); CopyBuffer(hWPR18,0,0,120,w18); CopyBuffer(hWPR27,0,0,120,w27);
   CopyBuffer(hBB9,1,0,120,b9u); CopyBuffer(hBB9,2,0,120,b9l);
   CopyBuffer(hBB18,1,0,120,b18u); CopyBuffer(hBB18,2,0,120,b18l);
   CopyBuffer(hBB27,1,0,120,b27u); CopyBuffer(hBB27,2,0,120,b27l);

   // Populate the flat 3960 array (33 features * 120 bars)
   for(int i=0; i<120; i++) {
      int h_idx = 119 - i; // Older bars first [119 ... 0]
      int buf_idx = 119 - i; // Index in copied indicator buffers corresponding to h_idx
      
      float f[33]; // Bitcoin has 33 features (no USDX/USDJPY)
      double close = history[h_idx].c;
      
      f[0] = (float)MathLog(close / (history[h_idx+1].c + 1e-8));
      f[1] = (float)history[h_idx].spread;
      f[2] = (float)((double)(history[h_idx].time_start - history[h_idx+1].time_start) / 1000.0);
      f[3] = (float)((history[h_idx].h - MathMax(history[h_idx].o, close)) / close);
      f[4] = (float)((MathMin(history[h_idx].o, close) - history[h_idx].l) / close);
      f[5] = (float)((history[h_idx].h - history[h_idx].l) / close);
      f[6] = (float)((close - history[h_idx].l) / (history[h_idx].h - history[h_idx].l + 1e-8));
      f[7] = (float)r9[buf_idx]; f[8] = (float)r18[buf_idx]; f[9] = (float)r27[buf_idx];
      f[10] = (float)(a9[buf_idx] / close); f[11] = (float)(a18[buf_idx] / close); f[12] = (float)(a27[buf_idx] / close);
      f[13] = (float)(mm[buf_idx] / close); f[14] = (float)(ms[buf_idx] / close); f[15] = (float)((mm[buf_idx] - ms[buf_idx]) / close);
      f[16] = (float)((e9[buf_idx] - close) / close); f[17] = (float)((e18[buf_idx] - close) / close); f[18] = (float)((e27[buf_idx] - close) / close);
      f[19] = (float)((e54[buf_idx] - close) / close); f[20] = (float)((e144[buf_idx] - close) / close);
      f[21] = (float)c9[buf_idx]; f[22] = (float)c18[buf_idx]; f[23] = (float)c27[buf_idx];
      f[24] = (float)w9[buf_idx]; f[25] = (float)w18[buf_idx]; f[26] = (float)w27[buf_idx];
      f[27] = (float)((close - history[h_idx+9].c) / close);
      f[28] = (float)((close - history[h_idx+18].c) / close);
      f[29] = (float)((close - history[h_idx+27].c) / close);
      // f[30] and f[31] removed (no USDX/USDJPY for Bitcoin)
      f[30] = (float)((b9u[buf_idx] - b9l[buf_idx]) / close);
      f[31] = (float)((b18u[buf_idx] - b18l[buf_idx]) / close);
      f[32] = (float)((b27u[buf_idx] - b27l[buf_idx]) / close);

      for(int k=0; k<33; k++) {
         input_data[i * 33 + k] = (f[k] - medians[k]) / (iqrs[k] + 1e-8f);
      }
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) {
      Print("❌ Inference Error: ", GetLastError());
      return;
   }
   
   int signal = ArrayMaximum(output_data);
   float prob = output_data[signal];

   if(signal == 1 && prob > 0.55 && !HasOpenPosition()) ExecuteTrade(ORDER_TYPE_BUY);
   if(signal == 2 && prob > 0.55 && !HasOpenPosition()) ExecuteTrade(ORDER_TYPE_SELL);
}

//+------------------------------------------------------------------+
//| Order Execution                                                  |
//+------------------------------------------------------------------+
void ExecuteTrade(ENUM_ORDER_TYPE type) {
   double atr_buf[1]; 
   if(CopyBuffer(hATR18, 0, 0, 1, atr_buf) < 1) return;
   
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl_dist = SL_MULTIPLIER * atr_buf[0];
   double tp_dist = TP_MULTIPLIER * atr_buf[0];
   
   double sl = (type == ORDER_TYPE_BUY) ? (price - sl_dist) : (price + sl_dist);
   double tp = (type == ORDER_TYPE_BUY) ? (price + tp_dist) : (price - tp_dist);
   
   trade.PositionOpen(_Symbol, type, 0.1, price, sl, tp);
}

bool HasOpenPosition() {
   for(int i=PositionsTotal()-1; i>=0; i--)
      if(PositionGetSymbol(i) == _Symbol && PositionGetInteger(POSITION_MAGIC) == MAGIC_NUMBER) return true;
   return false;
}

void OnDeinit(const int reason) {
   if(onnx_handle != INVALID_HANDLE) OnnxRelease(onnx_handle);
   IndicatorRelease(hRSI9); IndicatorRelease(hRSI18); IndicatorRelease(hRSI27);
   IndicatorRelease(hATR9); IndicatorRelease(hATR18); IndicatorRelease(hATR27);
   IndicatorRelease(hMACD); IndicatorRelease(hEMA9); IndicatorRelease(hEMA18);
   IndicatorRelease(hEMA27); IndicatorRelease(hEMA54); IndicatorRelease(hEMA144);
   IndicatorRelease(hCCI9); IndicatorRelease(hCCI18); IndicatorRelease(hCCI27);
   IndicatorRelease(hWPR9); IndicatorRelease(hWPR18); IndicatorRelease(hWPR27);
   IndicatorRelease(hBB9); IndicatorRelease(hBB18); IndicatorRelease(hBB27);
}
