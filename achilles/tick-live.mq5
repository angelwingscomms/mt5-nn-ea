#include <Trade\Trade.mqh>
#resource "\\Files\\achilles.onnx" as uchar model_buffer[]

input int TICK_DENSITY=144; input double ATR_TP=2.0, ATR_SL=1.1;
input string USDX_Symbol="$USDX", USDJPY_Symbol="USDJPY";

CTrade trade; long onnx=INVALID_HANDLE;
double o_a[400], h_a[400], l_a[400], c_a[400], s_a[400], d_a[400], dx_a[400], jp_a[400];
ulong tm_a[400]; int bars_total=0, ticks_in_bar=0;
double b_open, b_high, b_low, b_spread_sum; ulong b_start;

int OnInit() {
   onnx=OnnxCreateFromBuffer(model_buffer,ONNX_DEFAULT);
   long in[]={1,144,40}, out[]={1,3};
   OnnxSetInputShape(onnx,0,in); OnnxSetOutputShape(onnx,0,out);
   return(INIT_SUCCEEDED);
}

void OnTick() {
   MqlTick t; if(!SymbolInfoTick(_Symbol,t)) return;
   if(ticks_in_bar==0){ b_open=t.bid; b_high=t.bid; b_low=t.bid; b_spread_sum=0; b_start=t.time_msc; }
   b_high=MathMax(b_high,t.bid); b_low=MathMin(b_low,t.bid); b_spread_sum+=(t.ask-t.bid); ticks_in_bar++;
   if(ticks_in_bar>=TICK_DENSITY){
      Shift(b_open, b_high, b_low, t.bid, b_spread_sum/TICK_DENSITY, (double)(t.time_msc-b_start), b_start);
      ticks_in_bar=0; if(bars_total>=300) Predict();
   }
}

void Shift(double o,double h,double l,double c,double s,double d,ulong t){
   for(int i=399;i>0;i--){ o_a[i]=o_a[i-1]; h_a[i]=h_a[i-1]; l_a[i]=l_a[i-1]; c_a[i]=c_a[i-1]; s_a[i]=s_a[i-1]; d_a[i]=d_a[i-1]; dx_a[i]=dx_a[i-1]; jp_a[i]=jp_a[i-1]; tm_a[i]=tm_a[i-1]; }
   o_a[0]=o; h_a[0]=h; l_a[0]=l; c_a[0]=c; s_a[0]=s; d_a[0]=d; tm_a[0]=t; dx_a[0]=SymbolInfoDouble(USDX_Symbol,SYMBOL_BID); jp_a[0]=SymbolInfoDouble(USDJPY_Symbol,SYMBOL_BID); bars_total++;
}

void Predict(){
   float in[5760];
   for(int f=0;f<35;f++){
      double sum=0, sq=0; for(int b=0;b<250;b++){ double v=GetRaw(f,b); sum+=v; sq+=(v*v); }
      double m=sum/250.0, st=MathSqrt(MathMax(0,(sq/250.0)-(m*m)))+1e-8;
      for(int i=0;i<144;i++) in[i*40+f]=(float)((GetRaw(f,143-i)-m)/st);
   }
   for(int i=0;i<144;i++){
      MqlDateTime dt; TimeToStruct((datetime)(tm_a[143-i]/1000),dt); double p=3.14159265;
      in[i*40+35]=(float)MathSin(2*p*dt.hour/24.0); in[i*40+36]=(float)MathCos(2*p*dt.hour/24.0);
      in[i*40+37]=(float)MathSin(2*p*dt.min/60.0); in[i*40+38]=(float)MathCos(2*p*dt.min/60.0); in[i*40+39]=(float)(dt.day_of_week/6.0);
   }
   float out[3]; OnnxRun(onnx,ONNX_DEFAULT,in,out);
   if(PositionsTotal()==0 && (SymbolInfoDouble(_Symbol,SYMBOL_ASK)-SymbolInfoDouble(_Symbol,SYMBOL_BID)) < CATR(0,14)*0.3){
      if(out[1]>0.85) Execute(ORDER_TYPE_BUY); if(out[2]>0.85) Execute(ORDER_TYPE_SELL);
   }
}

double GetRaw(int f,int s){
   switch(f){
      case 0: return MathLog(c_a[s]/(c_a[s+1]+1e-8)); case 1: return s_a[s]; case 2: return d_a[s];
      case 3: return (h_a[s]-MathMax(o_a[s],c_a[s]))/(c_a[s]+1e-8); case 4: return (MathMin(o_a[s],c_a[s])-l_a[s])/(c_a[s]+1e-8);
      case 5: return (h_a[s]-l_a[s])/(c_a[s]+1e-8); case 6: return (c_a[s]-l_a[s])/(h_a[s]-l_a[s]+1e-8);
      case 7: return CRSI(s,9); case 8: return CRSI(s,18); case 9: return CRSI(s,27);
      case 10: return CATR(s,9); case 11: return CATR(s,18); case 12: return CATR(s,27);
      case 13: return (CEMA(s,12)-CEMA(s,26)); case 14: return CM_S(s); case 15: return (CEMA(s,12)-CEMA(s,26)-CM_S(s));
      case 16: return CEMA(s,9)-c_a[s]; case 17: return CEMA(s,18)-c_a[s]; case 18: return CEMA(s,27)-c_a[s]; case 19: return CEMA(s,54)-c_a[s]; case 20: return CEMA(s,144)-c_a[s];
      case 21: return CCCI(s,9); case 22: return CCCI(s,18); case 23: return CCCI(s,27);
      case 24: return CWPR(s,9); case 25: return CWPR(s,18); case 26: return CWPR(s,27);
      case 27: return c_a[s]-c_a[s+9]; case 28: return c_a[s]-c_a[s+18]; case 29: return c_a[s]-c_a[s+27];
      case 30: return (dx_a[s]-dx_a[s+1])/(dx_a[s+1]+1e-8); case 31: return (jp_a[s]-jp_a[s+1])/(jp_a[s+1]+1e-8);
      case 32: return CBBW(s,9); case 33: return CBBW(s,18); case 34: return CBBW(s,27); default: return 0;
   }
}

float CEMA(int x,int p){ double m=2.0/(p+1), e=c_a[x+p]; for(int i=x+p-1;i>=x;i--) e=(c_a[i]-e)*m+e; return (float)e; }
float CM_S(int x){ double m=2.0/10, s=0; for(int i=0;i<9;i++) s+=(CEMA(x+20+i,12)-CEMA(x+20+i,26)); s/=9; for(int i=19;i>=0;i--) s=((CEMA(x+i,12)-CEMA(x+i,26))-s)*m+s; return (float)s; }
float CATR(int x,int p){ double s=0; for(int i=0;i<p;i++){ double d1=h_a[x+i]-l_a[x+i],d2=MathAbs(h_a[x+i]-c_a[x+i+1]),d3=MathAbs(l_a[x+i]-c_a[x+i+1]); s+=MathMax(d1,MathMax(d2,d3)); } return (float)(s/p); }
float CCCI(int x,int p){ double tp=(h_a[x]+l_a[x]+c_a[x])/3, sm=0, md=0; for(int i=0;i<p;i++) sm+=(h_a[x+i]+l_a[x+i]+c_a[x+i])/3; sm/=p; for(int i=0;i<p;i++) md+=MathAbs(((h_a[x+i]+l_a[x+i]+c_a[x+i])/3)-sm); md/=p; return (float)((tp-sm)/(0.015*md+1e-8)); }
float CRSI(int x,int p){ double u=0, d=0; for(int i=0; i<p; i++){ double df=c_a[x+i]-c_a[x+i+1]; if(df>0) u+=df; else d-=df; } return (d==0)?100:(float)(100-(100/(1+u/(d+1e-8)))); }
float CWPR(int x,int p){ double h=h_a[x], l=l_a[x]; for(int i=1; i<p; i++){ h=MathMax(h,h_a[x+i]); l=MathMin(l,l_a[x+i]); } return (h==l)?0:(float)(-100*(h-c_a[x])/(h-l+1e-8)); }
float CBBW(int x,int p){ double s=0, sq=0; for(int i=0; i<p; i++) s+=c_a[i+x]; double m=s/p; for(int i=0; i<p; i++) sq+=MathPow(c_a[i+x]-m,2); return (float)((MathSqrt(sq/p)*4)/(m+1e-8)); }

void Execute(ENUM_ORDER_TYPE t){
   double p=(t==ORDER_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_ASK):SymbolInfoDouble(_Symbol,SYMBOL_BID);
   double v=CATR(0,14), sl=(t==ORDER_TYPE_BUY)?p-(v*ATR_SL):p+(v*ATR_SL), tp=(t==ORDER_TYPE_BUY)?p+(v*ATR_TP):p-(v*ATR_TP);
   double margin = SymbolInfoDouble(_Symbol, SYMBOL_MARGIN_INITIAL);
   if(margin <= 0) margin = 100.0;
   double lot = AccountInfoDouble(ACCOUNT_FREEMARGIN) / margin;
   lot = MathFloor(lot / SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP)) * SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double max_v = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), min_v = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   if(lot > max_v) lot = max_v; if(lot < min_v) return;
   trade.PositionOpen(_Symbol,t,lot,p,sl,tp);
}