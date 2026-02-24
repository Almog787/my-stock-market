import json
import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz

# --- הגדרות נתיבים ---
DATA_DIR = "data_hub"
HISTORY_DIR = os.path.join(DATA_DIR, "price_history_archive") # תיקייה ייעודית
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
CSV_HISTORY_FILE = os.path.join(HISTORY_DIR, "full_stocks_history.csv")
TZ = pytz.timezone('Israel')

# יצירת תיקייה ייעודית אם לא קיימת
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_current_prices(tickers):
    """משיכת מחירים עדכניים עבור כל המניות ברשימה"""
    prices = {}
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).history(period="1d")
            if not data.empty:
                prices[ticker] = round(data['Close'].iloc[-1], 2)
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
    return prices

def update_csv_history():
    # 1. טעינת רשימת המניות מהפורטפוליו
    if not os.path.exists(PORTFOLIO_FILE):
        print("Portfolio file not found.")
        return
    
    with open(PORTFOLIO_FILE, 'r') as f:
        holdings = json.load(f)
    
    tickers = list(holdings.keys())
    
    # 2. קבלת מחירים וזמן נוכחי
    current_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    prices = get_current_prices(tickers)
    
    if not prices:
        print("No prices fetched. Skipping update.")
        return

    # 3. יצירת השורה החדשה
    new_entry = {"timestamp": current_time}
    new_entry.update(prices)
    new_df = pd.DataFrame([new_entry])

    # 4. עדכון קובץ ה-CSV
    if os.path.exists(CSV_HISTORY_FILE):
        # קריאת ההיסטוריה הקיימת והוספת השורה החדשה (Append)
        old_df = pd.read_csv(CSV_HISTORY_FILE)
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
        # מוודא שכל המניות מופיעות כעמודות גם אם נוספו מניות חדשות
        combined_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
    else:
        # יצירת קובץ חדש אם לא קיים
        new_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
    
    print(f"History updated successfully at {current_time}")

if __name__ == "__main__":
    update_csv_history()
