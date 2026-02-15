import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import pytz

PORTFOLIO_FILE = "portfolio.json"
HISTORY_FILE = "stock_history.json"
TZ = pytz.timezone('Israel')

def main():
    if not os.path.exists(PORTFOLIO_FILE): return
    with open(PORTFOLIO_FILE, 'r') as f:
        holdings = json.load(f)
    tickers = list(holdings.keys())

    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = []

    # מנגנון השלמת נתונים שנה אחורה אם הקובץ ריק או חסר
    if not history:
        print("⏳ מבצע השלמת נתונים שנה אחורה...")
        hist_data = yf.download(tickers, period="1y", interval="1d")['Close']
        for date, row in hist_data.iterrows():
            history.append({
                "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
                "prices": {t: round(float(row[t]), 2) for t in tickers if not hasattr(row[t], 'isna') or not row[t].isna().any()}
            })

    # דגימה שעתית נוכחית
    data = yf.download(tickers, period="1d", interval="1h")['Close']
    current_prices = {t: round(float(data[t].iloc[-1]), 2) for t in tickers}
    
    history.append({
        "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "prices": current_prices
    })

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-10000:], f, indent=4) # שומר היסטוריה ארוכה

if __name__ == "__main__":
    main()
