import os
import httpx
import pandas as pd
import pandas_ta as ta

# SECURE CREDENTIAL BACKEND MATRIX
FINNHUB_KEY = "d2530epr01qns40ctr90d2530epr01qns40ctr9g"
TWELVE_KEY = "ac51c8bd269246109f27d4dec51bcc28"

def load_stock_lists():
    """Aggregates and formats stock symbols from repository configuration tracking files"""
    stocks = set()
    for filename in ["Stock_List.txt", "Stock_List2.txt"]:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                for line in f:
                    sym = line.strip().upper()
                    if sym and not sym.startswith("#"):
                        stocks.add(sym)
    return list(stocks) if stocks else ["ALAB", "BTBT", "ENVX", "OKLO"]

def run_analysis_pipeline():
    symbols = load_stock_lists()
    print(f"🚀 Triggering calculations via Dual-API Engine for: {symbols}")
    
    for sym in symbols:
        data_fetched = False
        res_data = None
        
        # PRIMARY: Pull structural indicators from TwelveData
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1h&outputsize=50&apikey={TWELVE_KEY}"
            response = httpx.get(url, timeout=10.0)
            res_json = response.json()
            
            if res_json.get("status") == "ok":
                # Convert TwelveData schema layout to structural DataFrame
                df = pd.DataFrame(res_json["values"])
                df['close'] = pd.to_numeric(df['close'])
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                # Reverse dataframe so chronological order maps oldest -> newest for pandas_ta
                df = df.iloc[::-1].reset_index(drop=True)
                
                rsi = ta.rsi(df['close'], length=14)
                latest_rsi = rsi.iloc[-1]
                print(f"📊 [TwelveData] {sym} | 1-Hour RSI: {round(latest_rsi, 2)}")
                data_fetched = True
        except Exception as e:
            print(f"⚠️ TwelveData pipeline throttled/failed for {sym}: {e}")
            
        # SECONDARY FAILOVER: If TwelveData hits rate limits, try Finnhub
        if not data_fetched:
            try:
                url = f"https://finnhub.io/api/v1/stock/candle?symbol={sym}&resolution=60&count=50&token={FINNHUB_KEY}"
                res_json = httpx.get(url, timeout=10.0).json()
                if res_json.get("s") == "ok":
                    df = pd.DataFrame(res_json)
                    rsi = ta.rsi(df['c'], length=14)
                    print(f"🔄 [Finnhub Failover Fallback] {sym} | 1-Hour RSI: {round(rsi.iloc[-1], 2)}")
            except Exception as e:
                print(f"❌ Both data pipelines exhausted for token {sym}: {e}")

if __name__ == "__main__":
    run_analysis_pipeline()