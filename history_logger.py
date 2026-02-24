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
CSV_HISTORY_FILE = os.path.join(HISTORY_DIR, "full_stocks_history.csv")
TZ = pytz.timezone('Israel')

# יצירת תיקייה ייעודית אם לא קיימת
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_current_prices(tickers):
    """משיכת מחירים עדכניים עבור כל המניות ברשימה"""
    prices = {}
    # משיכת נתונים מרוכזת (יותר מהיר מ-Loop לכל טיקר בנפרד)
    try:
        data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
        for ticker in tickers:
            # תמיכה גם אם הורדנו מניה אחת (Series) או כמה (DataFrame)
            if len(tickers) == 1:
                price = data.iloc[-1]
            else:
                price = data[ticker].iloc[-1]
            
            if pd.notnull(price):
                prices[ticker] = round(float(price), 2)
    except Exception as e:
        print(f"Error fetching prices: {e}")
    return prices

def update_csv_history():
    # 1. טעינת רשימת המניות מהפורטפוליו
    if not os.path.exists(PORTFOLIO_FILE):
        print(f"Portfolio file not found at {PORTFOLIO_FILE}")
        return
    
    try:
        with open(PORTFOLIO_FILE, 'r') as f:
            holdings = json.load(f)
        tickers = list(holdings.keys())
    except Exception as e:
        print(f"Error reading portfolio.json: {e}")
        return
    
    # 2. קבלת מחירים וזמן נוכחי
    current_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    prices = get_current_prices(tickers)
    
    if not prices:
        print("No prices fetched. Skipping update.")
        return

    # 3. יצירת השורה החדשה כ-DataFrame
    new_entry = {"timestamp": current_time}
    new_entry.update(prices)
    new_df = pd.DataFrame([new_entry])

    # 4. עדכון קובץ ה-CSV
    if os.path.exists(CSV_HISTORY_FILE):
        try:
            # קריאת ההיסטוריה הקיימת
            old_df = pd.read_csv(CSV_HISTORY_FILE)
            
            # חיבור הנתונים - sort=False שומר על סדר העמודות המקורי
            # אם נוספה מניה חדשה, פנדס יוסיף עמודה וערכי NaN לשורות ישנות
            combined_df = pd.concat([old_df, new_df], ignore_index=True, sort=False)
            
            combined_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
            print(f"Successfully appended to {CSV_HISTORY_FILE}")
        except Exception as e:
            print(f"Error updating existing CSV: {e}")
    else:
        # יצירת קובץ חדש לחלוטין
        new_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
        print(f"Created new history file at {CSV_HISTORY_FILE}")
    
    print(f"Update complete: {current_time}")

if __name__ == "__main__":
    update_csv_history()
