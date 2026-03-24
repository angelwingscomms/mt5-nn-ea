//+------------------------------------------------------------------+
//|                                  Live_Achilles_TickBar.mq5       |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

input int    TICK_DENSITY  = 144;      // Variable Bar Density
input double TP_POINTS     = 1.44;     // Take Profit
input double SL_POINTS     = 0.0;      // Stop Loss (0 = No SL)
input string USDX_Symbol   = "$USDX";  // USD Index Symbol Name
input string USDJPY_Symbol = "USDJPY"; // USDJPY Symbol Name

float means[31] = {0.0f}; // PASTE FROM PYTHON
float stds[31]  = {1.0f}; // PASTE FROM PYTHON

CTrade trade;
long onnx = INVALID_HANDLE;
float input_data[3720];
double o_a[150], h_a[150], l_a[150], c_a[150], v_a[150], s_a[150], dx_a[150], jp_a[150];
int ticks_in_bar = 0, bars = 0;
double b_open, b_high, b_low, b_vol, b_spread;

int OnInit() {
   if(!SymbolSelect(USDX_Symbol, true) || !SymbolSelect(USDJPY_Symbol, true)) return(INIT_FAILED);
   string model_path = "achilles_" + IntegerToString(TICK_DENSITY) + ".onnx";
   onnx = OnnxCreateFromFile(model_path, ONNX_DEFAULT);
   if(onnx == INVALID_HANDLE) { Print("❌ Load Error: ", model_path); return(INIT_FAILED); }
   long in[]={1,120,31}; OnnxSetInputShape(onnx,0,in);
   long out[]={1,3}; OnnxSetOutputShape(onnx,0,out);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { if(onnx != INVALID_HANDLE) OnnxRelease(onnx); }

void OnTick() {
   MqlTick t; if(!SymbolInfoTick(_Symbol, t)) return;
   if(ticks_in_bar == 0) { b_open=t.last; b_high=t.last; b_low=t.last; b_vol=0; b_spread=0; }
   b_high=MathMax(b_high, t.last); b_low=MathMin(b_low, t.last);
   b_vol += t.volume; b_spread += (t.ask-t.bid); ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      Shift(b_open, b_high, b_low, t.last, b_vol, b_spread/(double)TICK_DENSITY);
      ticks_in_bar = 0;
      if(bars >= 120) Predict();
   }
}

void Shift(double o, double h, double l, double c, double v, double s) {
   for(int i=149; i>0; i--) { 
      o_a[i]=o_a[i-1]; h_a[i]=h_a[i-1]; l_a[i]=l_a[i-1]; c_a[i]=c_a[i-1]; 
      v_a[i]=v_a[i-1]; s_a[i]=s_a[i-1]; dx_a[i]=dx_a[i-1]; jp_a[i]=jp_a[i-1]; 
   }
   o_a[0]=o; h_a[0]=h; l_a[0]=l; c_a[0]=c; v_a[0]=v; s_a[0]=s;
   dx_a[0]=SymbolInfoDouble(USDX_Symbol, SYMBOL_BID); 
   jp_a[0]=SymbolInfoDouble(USDJPY_Symbol, SYMBOL_BID);
   bars++;
}

void Predict() {
   for(int i=0; i<120; i++) {
      int x = 119-i; float f[31];
      f[0]=(float)((c_a[x]-o_a[x])/(o_a[x]+1e-8)); f[1]=(float)s_a[x]; f[2]=(float)((v_a[x]-v_a[x+1])/(v_a[x+1]+1e-8));
      double spv=0, sv=0; for(int j=0; j<100; j++) { spv+=((h_a[x+j]+l_a[x+j]+c_a[x+j])/3)*v_a[x+j]; sv+=v_a[x+j]; }
      double vwap=spv/(sv+1e-8); f[3]=(float)((c_a[x]-vwap)/(vwap+1e-8));
      f[4]=(float)(CalcEMA(x,9)-c_a[x]); f[5]=(float)(CalcEMA(x,18)-c_a[x]); f[6]=(float)(CalcEMA(x,27)-c_a[x]);
      f[7]=CalcRSI(x,9); f[8]=CalcRSI(x,18); f[9]=CalcRSI(x,27);
      f[10]=(float)(CalcEMA(x,9)-CalcEMA(x,18)); f[11]=f[10]; f[12]=0;
      f[13]=(float)((dx_a[x]-dx_a[x+1])/(dx_a[x+1]+1e-8)); f[14]=(float)((jp_a[x]-jp_a[x+1])/(jp_a[x+1]+1e-8));
      f[15]=CalcATR(x,9); f[16]=CalcATR(x,18); f[17]=CalcATR(x,27);
      f[18]=CalcBBW(x,9); f[19]=CalcBBW(x,18); f[20]=CalcBBW(x,27);
      f[21]=0; f[22]=0; f[23]=0; f[24]=CalcWPR(x,9); f[25]=CalcWPR(x,18); f[26]=CalcWPR(x,27);
      f[27]=(float)(c_a[x]-c_a[x+9]); f[28]=(float)(c_a[x]-c_a[x+18]); f[29]=(float)(c_a[x]-c_a[x+27]);
      f[30]=(float)(MathAbs(c_a[x]-o_a[x])/(h_a[x]-l_a[x]+1e-8));
      for(int k=0; k<31; k++) input_data[i*31+k]=(f[k]-means[k]) / (stds[k]+1e-8f);
   }
   float out[3]; OnnxRun(onnx, ONNX_DEFAULT, input_data, out);
   if(out[0]>0.5) return;
   double a=SymbolInfoDouble(_Symbol,SYMBOL_ASK), b=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(out[1]>0.55 && PositionsTotal()==0) Execute(ORDER_TYPE_BUY, a);
   if(out[2]>0.55 && PositionsTotal()==0) Execute(ORDER_TYPE_SELL, b);
}

void Execute(ENUM_ORDER_TYPE type, double p) {
   double sl = (SL_POINTS <= 0) ? 0 : (type==ORDER_TYPE_BUY ? p-SL_POINTS : p+SL_POINTS);
   double tp = (type==ORDER_TYPE_BUY ? p+TP_POINTS : p-TP_POINTS);
   if(type==ORDER_TYPE_BUY) trade.Buy(0.01,_Symbol,p,sl,tp); else trade.Sell(0.01,_Symbol,p,sl,tp);
}

float CalcEMA(int idx, int p) { double m=2.0/(p+1); double ema=c_a[idx+p]; for(int i=idx+p-1; i>=idx; i--) ema=(c_a[i]-ema)*m+ema; return (float)ema; }
float CalcRSI(int idx, int p) { double u=0, d=0; for(int i=0; i<p; i++) { double diff=c_a[idx+i]-c_a[idx+i+1]; if(diff>0) u+=diff; else d-=diff; } return (d==0)?100:(float)(100-(100/(1+u/d))); }
float CalcATR(int idx, int p) { double s=0; for(int i=0; i<p; i++) s+=MathMax(h_a[idx+i]-l_a[idx+i], MathAbs(h_a[idx+i]-c_a[idx+i+1])); return (float)(s/p); }
float CalcWPR(int idx, int p) { double h=h_a[idx], l=l_a[idx]; for(int i=1; i<p; i++) { h=MathMax(h,h_a[idx+i]); l=MathMin(l,l_a[idx+i]); } return (h==l)?0:(float)(-100*(h-c_a[idx])/(h-l)); }
float CalcBBW(int idx, int p) { double s=0, sq=0; for(int i=0; i<p; i++) s+=c_a[idx+i]; double m=s/p; for(int i=0; i<p; i++) sq+=MathPow(c_a[idx+i]-m,2); return (float)((MathSqrt(sq/p)*4)/m); }