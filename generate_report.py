import json
import pandas as pd
from datetime import datetime
import pytz
import os

HISTORY_FILE = "stock_history.json"
PORTFOLIO_FILE = "portfolio.json"
README_FILE = "README.md"
TZ = pytz.timezone('Israel')

def get_start_date(now):
    if now.day >= 10:
        return now.replace(day=10, hour=0, minute=0, second=0)
    month = now.month - 1 if now.month > 1 else 12
    year = now.year if now.month > 1 else now.year - 1
    return datetime(year, month, 10)

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE): return
    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    df = pd.DataFrame([{"ts": pd.to_datetime(e['timestamp']), **e['prices']} for e in history])
    now_local = datetime.now(TZ).replace(tzinfo=None)
    start_dt = get_start_date(now_local)
    
    # מחיר ה-10 לחודש
    base_row = df[df['ts'] >= start_dt].iloc[0]
    current_row = df.iloc[-1]

    output = f"# 📈 דוח תיק מניות - סיכום מה-10 לחודש\n\n"
    output += f"**זמן דוח:** {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}\n\n"
    output += "| מניה | כמות | מחיר ב-10 | מחיר נוכחי | רווח/הפסד | % שינוי |\n|---|---|---|---|---|---|\n"

    total_gain = 0
    for ticker, amount in holdings.items():
        p_base = base_row[ticker]
        p_now = current_row[ticker]
        gain = (p_now - p_base) * amount
        pct = ((p_now / p_base) - 1) * 100
        total_gain += gain
        icon = "✅" if gain >= 0 else "🔻"
        output += f"| {ticker} | {amount} | ${p_base:.2f} | ${p_now:.2f} | {icon} ${gain:,.2f} | {pct:.2f}% |\n"

    output += f"\n## 💰 רווח כולל לחודש זה: `${total_gain:,.2f}`\n"
    
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == "__main__":
    main()
