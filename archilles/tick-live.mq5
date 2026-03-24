//+------------------------------------------------------------------+
//|                                  Live_Achilles_TickBar.mq5       |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

#resource "\\Files\\achilles_144.onnx" as uchar model_buffer[]

input int    TICK_DENSITY  = 144;      // Variable Bar Density
input double TP_POINTS     = 1.44;     // Target Profit
input double SL_POINTS     = 1.44;      // 0 = ABSOLUTELY NO STOP LOSS
input string USDX_Symbol   = "$USDX";  // USD Index Symbol
input string USDJPY_Symbol = "USDJPY"; // Yield Proxy Symbol

float means[35]={-0.000003f,0.286519f,48873.666667f,0.000149f,0.000146f,0.000303f,0.493767f,49.869564f,49.687725f,49.565113f,1.519998f,1.526129f,1.530636f,-0.073630f,-0.078442f,0.004813f,0.055322f,0.128952f,0.209752f,0.455186f,1.100607f,-490657.532075f,-318802.143319f,-243815.193814f,-50.171725f,-49.145609f,-48.455307f,-0.119320f,-0.286310f,-0.443835f,0.000000f,0.000000f,0.001019f,0.001431f,0.001770f};
float stds[35]={0.000231f,0.062826f,125080.947769f,0.000151f,0.000146f,0.000167f,0.338452f,14.423269f,9.750540f,7.442737f,0.428174f,0.378513f,0.353843f,1.019579f,0.934306f,0.366638f,1.524156f,2.320060f,2.885289f,3.930968f,5.355729f,301580.169264f,189018.026698f,133811.444149f,31.042835f,30.984008f,31.482194f,3.401854f,4.997250f,6.198753f,0.000000f,0.000000f,0.000572f,0.000788f,0.000963f};

CTrade trade;
long onnx = INVALID_HANDLE;
float input_data[4200]; 
// Arrays increased to 300 to prevent 'Array Out of Range' for 144-period indicators
double o_a[300], h_a[300], l_a[300], c_a[300], s_a[300], d_a[300], dx_a[300], jp_a[300];
int ticks_in_bar = 0, bars = 0;
double b_open, b_high, b_low, b_spread;
ulong b_start_time;

int OnInit() {
   if(!SymbolSelect(USDX_Symbol, true) || !SymbolSelect(USDJPY_Symbol, true)) return(INIT_FAILED);
   onnx = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
   if(onnx == INVALID_HANDLE) return(INIT_FAILED);
   long in[]={1,120,35}; OnnxSetInputShape(onnx,0,in);
   long out[]={1,3}; OnnxSetOutputShape(onnx,0,out);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) { if(onnx != INVALID_HANDLE) OnnxRelease(onnx); }

void OnTick() {
   MqlTick t; if(!SymbolInfoTick(_Symbol, t)) return;
   if(ticks_in_bar == 0) { b_open=t.bid; b_high=t.bid; b_low=t.bid; b_spread=0; b_start_time=t.time_msc; }
   b_high=MathMax(b_high, t.bid); b_low=MathMin(b_low, t.bid);
   b_spread += (t.ask-t.bid); ticks_in_bar++;

   if(ticks_in_bar >= TICK_DENSITY) {
      Shift(b_open, b_high, b_low, t.bid, b_spread/(double)TICK_DENSITY, (double)(t.time_msc - b_start_time));
      ticks_in_bar = 0;
      // Inference requires 120 bars + 144 bar indicator depth = 264 minimum
      if(bars >= 270) Predict(); 
   }
}

void Shift(double o, double h, double l, double c, double s, double d) {
   for(int i=299; i>0; i--) { 
      o_a[i]=o_a[i-1]; h_a[i]=h_a[i-1]; l_a[i]=l_a[i-1]; c_a[i]=c_a[i-1]; 
      s_a[i]=s_a[i-1]; d_a[i]=d_a[i-1]; dx_a[i]=dx_a[i-1]; jp_a[i]=jp_a[i-1]; 
   }
   o_a[0]=o; h_a[0]=h; l_a[0]=l; c_a[0]=c; s_a[0]=s; d_a[0]=d;
   dx_a[0]=SymbolInfoDouble(USDX_Symbol, SYMBOL_BID);
   jp_a[0]=SymbolInfoDouble(USDJPY_Symbol, SYMBOL_BID);
   bars++;
}

void Predict() {
   for(int i=0; i<120; i++) {
      int x = 119-i; float f[35];
      f[0]=(float)MathLog(c_a[x]/(c_a[x+1]+1e-8)); 
      f[1]=(float)s_a[x]; 
      f[2]=(float)d_a[x];
      f[3]=(float)((h_a[x]-MathMax(o_a[x],c_a[x]))/(c_a[x]+1e-8)); 
      f[4]=(float)((MathMin(o_a[x],c_a[x])-l_a[x])/(c_a[x]+1e-8));
      f[5]=(float)((h_a[x]-l_a[x])/(c_a[x]+1e-8)); 
      f[6]=(float)((c_a[x]-l_a[x])/(h_a[x]-l_a[x]+1e-8));
      f[7]=CRSI(x,9); f[8]=CRSI(x,18); f[9]=CRSI(x,27);
      f[10]=CATR(x,9); f[11]=CATR(x,18); f[12]=CATR(x,27);
      double e9=CEMA(x,9), e18=CEMA(x,18), e27=CEMA(x,27), e54=CEMA(x,54), e144=CEMA(x,144);
      f[13]=(float)(e9-e18); f[14]=f[13]; f[15]=0;
      f[16]=(float)(e9-c_a[x]); f[17]=(float)(e18-c_a[x]); f[18]=(float)(e27-c_a[x]); 
      f[19]=(float)(e54-c_a[x]); f[20]=(float)(e144-c_a[x]);
      f[21]=0; f[22]=0; f[23]=0;
      f[24]=CWPR(x,9); f[25]=CWPR(x,18); f[26]=CWPR(x,27);
      f[27]=(float)(c_a[x]-c_a[x+9]); f[28]=(float)(c_a[x]-c_a[x+18]); f[29]=(float)(c_a[x]-c_a[x+27]);
      f[30]=(float)((dx_a[x]-dx_a[x+1])/(dx_a[x+1]+1e-8)); f[31]=(float)((jp_a[x]-jp_a[x+1])/(jp_a[x+1]+1e-8));
      f[32]=CBBW(x,9); f[33]=CBBW(x,18); f[34]=CBBW(x,27);
      for(int k=0; k<35; k++) input_data[i*35+k]=(f[k]-means[k])/(stds[k]+1e-8f);
   }
   float out[3]; OnnxRun(onnx, ONNX_DEFAULT, input_data, out);
   if(out[0]>0.5) return;
   double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(out[1]>0.55 && PositionsTotal()==0) Execute(ORDER_TYPE_BUY, ask);
   if(out[2]>0.55 && PositionsTotal()==0) Execute(ORDER_TYPE_SELL, bid);
}

void Execute(ENUM_ORDER_TYPE type, double p) {
   double sl = (SL_POINTS <= 0) ? 0 : (type==ORDER_TYPE_BUY ? p-SL_POINTS : p+SL_POINTS);
   double tp = (type==ORDER_TYPE_BUY ? p+TP_POINTS : p-TP_POINTS);
   if(type==ORDER_TYPE_BUY) trade.Buy(0.01,_Symbol,p,sl,tp); else trade.Sell(0.01,_Symbol,p,sl,tp);
}

float CRSI(int x, int p) { double u=0, d=0; for(int i=0; i<p; i++) { double df=c_a[x+i]-c_a[x+i+1]; if(df>0) u+=df; else d-=df; } return (d==0)?100:(float)(100-(100/(1+u/(d+1e-8)))); }
float CATR(int x, int p) { double s=0; for(int i=0; i<p; i++) s+=MathMax(h_a[x+i]-l_a[x+i], MathAbs(h_a[x+i]-c_a[x+i+1])); return (float)(s/p); }
float CEMA(int x, int p) { double m=2.0/(p+1); double e=c_a[x+p]; for(int i=x+p-1; i>=x; i--) e=(c_a[i]-e)*m+e; return (float)e; }
float CWPR(int x, int p) { double h=h_a[x], l=l_a[x]; for(int i=1; i<p; i++) { h=MathMax(h,h_a[x+i]); l=MathMin(l,l_a[x+i]); } return (h==l)?0:(float)(-100*(h-c_a[x])/(h-l+1e-8)); }
float CBBW(int x, int p) { double s=0, sq=0; for(int i=0; i<p; i++) s+=c_a[i+x]; double m=s/p; for(int i=0; i<p; i++) sq+=MathPow(c_a[i+x]-m,2); return (float)((MathSqrt(sq/p)*4)/(m+1e-8)); }