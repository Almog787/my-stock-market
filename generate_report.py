import json
import pandas as pd
from datetime import datetime
import pytz
import os

HISTORY_FILE = "stock_history.json"
PORTFOLIO_FILE = "portfolio.json"
README_FILE = "README.md"
TZ = pytz.timezone('Israel')

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        return

    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    # יצירת DataFrame וניקוי נתונים
    df = pd.DataFrame([{"ts": pd.to_datetime(e['timestamp']), **e['prices']} for e in history])
    df['ts'] = df['ts'].dt.tz_localize(None)
    df = df.sort_values('ts')

    output = f"# 📈 דוח ביצועי תיק מניות שנתי\n\n"
    output += f"**עודכן ב:** {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}\n\n"

    # --- חלק 1: סיכום חודשי (שנה אחורה) ---
    output += "## 🗓️ רווח/הפסד לפי חודשים (מה-10 ל-10)\n\n"
    output += "| תקופה | רווח/הפסד דולרי | תשואה |\n|---|---|---|\n"

    monthly_data = []
    now = datetime.now()
    
    # לולאה שרצה 12 חודשים אחורה
    for i in range(12):
        # חישוב תאריכי התחלה וסוף (מה-10 ל-10)
        target_month = now.month - i
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        end_dt = datetime(target_year, target_month, 10)
        # חודש קודם
        start_month = target_month - 1
        start_year = target_year
        if start_month <= 0:
            start_month = 12
            start_year -= 1
        start_dt = datetime(start_year, start_month, 10)

        # סינון הנתונים לתקופה הזו
        period_data = df[(df['ts'] >= start_dt) & (df['ts'] <= end_dt)]
        
        if len(period_data) >= 2:
            first_day = period_data.iloc[0]
            last_day = period_data.iloc[-1]
            
            month_gain = 0
            month_start_value = 0
            
            for ticker, amount in holdings.items():
                if ticker in first_day and ticker in last_day:
                    gain = (last_day[ticker] - first_day[ticker]) * amount
                    month_gain += gain
                    month_start_value += (first_day[ticker] * amount)
            
            pct = (month_gain / month_start_value * 100) if month_start_value != 0 else 0
            icon = "🟢" if month_gain >= 0 else "🔴"
            period_str = f"{start_dt.strftime('%m/%y')} - {end_dt.strftime('%m/%y')}"
            monthly_data.append(f"| {period_str} | {icon} ${month_gain:,.2f} | {pct:.2f}% |")

    output += "\n".join(monthly_data) + "\n\n"

    # --- חלק 2: פירוט אחזקות נוכחיות ---
    output += "## 📊 פירוט אחזקות נוכחי (חודש שוטף)\n\n"
    output += "| מניה | כמות | מחיר נוכחי | שווי כולל |\n|---|---|---|---|\n"
    
    current_row = df.iloc[-1]
    total_portfolio_value = 0
    
    for ticker, amount in holdings.items():
        price = current_row[ticker]
        value = price * amount
        total_portfolio_value += value
        output += f"| {ticker} | {amount} | ${price:.2f} | ${value:,.2f} |\n"

    output += f"\n**שווי תיק כולל:** `${total_portfolio_value:,.2f}`\n"

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == "__main__":
    main()
