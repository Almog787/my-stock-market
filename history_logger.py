import json
import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz

# --- הגדרות נתיבים ---
DATA_DIR = "data_hub"
HISTORY_DIR = os.path.join(DATA_DIR, "price_history_archive")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
CSV_HISTORY_FILE = os.path.join(HISTORY_DIR, "full_stocks_extended_history.csv")
TZ = pytz.timezone('Israel')

os.makedirs(HISTORY_DIR, exist_ok=True)

def get_exchange_rate():
    """שליפת שער חליפין דולר-שקל עדכני"""
    try:
        usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]
        return round(usd_ils, 4)
    except:
        return 3.65  # Fallback

def fetch_stock_data(tickers):
    """איסוף מחיר, דיבידנד ו-P/E עבור רשימת מניות"""
    combined_data = []
    current_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    usd_ils = get_exchange_rate()

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            # מחיר אחרון
            hist = stock.history(period="1d")
            if hist.empty: continue
            
            price = round(hist['Close'].iloc[-1], 2)
            
            # דיבידנדים (מצטבר ליום האחרון אם היה)
            div = stock.dividends
            last_div = round(div.iloc[-1], 2) if not div.empty and (datetime.now().date() == div.index[-1].date()) else 0
            
            # יחס P/E (נתון נוכחי מה-Info)
            info = stock.info
            pe_ratio = info.get('trailingPE', info.get('forwardPE', None))
            if pe_ratio: pe_ratio = round(pe_ratio, 2)

            combined_data.append({
                "timestamp": current_time,
                "ticker": ticker,
                "price": price,
                "dividend": last_div,
                "pe_ratio": pe_ratio,
                "usd_ils": usd_ils
            })
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
    
    return combined_data

def update_csv_history():
    if not os.path.exists(PORTFOLIO_FILE):
        print("Portfolio file not found.")
        return
    
    with open(PORTFOLIO_FILE, 'r') as f:
        holdings = json.load(f)
    tickers = list(holdings.keys())

    print(f"Updating extended history for: {tickers}...")
    new_data = fetch_stock_data(tickers)
    
    if not new_data:
        print("No data collected.")
        return

    new_df = pd.DataFrame(new_data)

    if os.path.exists(CSV_HISTORY_FILE):
        old_df = pd.read_csv(CSV_HISTORY_FILE)
        # חיבור הנתונים החדשים לישנים
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
        # מניעת כפילויות (לפי זמן ומניה)
        combined_df.drop_duplicates(subset=['timestamp', 'ticker'], keep='last', inplace=True)
        combined_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
    else:
        new_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')

    print(f"Extended history updated successfully.")

if __name__ == "__main__":
    update_csv_history()
