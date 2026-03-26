//+------------------------------------------------------------------+
//|                                       Live_Trader_Achilles.mq5   |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

#resource "\\Files\\model_achilles.onnx" as uchar model_buffer[]

// --- REPLACE THESE WITH YOUR EXACT SCALER VALUES FROM PYTHON OUTPUT ---
float means[35] = {0.000000f, 51.189174f, 51.075032f, 51.004080f, 3.517946f, 3.517941f, 3.517926f, 42.348980f, 30.035590f, 24.474167f, 0.067751f, 0.067797f, -0.000046f, 0.043507f, 0.043532f, -0.000026f, -0.038566f, -0.096593f, -0.256798f, -0.694267f, -1.041581f, 1.011379f, 0.983319f, 1.013621f, 0.982728f, 2.907154f, 4.077826f, 4.737549f, -47.153562f, -46.312420f, -45.713778f, 100.001607f, 100.003211f, 100.004818f, 0.000002f};
float stds[35] = {0.000116f, 16.093140f, 11.326040f, 9.254162f, 3.149388f, 3.042273f, 2.984301f, 15.057561f, 11.316008f, 9.347656f, 3.734296f, 3.624178f, 1.313854f, 2.853142f, 2.709365f, 1.277773f, 4.409708f, 7.188475f, 11.774967f, 18.966044f, 23.041821f, 0.175691f, 0.168227f, 0.219472f, 0.209209f, 97.277825f, 106.074821f, 109.298195f, 30.882662f, 30.077193f, 29.523275f, 0.175784f, 0.246018f, 0.302535f, 0.000668f};

CTrade trade;
long onnx_handle;
int rsi7_h, rsi14_h, rsi21_h, atr7_h, atr14_h, atr21_h, adx7_h, adx14_h, adx21_h;
int macd1_h, macd2_h, e9_h, e21_h, e54_h, e144_h, e216_h;
int cci7_h, cci14_h, cci21_h, wpr7_h, wpr14_h, wpr21_h, mom7_h, mom14_h, mom21_h;

float input_data[4200]; // 120 length * 35 features = 4200

int OnInit() {
    onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
    if(onnx_handle == INVALID_HANDLE) { Print("❌ ONNX Load Error"); return(INIT_FAILED); }

    long in_shape[] = {1, 120, 35}; 
    if(!OnnxSetInputShape(onnx_handle, 0, in_shape)) return(INIT_FAILED);
    long out_shape[] = {1, 1}; // 1 Dense Layer Output Requirement
    if(!OnnxSetOutputShape(onnx_handle, 0, out_shape)) return(INIT_FAILED);
    
    rsi7_h = iRSI(_Symbol, PERIOD_M1, 7, PRICE_CLOSE);
    rsi14_h = iRSI(_Symbol, PERIOD_M1, 14, PRICE_CLOSE);
    rsi21_h = iRSI(_Symbol, PERIOD_M1, 21, PRICE_CLOSE);
    atr7_h = iATR(_Symbol, PERIOD_M1, 7);
    atr14_h = iATR(_Symbol, PERIOD_M1, 14);
    atr21_h = iATR(_Symbol, PERIOD_M1, 21);
    adx7_h = iADX(_Symbol, PERIOD_M1, 7);
    adx14_h = iADX(_Symbol, PERIOD_M1, 14);
    adx21_h = iADX(_Symbol, PERIOD_M1, 21);
    macd1_h = iMACD(_Symbol, PERIOD_M1, 12, 26, 9, PRICE_CLOSE);
    macd2_h = iMACD(_Symbol, PERIOD_M1, 9, 18, 9, PRICE_CLOSE);
    e9_h = iMA(_Symbol, PERIOD_M1, 9, 0, MODE_EMA, PRICE_CLOSE);
    e21_h = iMA(_Symbol, PERIOD_M1, 21, 0, MODE_EMA, PRICE_CLOSE);
    e54_h = iMA(_Symbol, PERIOD_M1, 54, 0, MODE_EMA, PRICE_CLOSE);
    e144_h = iMA(_Symbol, PERIOD_M1, 144, 0, MODE_EMA, PRICE_CLOSE);
    e216_h = iMA(_Symbol, PERIOD_M1, 216, 0, MODE_EMA, PRICE_CLOSE);
    cci7_h = iCCI(_Symbol, PERIOD_M1, 7, PRICE_CLOSE);
    cci14_h = iCCI(_Symbol, PERIOD_M1, 14, PRICE_CLOSE);
    cci21_h = iCCI(_Symbol, PERIOD_M1, 21, PRICE_CLOSE);
    wpr7_h = iWPR(_Symbol, PERIOD_M1, 7);
    wpr14_h = iWPR(_Symbol, PERIOD_M1, 14);
    wpr21_h = iWPR(_Symbol, PERIOD_M1, 21);
    mom7_h = iMomentum(_Symbol, PERIOD_M1, 7, PRICE_CLOSE);
    mom14_h = iMomentum(_Symbol, PERIOD_M1, 14, PRICE_CLOSE);
    mom21_h = iMomentum(_Symbol, PERIOD_M1, 21, PRICE_CLOSE);
    return(INIT_SUCCEEDED);
}

void OnTick() {
    static datetime last_bar;
    datetime curr_bar = iTime(_Symbol, PERIOD_M1, 0);
    if(curr_bar == last_bar) return;
    last_bar = curr_bar;

    if(!BuildWindow()) return;

    float output[1]; 
    if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output)) {
        Print("❌ OnnxRun Error"); return;
    }

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    double spread = ask - bid;
    long sl_pt = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
    
    double actual_dist = MathMax(1.44, (sl_pt * point) + spread + (10 * point)); 
    
    // Convert single output 
    double up_prob = output[0];
    double down_prob = 1.0 - up_prob;

    ulong pos_ticket = 0;
    int current_pos = GetCurrentPositionType(pos_ticket);

    if(current_pos == -1) {
        if(up_prob > 0.55) ExecuteTrade(ORDER_TYPE_BUY, ask, actual_dist, digits, up_prob);
        else if(down_prob > 0.55) ExecuteTrade(ORDER_TYPE_SELL, bid, actual_dist, digits, down_prob);
    }
    else if(current_pos == POSITION_TYPE_BUY && down_prob > 0.80) {
        if(trade.PositionClose(pos_ticket)) ExecuteTrade(ORDER_TYPE_SELL, bid, actual_dist, digits, down_prob);
    }
    else if(current_pos == POSITION_TYPE_SELL && up_prob > 0.80) {
        if(trade.PositionClose(pos_ticket)) ExecuteTrade(ORDER_TYPE_BUY, ask, actual_dist, digits, up_prob);
    }
}

int GetCurrentPositionType(ulong &ticket) {
    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        ulong t = PositionGetTicket(i);
        if(PositionGetString(POSITION_SYMBOL) == _Symbol) {
            string cm = PositionGetString(POSITION_COMMENT);
            if(cm == "Achilles_BUY" || cm == "Achilles_SELL") { // Safe lock
                ticket = t;
                return (int)PositionGetInteger(POSITION_TYPE);
            }
        }
    }
    return -1;
}

void ExecuteTrade(ENUM_ORDER_TYPE type, double price, double dist, int digits, double prob) {
    double sl = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price - dist, digits) : NormalizeDouble(price + dist, digits);
    double tp = (type == ORDER_TYPE_BUY) ? NormalizeDouble(price + dist, digits) : NormalizeDouble(price - dist, digits);
    string comment = (type == ORDER_TYPE_BUY) ? "Achilles_BUY" : "Achilles_SELL";
    
    if((type == ORDER_TYPE_BUY && trade.Buy(1.0, _Symbol, price, sl, tp, comment)) || 
       (type == ORDER_TYPE_SELL && trade.Sell(1.0, _Symbol, price, sl, tp, comment))) {
        PrintFormat("🤖 Achilles %s | Confidence Prob: %.2f%% | SL: %f | TP: %f", comment, prob*100, sl, tp);
    }
}

bool BuildWindow() {
    double usdx[]; if(CopyClose("$USDX", PERIOD_M1, 1, 121, usdx) < 121) return false;
    double o[], c[];
    if(CopyOpen(_Symbol, PERIOD_M1, 1, 120, o) < 120) return false;
    if(CopyClose(_Symbol, PERIOD_M1, 1, 120, c) < 120) return false;

    // Buffer collections optimization
    double r7[120], r14[120], r21[120], a7[120], a14[120], a21[120], ad7[120], ad14[120], ad21[120];
    CopyBuffer(rsi7_h, 0, 1, 120, r7); CopyBuffer(rsi14_h, 0, 1, 120, r14); CopyBuffer(rsi21_h, 0, 1, 120, r21);
    CopyBuffer(atr7_h, 0, 1, 120, a7); CopyBuffer(atr14_h, 0, 1, 120, a14); CopyBuffer(atr21_h, 0, 1, 120, a21);
    CopyBuffer(adx7_h, 0, 1, 120, ad7); CopyBuffer(adx14_h, 0, 1, 120, ad14); CopyBuffer(adx21_h, 0, 1, 120, ad21);
    
    double m1m[120], m1s[120], m2m[120], m2s[120];
    CopyBuffer(macd1_h, 0, 1, 120, m1m); CopyBuffer(macd1_h, 1, 1, 120, m1s);
    CopyBuffer(macd2_h, 0, 1, 120, m2m); CopyBuffer(macd2_h, 1, 1, 120, m2s);
    
    double em9[120], em21[120], em54[120], em144[120], em216[120];
    CopyBuffer(e9_h, 0, 1, 120, em9); CopyBuffer(e21_h, 0, 1, 120, em21); CopyBuffer(e54_h, 0, 1, 120, em54); 
    CopyBuffer(e144_h, 0, 1, 120, em144); CopyBuffer(e216_h, 0, 1, 120, em216);

    double c7[120], c14[120], c21[120], w7[120], w14[120], w21[120], mo7[120], mo14[120], mo21[120];
    CopyBuffer(cci7_h, 0, 1, 120, c7); CopyBuffer(cci14_h, 0, 1, 120, c14); CopyBuffer(cci21_h, 0, 1, 120, c21);
    CopyBuffer(wpr7_h, 0, 1, 120, w7); CopyBuffer(wpr14_h, 0, 1, 120, w14); CopyBuffer(wpr21_h, 0, 1, 120, w21);
    CopyBuffer(mom7_h, 0, 1, 120, mo7); CopyBuffer(mom14_h, 0, 1, 120, mo14); CopyBuffer(mom21_h, 0, 1, 120, mo21);

    for(int i = 0; i < 120; i++) {
        float f[35];
        f[0] = (float)((usdx[i+1] - usdx[i]) / usdx[i]);
        f[1] = (float)r7[i]; f[2] = (float)r14[i]; f[3] = (float)r21[i];
        f[4] = (float)a7[i]; f[5] = (float)a14[i]; f[6] = (float)a21[i];
        f[7] = (float)ad7[i]; f[8] = (float)ad14[i]; f[9] = (float)ad21[i];
        f[10] = (float)m1m[i]; f[11] = (float)m1s[i]; f[12] = (float)(m1m[i] - m1s[i]);
        f[13] = (float)m2m[i]; f[14] = (float)m2s[i]; f[15] = (float)(m2m[i] - m2s[i]);
        f[16] = (float)(em9[i] - c[i]); f[17] = (float)(em21[i] - c[i]); f[18] = (float)(em54[i] - c[i]);
        f[19] = (float)(em144[i] - c[i]); f[20] = (float)(em216[i] - c[i]);
        
        int shift = 120 - i;
        double vp14, vm14, vp9, vm9;
        CalcVortex(shift, 14, vp14, vm14); CalcVortex(shift, 9, vp9, vm9);
        f[21] = (float)vp14; f[22] = (float)vm14; f[23] = (float)vp9; f[24] = (float)vm9;
        
        f[25] = (float)c7[i]; f[26] = (float)c14[i]; f[27] = (float)c21[i];
        f[28] = (float)w7[i]; f[29] = (float)w14[i]; f[30] = (float)w21[i];
        f[31] = (float)mo7[i]; f[32] = (float)mo14[i]; f[33] = (float)mo21[i];
        f[34] = (float)((c[i] - o[i]) / o[i]);

        for(int k = 0; k < 35; k++) input_data[i * 35 + k] = (f[k] - means[k]) / stds[k];
    }
    return true;
}

void CalcVortex(int index, int period, double &vi_plus, double &vi_minus) {
    double sum_tr = 0, sum_vp = 0, sum_vm = 0;
    for(int i = 0; i < period; i++) {
        int s = index + i;
        double h = iHigh(_Symbol, PERIOD_M1, s), l = iLow(_Symbol, PERIOD_M1, s);
        double c_prev = iClose(_Symbol, PERIOD_M1, s+1);
        sum_tr += MathMax(h-l, MathMax(MathAbs(h-c_prev), MathAbs(l-c_prev)));
        sum_vp += MathAbs(h - iLow(_Symbol, PERIOD_M1, s+1));
        sum_vm += MathAbs(l - iHigh(_Symbol, PERIOD_M1, s+1));
    }
    vi_plus = (sum_tr == 0) ? 1.0 : sum_vp / sum_tr;
    vi_minus = (sum_tr == 0) ? 1.0 : sum_vm / sum_tr;
}