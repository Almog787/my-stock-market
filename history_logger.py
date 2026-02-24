import json
import pandas as pd
import yfinance as yf
import os
from datetime import datetime
import pytz

# --- הגדרות נתיבים ---
DATA_DIR = "data_hub"
HISTORY_DIR = os.path.join(DATA_DIR, "price_history_archive")
INDIVIDUAL_DIR = os.path.join(HISTORY_DIR, "individual_stocks") # תיקייה לקבצים נפרדים
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
CSV_HISTORY_FILE = os.path.join(HISTORY_DIR, "full_stocks_extended_history.csv")
TZ = pytz.timezone('Israel')

# יצירת תיקיות אם לא קיימות
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(INDIVIDUAL_DIR, exist_ok=True)

def fetch_comprehensive_history(tickers):
    """מושך היסטוריה מלאה של מחירים, דיבידנדים ושערי חליפין (5 שנים)"""
    all_data = []
    
    print("Fetching historical exchange rates (USD/ILS)...")
    usd_ils_hist = yf.download("ILS=X", period="5y", interval="1d", progress=False)['Close']

    for ticker in tickers:
        print(f"Fetching full 5-year history for {ticker}...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5y")
        dividends = stock.dividends
        current_pe = stock.info.get('trailingPE', None)

        for date, row in hist.iterrows():
            date_str = date.strftime('%Y-%m-%d %H:%M:%S')
            
            div_val = 0
            if date in dividends.index:
                div_val = float(dividends.loc[date])
            
            exchange_rate = 3.65 
            if date in usd_ils_hist.index:
                exchange_rate = float(usd_ils_hist.loc[date])

            all_data.append({
                "timestamp": date_str,
                "ticker": ticker,
                "price": round(float(row['Close']), 2),
                "dividend": round(div_val, 2),
                "pe_ratio": current_pe if date == hist.index[-1] else None,
                "usd_ils": round(exchange_rate, 4)
            })
            
    return pd.DataFrame(all_data)

def save_individual_files(df):
    """מפצל את ה-DataFrame המאוחד לקבצים נפרדים לכל מניה"""
    tickers = df['ticker'].unique()
    for ticker in tickers:
        ticker_df = df[df['ticker'] == ticker]
        file_path = os.path.join(INDIVIDUAL_DIR, f"{ticker}_history.csv")
        ticker_df.to_csv(file_path, index=False, encoding='utf-8')
    print(f"Updated {len(tickers)} individual stock files in {INDIVIDUAL_DIR}")

def update_csv_history():
    if not os.path.exists(PORTFOLIO_FILE):
        print("Portfolio file not found.")
        return
    
    with open(PORTFOLIO_FILE, 'r') as f:
        holdings = json.load(f)
    tickers = list(holdings.keys())

    if not os.path.exists(CSV_HISTORY_FILE):
        # הרצה ראשונה - בנייה מאפס
        print("Initial run: Building full historical database...")
        combined_df = fetch_comprehensive_history(tickers)
    else:
        # עדכון שוטף - הוספת נתוני היום
        print("Existing history found. Fetching today's update...")
        current_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
        
        # שער חליפין נוכחי
        try:
            usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]
        except:
            usd_ils = 3.65

        new_entries = []
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                if hist.empty: continue
                
                price = round(hist['Close'].iloc[-1], 2)
                divs = stock.dividends
                today_div = round(divs.iloc[-1], 2) if not divs.empty and (datetime.now().date() == divs.index[-1].date()) else 0
                pe = stock.info.get('trailingPE', None)

                new_entries.append({
                    "timestamp": current_time,
                    "ticker": ticker,
                    "price": price,
                    "dividend": today_div,
                    "pe_ratio": round(pe, 2) if pe else None,
                    "usd_ils": round(usd_ils, 4)
                })
            except Exception as e:
                print(f"Error updating {ticker}: {e}")

        new_df = pd.DataFrame(new_entries)
        old_df = pd.read_csv(CSV_HISTORY_FILE)
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['timestamp', 'ticker'], keep='last', inplace=True)
    
    # שמירת הקובץ המאוחד הראשי
    combined_df.to_csv(CSV_HISTORY_FILE, index=False, encoding='utf-8')
    
    # פיצול ושמירה לקבצים נפרדים
    save_individual_files(combined_df)
    
    print("All updates completed successfully.")

if __name__ == "__main__":
    update_csv_history()
