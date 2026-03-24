//+------------------------------------------------------------------+
//|                                              Live_Trader_144.mq5 |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

#resource "\\Files\\model_144.onnx" as uchar model_buffer[]

// --- REPLACE THESE WITH YOUR EXACT SCALER VALUES FROM PYTHON OUTPUT ---
float means[] = {0.000000f, 51.189174f, 51.075032f, 51.004080f, 3.517946f, 3.517941f, 3.517926f, 42.348980f, 30.035590f, 24.474167f, 0.067751f, 0.067797f, -0.000046f, 0.043507f, 0.043532f, -0.000026f, -0.038566f, -0.096593f, -0.256798f, -0.694267f, -1.041581f, 1.011379f, 0.983319f, 1.013621f, 0.982728f, 2.907154f, 4.077826f, 4.737549f, -47.153562f, -46.312420f, -45.713778f, 100.001607f, 100.003211f, 100.004818f, 0.000002f};
float stds[] = {0.000116f, 16.093140f, 11.326040f, 9.254162f, 3.149388f, 3.042273f, 2.984301f, 15.057561f, 11.316008f, 9.347656f, 3.734296f, 3.624178f, 1.313854f, 2.853142f, 2.709365f, 1.277773f, 4.409708f, 7.188475f, 11.774967f, 18.966044f, 23.041821f, 0.175691f, 0.168227f, 0.219472f, 0.209209f, 97.277825f, 106.074821f, 109.298195f, 30.882662f, 30.077193f, 29.523275f, 0.175784f, 0.246018f, 0.302535f, 0.000668f};

CTrade trade;
long onnx_handle;
int rsi_h, atr_h, adx_h, macd_h, ema54_h, ema144_h, ema216_h, ema540_h;

float input_data[390]; 

int OnInit() {
    onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
    if(onnx_handle == INVALID_HANDLE) {
        Print("❌ ONNX Load Error: ", GetLastError());
        return(INIT_FAILED);
    }

    long in_shape[] = {1, 30, 13}; 
    if(!OnnxSetInputShape(onnx_handle, 0, in_shape)) {
        Print("❌ Input Shape Error: ", GetLastError());
        return(INIT_FAILED);
    }
    
    long out_shape[] = {1, 2}; 
    if(!OnnxSetOutputShape(onnx_handle, 0, out_shape)) {
        Print("❌ Output Shape Error: ", GetLastError());
        return(INIT_FAILED);
    }
    
    rsi_h = iRSI(_Symbol, PERIOD_M1, 9, PRICE_CLOSE);
    atr_h = iATR(_Symbol, PERIOD_M1, 9);
    adx_h = iADX(_Symbol, PERIOD_M1, 9);
    macd_h = iMACD(_Symbol, PERIOD_M1, 9, 18, 9, PRICE_CLOSE);
    ema54_h = iMA(_Symbol, PERIOD_M1, 54, 0, MODE_EMA, PRICE_CLOSE);
    ema144_h = iMA(_Symbol, PERIOD_M1, 144, 0, MODE_EMA, PRICE_CLOSE);
    ema216_h = iMA(_Symbol, PERIOD_M1, 216, 0, MODE_EMA, PRICE_CLOSE);
    ema540_h = iMA(_Symbol, PERIOD_M1, 540, 0, MODE_EMA, PRICE_CLOSE);
    
    return(INIT_SUCCEEDED);
}

void OnTick() {
    static datetime last_bar;
    datetime curr_bar = iTime(_Symbol, PERIOD_M1, 0);
    if(curr_bar == last_bar) return;
    last_bar = curr_bar;

    if(!BuildWindow()) return;

    float output[2]; 
    if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output)) {
        Print("❌ OnnxRun Error: ", GetLastError());
        return;
    }

    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    
    int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
    double spread = ask - bid;
    long stop_level_points = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
    
    double min_safe_dist = (stop_level_points * point) + spread;
    double desired_dist = 1.44;
    double actual_dist = MathMax(desired_dist, min_safe_dist + (10 * point)); 
    
    // Evaluate BOTH predictions
    double buy_prob = output[0];
    double sell_prob = output[1];

    // Check Current Open Positions
    ulong pos_ticket = 0;
    int current_pos = GetCurrentPositionType(pos_ticket);

    // --- STATE 1: NO ACTIVE TRADES ---
    if(current_pos == -1) {
        if(buy_prob > sell_prob && buy_prob > 0.55) {
            ExecuteTrade(ORDER_TYPE_BUY, ask, actual_dist, digits, buy_prob, sell_prob);
        }
        else if(sell_prob > buy_prob && sell_prob > 0.55) {
            ExecuteTrade(ORDER_TYPE_SELL, bid, actual_dist, digits, buy_prob, sell_prob);
        }
    }
    // --- STATE 2: CURRENTLY HOLDING A BUY ---
    else if(current_pos == POSITION_TYPE_BUY) {
        // Only react if AI screams a strong SELL reversal (> 0.80)
        if(sell_prob > 0.80 && sell_prob > buy_prob) {
            Print("🔄 AI Strong SELL Reversal! Closing BUY and opening SELL.");
            if(trade.PositionClose(pos_ticket)) {
                ExecuteTrade(ORDER_TYPE_SELL, bid, actual_dist, digits, buy_prob, sell_prob);
            } else {
                Print("❌ Reversal Close Error: ", GetLastError());
            }
        }
    }
    // --- STATE 3: CURRENTLY HOLDING A SELL ---
    else if(current_pos == POSITION_TYPE_SELL) {
        // Only react if AI screams a strong BUY reversal (> 0.80)
        if(buy_prob > 0.80 && buy_prob > sell_prob) {
            Print("🔄 AI Strong BUY Reversal! Closing SELL and opening BUY.");
            if(trade.PositionClose(pos_ticket)) {
                ExecuteTrade(ORDER_TYPE_BUY, ask, actual_dist, digits, buy_prob, sell_prob);
            } else {
                Print("❌ Reversal Close Error: ", GetLastError());
            }
        }
    }
}

// Helper: Safely gets the position type for THIS symbol
int GetCurrentPositionType(ulong &ticket) {
    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        ulong t = PositionGetTicket(i);
        if(PositionGetString(POSITION_SYMBOL) == _Symbol) {
            ticket = t;
            return (int)PositionGetInteger(POSITION_TYPE); // Returns POSITION_TYPE_BUY or POSITION_TYPE_SELL
        }
    }
    return -1; // No open positions for this symbol
}

// Helper: Executes trade to keep OnTick clean
void ExecuteTrade(ENUM_ORDER_TYPE type, double price, double dist, int digits, double p_buy, double p_sell) {
    if(type == ORDER_TYPE_BUY) {
        double sl = NormalizeDouble(price - dist, digits);
        double tp = NormalizeDouble(price + dist, digits);
        if(trade.Buy(1.0, _Symbol, price, sl, tp, "AI_BUY")) {
            PrintFormat("🤖 AI BUY Signal! Buy Prob: %.2f%% | Sell Prob: %.2f%% | SL: %f | TP: %f", p_buy*100, p_sell*100, sl, tp);
        } else {
            Print("❌ Buy Error: ", GetLastError());
        }
    } else {
        double sl = NormalizeDouble(price + dist, digits);
        double tp = NormalizeDouble(price - dist, digits);
        if(trade.Sell(1.0, _Symbol, price, sl, tp, "AI_SELL")) {
            PrintFormat("🤖 AI SELL Signal! Buy Prob: %.2f%% | Sell Prob: %.2f%% | SL: %f | TP: %f", p_buy*100, p_sell*100, sl, tp);
        } else {
            Print("❌ Sell Error: ", GetLastError());
        }
    }
}

bool BuildWindow() {
    double c[], usdx[], buf[];
    ArraySetAsSeries(c, true); 
    ArraySetAsSeries(usdx, true);
    
    if(CopyClose(_Symbol, PERIOD_M1, 0, 32, c) < 32) return false;
    if(CopyClose("$USDX", PERIOD_M1, 0, 32, usdx) < 32) return false;

    for(int i = 0; i < 30; i++) {
        int shift = 30 - i; 
        
        float f[13];
        f[0] = (float)((usdx[shift] - usdx[shift+1]) / usdx[shift+1]); 
        
        CopyBuffer(rsi_h, 0, shift, 1, buf); f[1] = (float)buf[0];
        CopyBuffer(atr_h, 0, shift, 1, buf); f[2] = (float)buf[0];
        CopyBuffer(adx_h, 0, shift, 1, buf); f[3] = (float)buf[0];
        
        double vp, vm; CalcVortex(shift, vp, vm);
        f[4] = (float)vp; f[5] = (float)vm;
        
        CopyBuffer(ema54_h, 0, shift, 1, buf); f[6] = (float)(buf[0] - c[shift]);
        CopyBuffer(ema144_h, 0, shift, 1, buf); f[7] = (float)(buf[0] - c[shift]);
        CopyBuffer(ema216_h, 0, shift, 1, buf); f[8] = (float)(buf[0] - c[shift]);
        CopyBuffer(ema540_h, 0, shift, 1, buf); f[9] = (float)(buf[0] - c[shift]);
        
        CopyBuffer(macd_h, 0, shift, 1, buf); f[10] = (float)buf[0]; 
        CopyBuffer(macd_h, 1, shift, 1, buf); f[11] = (float)buf[0]; 
        f[12] = f[10] - f[11]; 

        for(int k = 0; k < 13; k++) {
            input_data[i * 13 + k] = (f[k] - means[k]) / stds[k];
        }
    }
    return true;
}

void CalcVortex(int index, double &vi_plus, double &vi_minus) {
    double sum_tr = 0, sum_vp = 0, sum_vm = 0;
    for(int i = 0; i < 9; i++) {
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