//+------------------------------------------------------------------+
//|                                              Live_Trader_144.mq5 |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

// 1. Ensure model_144.onnx is in your MQL5/Files/ folder!
#resource "\\Files\\model_144.onnx" as uchar model_buffer[]

// --- REPLACE THESE WITH YOUR EXACT SCALER VALUES FROM PYTHON ---
// Make sure every number ends with an 'f' (e.g., 0.05f)
float means[] = {0.0f, 50.0f, 1.0f, 25.0f, 1.0f, 1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
float stds[]  = {0.01f, 15.0f, 0.5f, 10.0f, 0.2f, 0.2f, 2.0f, 3.0f, 4.0f, 5.0f, 1.0f, 1.0f, 0.5f};

CTrade trade;
long onnx_handle;
int rsi_h, atr_h, adx_h, macd_h, ema54_h, ema144_h, ema216_h, ema540_h;

// 2. FLAT 1D Array for strict MT5 compatibility (30 time steps * 13 features = 390)
float input_data[390]; 

int OnInit() {
    onnx_handle = OnnxCreateFromBuffer(model_buffer, ONNX_DEFAULT);
    if(onnx_handle == INVALID_HANDLE) {
        Print("❌ ONNX Load Error: ", GetLastError());
        return(INIT_FAILED);
    }

    // 3. STRICT SHAPE LOCKING
    long in_shape[] = {1, 30, 13}; // [Batch, Time, Features]
    if(!OnnxSetInputShape(onnx_handle, 0, in_shape)) {
        Print("❌ Input Shape Error: ", GetLastError());
        return(INIT_FAILED);
    }
    
    long out_shape[] = {1, 1}; // [Batch, Output Node]
    if(!OnnxSetOutputShape(onnx_handle, 0, out_shape)) {
        Print("❌ Output Shape Error: ", GetLastError());
        return(INIT_FAILED);
    }
    
    // Initialize Indicators
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

    // Build the 30-bar feature window
    if(!BuildWindow()) return;

    // Run Inference
    float output[1]; 
    if(!OnnxRun(onnx_handle, ONNX_DEFAULT, input_data, output)) {
        Print("❌ OnnxRun Error: ", GetLastError());
        return;
    }

    // Execution Logic
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

    // AI Prediction: >0.55 means BUY, <0.45 means SELL
    if(output[0] > 0.55) {
        trade.Buy(1.0, _Symbol, ask, ask - 1.44, ask + 1.44, "AI_BUY");
        Print("🤖 AI BUY Signal! Confidence: ", output[0]);
    }
    else if(output[0] < 0.45) {
        trade.Sell(1.0, _Symbol, bid, bid + 1.44, bid - 1.44, "AI_SELL");
        Print("🤖 AI SELL Signal! Confidence: ", output[0]);
    }
}

bool BuildWindow() {
    double c[], usdx[], buf[];
    ArraySetAsSeries(c, true); 
    ArraySetAsSeries(usdx, true);
    
    // Fetch 32 bars. Index 1 is the most recently closed bar.
    if(CopyClose(_Symbol, PERIOD_M1, 0, 32, c) < 32) return false;
    if(CopyClose("$USDX", PERIOD_M1, 0, 32, usdx) < 32) return false;

    for(int i = 0; i < 30; i++) {
        // LSTM expects chronological order. 
        // i = 0 is oldest (shift 30). i = 29 is newest closed (shift 1).
        int shift = 30 - i; 
        
        float f[13];
        // 0. Return: (Current - Previous) / Previous. In Series array, previous is shift+1
        f[0] = (float)((usdx[shift] - usdx[shift+1]) / usdx[shift+1]); 
        
        CopyBuffer(rsi_h, 0, shift, 1, buf); f[1] = (float)buf[0];
        CopyBuffer(atr_h, 0, shift, 1, buf); f[2] = (float)buf[0];
        CopyBuffer(adx_h, 0, shift, 1, buf); f[3] = (float)buf[0];
        
        double vp, vm; CalcVortex(shift, vp, vm);
        f[4] = (float)vp; f[5] = (float)vm;
        
        // EMAs as distance from close
        CopyBuffer(ema54_h, 0, shift, 1, buf); f[6] = (float)(buf[0] - c[shift]);
        CopyBuffer(ema144_h, 0, shift, 1, buf); f[7] = (float)(buf[0] - c[shift]);
        CopyBuffer(ema216_h, 0, shift, 1, buf); f[8] = (float)(buf[0] - c[shift]);
        CopyBuffer(ema540_h, 0, shift, 1, buf); f[9] = (float)(buf[0] - c[shift]);
        
        // MACD
        CopyBuffer(macd_h, 0, shift, 1, buf); f[10] = (float)buf[0]; // Main
        CopyBuffer(macd_h, 1, shift, 1, buf); f[11] = (float)buf[0]; // Signal
        f[12] = f[10] - f[11]; // Histogram

        // Apply Scaling and map directly into the Flat 1D Array
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