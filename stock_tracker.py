import yfinance as yf
import json
import os
import pandas as pd
from datetime import datetime, timedelta
import pytz

# הגדרות
PORTFOLIO_FILE = "portfolio.json"
HISTORY_FILE = "stock_history.json"
README_FILE = "README.md"
TZ = pytz.timezone('Israel')

def get_start_of_period():
    """מציב את תאריך היעד: ה-10 לחודש האחרון בשעה 00:00"""
    now = datetime.now(TZ)
    if now.day >= 10:
        start_date = now.replace(day=10, hour=0, minute=0, second=0, microsecond=0)
    else:
        month = now.month - 1 if now.month > 1 else 12
        year = now.year if now.month > 1 else now.year - 1
        start_date = datetime(year, month, 10, tzinfo=TZ)
    return start_date

def get_portfolio_data(holdings):
    tickers = list(holdings.keys())
    # שליפת נתונים נוכחיים
    data = yf.download(tickers, period="1d", interval="1h")['Close']
    
    current_stats = {}
    for ticker in tickers:
        current_stats[ticker] = data[ticker].iloc[-1]
    return current_stats

def backfill_history(holdings):
    """מושך היסטוריה שנה אחורה אם הקובץ לא קיים"""
    if os.path.exists(HISTORY_FILE):
        return
    
    print("⏳ מושך היסטוריה שנה אחורה... פעולה חד פעמית")
    tickers = list(holdings.keys())
    # משיכת נתונים יומיים לשנה האחרונה
    hist_data = yf.download(tickers, period="1y", interval="1d")['Close']
    
    history = []
    for date, row in hist_data.iterrows():
        entry = {
            "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
            "prices": {ticker: round(float(row[ticker]), 2) for ticker in tickers if not pd.isna(row[ticker])}
        }
        history.append(entry)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def main():
    if not os.path.exists(PORTFOLIO_FILE):
        print("נא ליצור קובץ portfolio.json")
        return

    with open(PORTFOLIO_FILE, 'r') as f:
        holdings = json.load(f)

    # 1. השלמת היסטוריה אם חסר
    backfill_history(holdings)

    # 2. קבלת מחירים נוכחיים
    current_prices = get_portfolio_data(holdings)
    
    # 3. טעינת היסטוריה וחישוב רווחים
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)
    
    # הוספת הדגימה הנוכחית להיסטוריה
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    history.append({"timestamp": now_str, "prices": current_prices})
    
    # 4. מציאת מחיר הבסיס (ה-10 לחודש)
    start_period = get_start_of_period()
    df_hist = pd.DataFrame([{"ts": pd.to_datetime(e['timestamp']), **e['prices']} for e in history])
    df_hist['ts'] = df_hist['ts'].dt.tz_localize(None)
    start_period_naive = start_period.replace(tzinfo=None)
    
    # מציאת השורה הקרובה ביותר ל-10 לחודש
    base_prices = df_hist[df_hist['ts'] >= start_period_naive].iloc[0]

    # 5. יצירת ה-README
    readme_output = f"# 📈 דוח ביצועי תיק מניות (מה-10 לחודש)\n\n"
    readme_output += f"**זמן עדכון:** {now_str}\n\n"
    readme_output += "| מניה | כמות | מחיר ב-10 לחודש | מחיר נוכחי | רווח/הפסד חודשי (סה\"כ) |\n"
    readme_output += "|---|---|---|---|---|\n"

    total_portfolio_gain = 0
    
    for ticker, amount in holdings.items():
        p_now = current_prices[ticker]
        p_base = base_prices[ticker]
        gain_per_unit = p_now - p_base
        total_ticker_gain = gain_per_unit * amount
        total_portfolio_gain += total_ticker_gain
        
        icon = "🟢" if total_ticker_gain >= 0 else "🔴"
        readme_output += f"| {ticker} | {amount} | ${p_base:.2f} | ${p_now:.2f} | {icon} ${total_ticker_gain:,.2f} |\n"

    readme_output += f"\n### 💰 סיכום רווח כולל לחודש זה: `${total_portfolio_gain:,.2f}`\n"
    
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_output)
    
    # שמירה מעודכנת של היסטוריה
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[-5000:], f, indent=4) # שמירת 5000 דגימות אחרונות

if __name__ == "__main__":
    main()
