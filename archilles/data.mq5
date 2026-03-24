//+------------------------------------------------------------------+
//|                                     Data_Gatherer_Achilles.mq5   |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

CTrade trade;
int rsi7_h, rsi14_h, rsi21_h;
int atr7_h, atr14_h, atr21_h;
int adx7_h, adx14_h, adx21_h;
int macd1_h, macd2_h;
int e9_h, e21_h, e54_h, e144_h, e216_h;
int cci7_h, cci14_h, cci21_h;
int wpr7_h, wpr14_h, wpr21_h;
int mom7_h, mom14_h, mom21_h;

struct BarRecord {
    datetime time;
    double f[35];   // 35 Features perfectly matching the Achilles architecture
    int label_buy;  // -1 = Pending, 0 = Loss, 1 = Win
    int label_sell; // -1 = Pending, 0 = Loss, 1 = Win
};

struct TradeTrack { ulong ticket; int history_idx; int type; };

BarRecord history[];
TradeTrack active_trades[];
int history_count = 0;

int OnInit() {
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

double GetBuf(int handle, int buffer=0, int shift=1) {
    double buf[1];
    if(CopyBuffer(handle, buffer, shift, 1, buf) > 0) return buf[0];
    return 0;
}

void OnTick() {
    CheckClosedTrades();
    
    static datetime last_bar;
    datetime curr_bar = iTime(_Symbol, PERIOD_M1, 0);
    if(curr_bar == last_bar) return;
    last_bar = curr_bar;

    ArrayResize(history, history_count + 1);
    BarRecord rec;
    rec.time = iTime(_Symbol, PERIOD_M1, 1);
    rec.label_buy = -1;  
    rec.label_sell = -1; 

    double c = iClose(_Symbol, PERIOD_M1, 1);
    double o = iOpen(_Symbol, PERIOD_M1, 1);
    
    double usdx[]; CopyClose("$USDX", PERIOD_M1, 1, 2, usdx); 
    rec.f[0]  = (usdx[1] - usdx[0]) / usdx[0]; 
    rec.f[1]  = GetBuf(rsi7_h);  rec.f[2]  = GetBuf(rsi14_h); rec.f[3]  = GetBuf(rsi21_h);
    rec.f[4]  = GetBuf(atr7_h);  rec.f[5]  = GetBuf(atr14_h); rec.f[6]  = GetBuf(atr21_h);
    rec.f[7]  = GetBuf(adx7_h);  rec.f[8]  = GetBuf(adx14_h); rec.f[9]  = GetBuf(adx21_h);
    
    rec.f[10] = GetBuf(macd1_h, 0); rec.f[11] = GetBuf(macd1_h, 1); rec.f[12] = rec.f[10] - rec.f[11];
    rec.f[13] = GetBuf(macd2_h, 0); rec.f[14] = GetBuf(macd2_h, 1); rec.f[15] = rec.f[13] - rec.f[14];
    
    rec.f[16] = GetBuf(e9_h) - c; rec.f[17] = GetBuf(e21_h) - c; rec.f[18] = GetBuf(e54_h) - c;
    rec.f[19] = GetBuf(e144_h) - c; rec.f[20] = GetBuf(e216_h) - c;

    double vp14, vm14, vp9, vm9;
    CalcVortex(1, 14, vp14, vm14); CalcVortex(1, 9, vp9, vm9);
    rec.f[21] = vp14; rec.f[22] = vm14; rec.f[23] = vp9; rec.f[24] = vm9;
    
    rec.f[25] = GetBuf(cci7_h); rec.f[26] = GetBuf(cci14_h); rec.f[27] = GetBuf(cci21_h);
    rec.f[28] = GetBuf(wpr7_h); rec.f[29] = GetBuf(wpr14_h); rec.f[30] = GetBuf(wpr21_h);
    rec.f[31] = GetBuf(mom7_h); rec.f[32] = GetBuf(mom14_h); rec.f[33] = GetBuf(mom21_h);
    
    rec.f[34] = (c - o) / o; 

    history[history_count] = rec;

    // Place dummy 1 Lot Trades ($144 = 1.44 points on Gold) to map outcome
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    
    if(trade.Buy(1.0, _Symbol, ask, ask - 1.44, ask + 1.44)) TrackTrade(trade.ResultOrder(), history_count, 1);
    if(trade.Sell(1.0, _Symbol, bid, bid + 1.44, bid - 1.44)) TrackTrade(trade.ResultOrder(), history_count, 0);

    history_count++;
}

void CheckClosedTrades() {
    for(int i = ArraySize(active_trades) - 1; i >= 0; i--) {
        if(!PositionSelectByTicket(active_trades[i].ticket)) {
            if(HistorySelectByPosition(active_trades[i].ticket)) {
                double profit = 0;
                for(int d = 0; d < HistoryDealsTotal(); d++) 
                    profit += HistoryDealGetDouble(HistoryDealGetTicket(d), DEAL_PROFIT);
                
                int won = (profit > 0) ? 1 : 0; 
                if(active_trades[i].type == 1) history[active_trades[i].history_idx].label_buy = won;
                else history[active_trades[i].history_idx].label_sell = won;
            }
            ArrayRemove(active_trades, i, 1);
        }
    }
}

void TrackTrade(ulong ticket, int idx, int type) {
    int s = ArraySize(active_trades);
    ArrayResize(active_trades, s + 1);
    active_trades[s].ticket = ticket;
    active_trades[s].history_idx = idx;
    active_trades[s].type = type;
}

void CalcVortex(int index, int period, double &vi_plus, double &vi_minus) {
    double sum_tr = 0, sum_vp = 0, sum_vm = 0;
    for(int i = 0; i < period; i++) {
        int s = index + i;
        double h = iHigh(_Symbol, PERIOD_CURRENT, s), l = iLow(_Symbol, PERIOD_CURRENT, s);
        double c_prev = iClose(_Symbol, PERIOD_CURRENT, s+1);
        sum_tr += MathMax(h-l, MathMax(MathAbs(h-c_prev), MathAbs(l-c_prev)));
        sum_vp += MathAbs(h - iLow(_Symbol, PERIOD_CURRENT, s+1));
        sum_vm += MathAbs(l - iHigh(_Symbol, PERIOD_CURRENT, s+1));
    }
    vi_plus = (sum_tr == 0) ? 1.0 : sum_vp / sum_tr;
    vi_minus = (sum_tr == 0) ? 1.0 : sum_vm / sum_tr;
}

void OnDeinit(const int reason) {
    int h = FileOpen("achilles.csv", FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
    string header = "time";
    for(int i = 0; i < 35; i++) header += ",f" + IntegerToString(i);
    header += ",label_buy,label_sell";
    FileWrite(h, header);
    
    for(int i = 0; i < history_count; i++) {
        string row = TimeToString(history[i].time);
        for(int k = 0; k < 35; k++) row += "," + DoubleToString(history[i].f[k], 6);
        row += "," + IntegerToString(history[i].label_buy) + "," + IntegerToString(history[i].label_sell);
        FileWrite(h, row);
    }
    FileClose(h);
    Print("✅ CSV Exported with 35 Features.");
}