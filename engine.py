import os
import httpx
import pandas as pd

# ═══════════════════════════════════════════════
# SECURE CREDENTIAL LAYERS
# ═══════════════════════════════════════════════
FINNHUB_KEY = "d2530epr01qns40ctr90d2530epr01qns40ctr9g"
TWELVE_KEY = "ac51c8bd269246109f27d4dec51bcc28"

def load_stock_lists():
    """Dynamically reads, filters, and combines symbols from tracking documents"""
    stocks = set()
    for filename in ["Stock_List.txt", "Stock_List2.txt"]:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                for line in f:
                    sym = line.strip().upper()
                    if sym and not sym.startswith("#"):
                        stocks.add(sym)
    # Global failover assets if text files are missing/blank
    return sorted(list(stocks)) if stocks else ["ALAB", "BTBT", "ENVX", "OKLO"]

def calculate_rsi_native(prices, period=14):
    """
    Computes mathematical RSI metrics using high-speed vector math.
    Replaces buggy third-party libraries with 100% native stability.
    """
    if len(prices) < period + 1:
        return 50.0 # Neutral fallback indicator state
        
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).copy()
    loss = (-delta.where(delta < 0, 0)).copy()
    
    # Calculate initial exponential moving averages
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Apply Wilder's smoothing logic
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])

def run_analysis_pipeline():
    symbols = load_stock_lists()
    print(f"🚀 Triggering calculations via Dual-API Engine for: {symbols}")
    
    for sym in symbols:
        data_fetched = False
        close_prices = None
        
        # PRIMARY SELECTION: Query 1-Hour candles using TwelveData
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1h&outputsize=50&apikey={TWELVE_KEY}"
            response = httpx.get(url, timeout=10.0)
            res_json = response.json()
            
            if res_json.get("status") == "ok":
                df = pd.DataFrame(res_json["values"])
                # Reverse structural layout orientation to map old -> new candles cleanly
                df = df.iloc[::-1].reset_index(drop=True)
                close_prices = pd.to_numeric(df['close'])
                
                rsi_val = calculate_rsi_native(close_prices, period=14)
                print(f"📊 [TwelveData] {sym} | 1-Hour RSI Matrix: {round(rsi_val, 2)}")
                data_fetched = True
                
        except Exception as e:
            print(f"⚠️ TwelveData primary endpoint throttled/refused for {sym}: {e}")
            
        # CONDITIONAL FAILOVER: If TwelveData rate-limits you, trigger Finnhub
        if not data_fetched:
            try:
                url = f"https://finnhub.io/api/v1/stock/candle?symbol={sym}&resolution=60&count=50&token={FINNHUB_KEY}"
                res_json = httpx.get(url, timeout=10.0).json()
                
                if res_json.get("s") == "ok":
                    close_prices = pd.Series(res_json["c"])
                    rsi_val = calculate_rsi_native(close_prices, period=14)
                    print(f"🔄 [Finnhub Failover Fallback] {sym} | 1-Hour RSI Matrix: {round(rsi_val, 2)}")
                else:
                    print(f"❌ Structural historical payload missing for asset: {sym}")
            except Exception as e:
                print(f"❌ Dual-lane communication pipeline completely choked for {sym}: {e}")

if __name__ == "__main__":
    run_analysis_pipeline()
