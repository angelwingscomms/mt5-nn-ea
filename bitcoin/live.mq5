#include <Trade\Trade.mqh>

#resource "\\Experts\\nn\\bitcoin\\bitcoin_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      
input double TP_MULTIPLIER = 2.7;      
input double SL_MULTIPLIER = 0.54;     
input int    MAGIC_NUMBER  = 144144;   

// --- PASTE SCALERS FROM PYTHON HERE ---
float medians[17] = {0.00000000f, 27.00000000f, 70.80700000f, 0.00012343f, 0.00012294f, 0.00068803f, 0.49367089f, 0.00000090f, 0.00000226f, -0.00000554f, 0.00071186f, 0.00000000f, -0.00000000f, 0.00000000f, -0.22252093f, 4.97673374f, 0.00029869f};
float iqrs[17]    = {0.00066690f, 0.03298611f, 30.69700000f, 0.00020701f, 0.00021453f, 0.00048550f, 0.62023607f, 0.00076084f, 0.00072568f, 0.00021931f, 0.00032776f, 1.41421356f, 1.41421356f, 1.56366296f, 1.52445867f, 1.00000000f, 0.00450263f};

long onnx_handle = INVALID_HANDLE;
CTrade trade;
float input_data[2040]; 
float output_data[3];   
datetime last_loss_time = 0;

// High-Density Orthogonal Feature Struct
struct Bar { 
   double o, h, l, c, v, spread, tvwp; 
   ulong time_msc; // Preserved exactly from tick for UTC math
   double atr18; 
   double macd_ema12, macd_ema26, macd_sig;
};
Bar history[200]; 
int ticks_in_bar = 0;
Bar cur_b;
bool warmed_up = false;

int OnInit() {
   if(ArraySize(model_buffer) == 0) return(INIT_FAILED);
   onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx_handle == INVALID_HANDLE) return(INIT_FAILED);

   const long in_shape[] = {1, 2040};
   const long out_shape[] = {1, 3};
   if(!OnnxSetInputShape(onnx_handle, 0, in_shape)) return(INIT_FAILED);
   if(!OnnxSetOutputShape(onnx_handle, 0, out_shape)) return(INIT_FAILED);
   
   trade.SetExpertMagicNumber(MAGIC_NUMBER);
   
   Print("[INFO] Pre-warming Internal Indicator States...");
   MqlTick pre_ticks[];
   int copied = CopyTicks(_Symbol, pre_ticks, COPY_TICKS_ALL, 0, 50000);
   for(int i = 0; i < copied; i++) ProcessTick(pre_ticks[i]);
   warmed_up = true;
   
   Print("✅ Neural Architecture Locked. State Warmed (17 Features).");
   return(INIT_SUCCEEDED);
}

void OnTick() {
   MqlTick t; if(SymbolInfoTick(_Symbol, t)) ProcessTick(t);
}

void ProcessTick(MqlTick &t) {
   if(ticks_in_bar == 0) {
      cur_b.o = t.bid; cur_b.h = t.bid; cur_b.l = t.bid; cur_b.c = t.bid; 
      cur_b.v = 0; cur_b.spread = 0; cur_b.time_msc = t.time_msc;
   }
   cur_b.h = MathMax(cur_b.h, t.bid); 
   cur_b.l = MathMin(cur_b.l, t.bid); 
   cur_b.c = t.bid;
   double tv = (t.volume > 0) ? (double)t.volume : 1.0;
   cur_b.v += tv; 
   cur_b.spread += (t.ask - t.bid);
   ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      cur_b.spread /= TICK_DENSITY;
      ComputeIndicators(cur_b);
      
      for(int i=199; i>0; i--) history[i] = history[i-1];
      history[0] = cur_b;
      ticks_in_bar = 0;
      
      if(warmed_up) Predict();
   }
}

// Minimal, exact mathematical parity
void ComputeIndicators(Bar &b) {
   Bar p = history[0]; 
   if(p.c == 0.0) p = b; 
   
   // RMA Smoothing (Wilder's ATR 18)
   double tr = MathMax(b.h - b.l, MathMax(MathAbs(b.h - p.c), MathAbs(b.l - p.c)));
   b.atr18 = (tr - p.atr18)/18.0 + p.atr18;

   // MACD 12, 26, 9
   b.macd_ema12 = (b.c - p.macd_ema12)*(2.0/13.0) + p.macd_ema12;
   b.macd_ema26 = (b.c - p.macd_ema26)*(2.0/27.0) + p.macd_ema26;
   double macd_raw = b.macd_ema12 - b.macd_ema26;
   b.macd_sig = (macd_raw - p.macd_sig)*(2.0/10.0) + p.macd_sig;
   
   // TVWP
   double sum_pv = 0, sum_v = 0;
   for(int j=0; j<143 && j<200; j++) { sum_pv += (history[j].c * history[j].v); sum_v += history[j].v; }
   sum_pv += (b.c * b.v); sum_v += b.v;
   b.tvwp = sum_pv / (sum_v + 1e-8);
}

void Predict() {
   if(history[144].c == 0.0) return; 
   if(TimeCurrent() < last_loss_time + 3600) return; 

   for(int i=0; i<120; i++) {
      int h = 119 - i; 
      float f[17];
      double cl = history[h].c;
      
      // ABSOLUTE UTC TIME PARITY (Bypasses MQL5 Broker Timezone Offset)
      double utc_hour = (double)((history[h].time_msc / 3600000) % 24);
      double utc_dow  = (double)(((history[h].time_msc / 86400000) + 4) % 7); // Jan 1 1970 was Thursday (4)

      f[0]=(float)MathLog(cl/(history[h+1].c+1e-8)); 
      f[1]=(float)history[h].spread; 
      f[2]=(float)((history[h].time_msc - history[h+1].time_msc) / 1000.0); 
      f[3]=(float)((history[h].h-MathMax(history[h].o,cl))/cl); 
      f[4]=(float)((MathMin(history[h].o,cl)-history[h].l)/cl);
      f[5]=(float)((history[h].h-history[h].l)/cl); 
      f[6]=(float)((cl-history[h].l)/(history[h].h-history[h].l+1e-8));
      
      double mm = history[h].macd_ema12 - history[h].macd_ema26;
      f[7]=(float)(mm/cl); 
      f[8]=(float)(history[h].macd_sig/cl); 
      f[9]=(float)((mm-history[h].macd_sig)/cl);
      
      f[10]=(float)(history[h].atr18/cl);
      
      f[11]=(float)MathSin(2.0*M_PI*utc_hour/24.0); 
      f[12]=(float)MathCos(2.0*M_PI*utc_hour/24.0);
      f[13]=(float)MathSin(2.0*M_PI*utc_dow/7.0); 
      f[14]=(float)MathCos(2.0*M_PI*utc_dow/7.0);
      
      f[15]=(float)MathLog(history[h].v + 1.0); 
      f[16]=(float)((cl - history[h].tvwp)/cl);

      for(int k=0; k<17; k++) input_data[i*17+k] = (f[k]-medians[k])/(iqrs[k]);
   }

   if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output_data)) return;
   
   int sig = ArrayMaximum(output_data);
   if((sig == 1 || sig == 2) && output_data[sig] > 0.65 && !HasPos()) {
      Exec(sig == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   }
}

void Exec(ENUM_ORDER_TYPE type) {
   double atr = history[0].atr18;
   double p = (type==ORDER_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_ASK):SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double sl = (type==ORDER_TYPE_BUY)?(p-atr*SL_MULTIPLIER):(p+atr*SL_MULTIPLIER);
   double tp = (type==ORDER_TYPE_BUY)?(p+atr*TP_MULTIPLIER):(p-atr*TP_MULTIPLIER);
   trade.PositionOpen(_Symbol,type,0.1,p,sl,tp);
}

bool HasPos() {
   for(int i=PositionsTotal()-1; i>=0; i--)
      if(PositionGetSymbol(i)==_Symbol && PositionGetInteger(POSITION_MAGIC)==MAGIC_NUMBER) return true;
   return false;
}

void OnDeinit(const int reason) { if(onnx_handle != INVALID_HANDLE) OnnxRelease(onnx_handle); }