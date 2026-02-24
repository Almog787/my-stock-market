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

def fetch_full_history(tickers):
    """מושך את כל היסטוריית המחירים עבור רשימת מניות"""
    print(f"Fetching full history for: {tickers}...")
    try:
        # מושך נתונים יומיים ל-5 השנים האחרונות כדי לבנות בסיס נתונים רחב
        data = yf.download(tickers, period="5y", interval="1d", progress=True)['Close']
        
        # אם יש רק מניה אחת, ה-Dataframe ייראה אחרת, נתקן זאת
        if len(tickers) == 1:
            data = data.to_frame()
            data.columns = tickers
            
        # ניקוי נתונים: הסרת שורות שבהן אין מידע לכל המניות (סופי שבוע/חגים)
        data = data.dropna(how='all')
        
        # עיצוב מחדש: הפיכת התאריך מעמודת אינדקס לעמודה רגילה בשם timestamp
        data.reset_index(inplace=True)
        data.rename(columns={'Date': 'timestamp'}, inplace=True)
        
        # המרת התאריך לפורמט טקסט נקי
        data['timestamp'] = data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return data
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return None

def update_csv_history():
    # 1. טעינת רשימת המניות מהפורטפוליו
    if not os.path.exists(PORTFOLIO_FILE):
        print("Portfolio file not found.")
        return
    
    with open(PORTFOLIO_FILE, 'r') as f:
        holdings = json.load(f)
    tickers = list(holdings.keys())

    # 2. בדיקה אם קובץ ה-CSV כבר קיים
    if not os.path.exists(CSV_HISTORY_FILE):
        # פעם ראשונה: בונים את כל ההיסטוריה
        df = fetch_full_history(tickers)
        if df is not None:
            df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
            print(f"Full history saved to {CSV_HISTORY_FILE}")
    else:
        # הקובץ קיים: מושכים רק את המחיר של היום ומוסיפים שורה
        print("CSV exists. Adding latest daily close price...")
        try:
            current_data = yf.download(tickers, period="1d", interval="1d", progress=False)['Close']
            current_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            
            # יצירת שורה חדשה
            new_entry = {"timestamp": current_time}
            if len(tickers) == 1:
                new_entry[tickers[0]] = round(float(current_data.iloc[-1]), 2)
            else:
                for t in tickers:
                    new_entry[t] = round(float(current_data[t].iloc[-1]), 2)
            
            new_df = pd.DataFrame([new_entry])
            
            # טעינת ישן וחיבור
            old_df = pd.read_csv(CSV_HISTORY_FILE)
            combined_df = pd.concat([old_df, new_df], ignore_index=True, sort=False)
            
            # הסרת כפילויות אם קיימות באותו תאריך
            combined_df.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
            
            combined_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
            print(f"Added latest data point for {current_time}")
        except Exception as e:
            print(f"Error updating CSV: {e}")

if __name__ == "__main__":
    update_csv_history()
