import json
import pandas as pd
from datetime import datetime
import pytz
import os
import yfinance as yf

HISTORY_FILE = "stock_history.json"
PORTFOLIO_FILE = "portfolio.json"
README_FILE = "README.md"
TZ = pytz.timezone('Israel')

def get_exchange_rate():
    """מושך את שער הדולר/שקל העדכני"""
    ticker = yf.Ticker("ILS=X")
    data = ticker.history(period="1d")
    return data['Close'].iloc[-1]

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        return

    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    # משיכת שער חליפין
    usd_to_ils = get_exchange_rate()

    # יצירת DataFrame וניקוי נתונים
    df = pd.DataFrame([{"ts": pd.to_datetime(e['timestamp']), **e['prices']} for e in history])
    df['ts'] = df['ts'].dt.tz_localize(None)
    df = df.sort_values('ts')

    output = f"# 📈 דוח ביצועי תיק מניות (בשקלים)\n\n"
    output += f"**עודכן ב:** {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}\n"
    output += f"**שער דולר עדכני:** ₪{usd_to_ils:.3f}\n\n"

    # --- חלק 1: סיכום חודשי (שנה אחורה) ---
    output += "## 🗓️ רווח/הפסד לפי חודשים (ILS)\n\n"
    output += "| תקופה | רווח/הפסד (₪) | תשואה |\n|---|---|---|\n"

    monthly_data = []
    now = datetime.now()
    
    for i in range(12):
        target_month = now.month - i
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        end_dt = datetime(target_year, target_month, 10)
        start_month = target_month - 1
        start_year = target_year
        if start_month <= 0:
            start_month = 12
            start_year -= 1
        start_dt = datetime(start_year, start_month, 10)

        period_data = df[(df['ts'] >= start_dt) & (df['ts'] <= end_dt)]
        
        if len(period_data) >= 2:
            first_day = period_data.iloc[0]
            last_day = period_data.iloc[-1]
            
            month_gain_usd = 0
            month_start_value_usd = 0
            
            for ticker, amount in holdings.items():
                if ticker in first_day and ticker in last_day:
                    gain = (last_day[ticker] - first_day[ticker]) * amount
                    month_gain_usd += gain
                    month_start_value_usd += (first_day[ticker] * amount)
            
            month_gain_ils = month_gain_usd * usd_to_ils
            pct = (month_gain_usd / month_start_value_usd * 100) if month_start_value_usd != 0 else 0
            icon = "🟢" if month_gain_ils >= 0 else "🔴"
            period_str = f"{start_dt.strftime('%m/%y')} - {end_dt.strftime('%m/%y')}"
            monthly_data.append(f"| {period_str} | {icon} ₪{month_gain_ils:,.0f} | {pct:.2f}% |")

    output += "\n".join(monthly_data) + "\n\n"

    # --- חלק 2: פירוט אחזקות נוכחיות ---
    output += "## 📊 פירוט אחזקות נוכחי (ILS)\n\n"
    output += "| מניה | כמות | מחיר (₪) | שווי כולל (₪) |\n|---|---|---|---|\n"
    
    current_row = df.iloc[-1]
    total_portfolio_ils = 0
    
    for ticker, amount in holdings.items():
        price_usd = current_row[ticker]
        price_ils = price_usd * usd_to_ils
        value_ils = price_ils * amount
        total_portfolio_ils += value_ils
        output += f"| {ticker} | {amount} | ₪{price_ils:,.2f} | ₪{value_ils:,.0f} |\n"

    output += f"\n**שווי תיק כולל בשקלים:** `₪{total_portfolio_ils:,.0f}`\n"

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == "__main__":
    main()
