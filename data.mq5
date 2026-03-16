//+------------------------------------------------------------------+
//|                                            Data_Gatherer_144.mq5 |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

CTrade trade;
int rsi_h, atr_h, adx_h, macd_h, ema54_h, ema144_h, ema216_h, ema540_h;

struct BarRecord {
    datetime time;
    double usdx_c, rsi, atr, adx, vi_plus, vi_minus;
    double ema54, ema144, ema216, ema540;
    double macd_main, macd_sig, macd_hist;
    int label; // -1 = Pending/Loss, 0 = Sell Won, 1 = Buy Won
};

struct TradeTrack { ulong ticket; int history_idx; int type; };

BarRecord history[];
TradeTrack active_trades[];
int history_count = 0;

int OnInit() {
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
    CheckClosedTrades();
    
    static datetime last_bar;
    datetime curr_bar = iTime(_Symbol, PERIOD_M1, 0);
    if(curr_bar == last_bar) return;
    last_bar = curr_bar;

    // 1. Record Data for the just-closed bar (Index 1)
    ArrayResize(history, history_count + 1);
    BarRecord rec;
    rec.time = iTime(_Symbol, PERIOD_M1, 1);
    rec.label = -1;

    double c = iClose(_Symbol, PERIOD_M1, 1);
    double usdx[]; CopyClose("$USDX", PERIOD_M1, 1, 1, usdx); rec.usdx_c = usdx[0];
    
    double buf[1];
    CopyBuffer(rsi_h, 0, 1, 1, buf); rec.rsi = buf[0];
    CopyBuffer(atr_h, 0, 1, 1, buf); rec.atr = buf[0];
    CopyBuffer(adx_h, 0, 1, 1, buf); rec.adx = buf[0];
    
    CopyBuffer(macd_h, 0, 1, 1, buf); rec.macd_main = buf[0];
    CopyBuffer(macd_h, 1, 1, 1, buf); rec.macd_sig = buf[0];
    rec.macd_hist = rec.macd_main - rec.macd_sig;

    // Save EMAs as distance from close (Crucial for Neural Networks)
    CopyBuffer(ema54_h, 0, 1, 1, buf); rec.ema54 = buf[0] - c;
    CopyBuffer(ema144_h, 0, 1, 1, buf); rec.ema144 = buf[0] - c;
    CopyBuffer(ema216_h, 0, 1, 1, buf); rec.ema216 = buf[0] - c;
    CopyBuffer(ema540_h, 0, 1, 1, buf); rec.ema540 = buf[0] - c;

    CalcVortex(1, rec.vi_plus, rec.vi_minus);
    history[history_count] = rec;

    // 2. Place 1 Lot Trades ($144 = 1.44 points on Gold)
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
                
                if(profit > 0) // Hit Take Profit
                    history[active_trades[i].history_idx].label = active_trades[i].type;
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

void CalcVortex(int index, double &vi_plus, double &vi_minus) {
    double sum_tr = 0, sum_vp = 0, sum_vm = 0;
    for(int i = 0; i < 9; i++) {
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
    int h = FileOpen("training_144.csv", FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ",");
    FileWrite(h, "time", "usdx_ret", "rsi", "atr", "adx", "vi_p", "vi_m", "e54", "e144", "e216", "e540", "macd_m", "macd_s", "macd_h", "label");
    
    for(int i = 0; i < history_count; i++) {
        double usdx_ret = (i>0) ? (history[i].usdx_c - history[i-1].usdx_c)/history[i-1].usdx_c : 0;
        FileWrite(h, TimeToString(history[i].time), usdx_ret, history[i].rsi, history[i].atr, history[i].adx, 
                  history[i].vi_plus, history[i].vi_minus, history[i].ema54, history[i].ema144, 
                  history[i].ema216, history[i].ema540, history[i].macd_main, history[i].macd_sig, 
                  history[i].macd_hist, history[i].label);
    }
    FileClose(h);
    Print("✅ CSV Exported.");
}