import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import os
import logging

# --- הגדרות ---
HISTORY_FILE = "stock_history.json"
PORTFOLIO_FILE = "portfolio.json"
README_FILE = "README.md"
LOG_FILE = "error_log.txt"
TZ = pytz.timezone('Israel')

# הגדרת לוגים לקובץ טקסט
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_live_data():
    """הורדת נתונים שאינם בהיסטוריה המקומית (שער חליפין)"""
    try:
        usd_ils = yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]
        return usd_ils
    except Exception as e:
        logging.error(f"Failed to fetch exchange rate: {e}")
        return 3.65  # ערך ברירת מחדל למקרה של תקלה

def get_dividends(tickers, holdings):
    """איסוף דיבידנדים שנתיים (לא נמצא בדרך כלל בהיסטוריית מחירים)"""
    total_usd = 0
    details = {}
    for t_sym in tickers:
        try:
            ticker = yf.Ticker(t_sym)
            div_rate = ticker.info.get('dividendRate') or 0
            details[t_sym] = div_rate
            total_usd += (div_rate * holdings[t_sym])
        except Exception as e:
            logging.error(f"Dividend error for {t_sym}: {e}")
            details[t_sym] = 0
    return total_usd, details

def main():
    # 1. בדיקת קבצים
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        error_msg = "Missing HISTORY_FILE or PORTFOLIO_FILE"
        print(error_msg)
        logging.error(error_msg)
        return

    # 2. טעינת נתונים
    try:
        with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
        with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    except Exception as e:
        logging.error(f"JSON Parse error: {e}")
        return

    usd_to_ils = get_live_data()
    tickers = list(holdings.keys())

    # 3. עיבוד DataFrame מהקובץ המקומי
    df = pd.DataFrame([{"ts": pd.to_datetime(e['timestamp']), **e['prices']} for e in history])
    df['ts'] = df['ts'].dt.tz_localize(None)
    df = df.sort_values('ts')
    
    # חישוב שווי תיק יומי (במקום לחשב כל פעם מחדש בלולאות)
    df['portfolio_val_usd'] = df.apply(lambda row: sum(row[t] * holdings[t] for t in tickers if t in row), axis=1)

    now = datetime.now()
    output = []
    output.append(f"# 📈 דוח ביצועי תיק מניות חכם")
    output.append(f"**עודכן ב:** {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')} | **שער דולר:** ₪{usd_to_ils:.3f}\n")

    # פונקציית עזר לחישוב תשואה
    def calc_return(start_dt, end_dt):
        mask = (df['ts'] >= start_dt) & (df['ts'] <= end_dt)
        subset = df.loc[mask]
        if len(subset) < 2: return None
        v_start = subset['portfolio_val_usd'].iloc[0]
        v_end = subset['portfolio_val_usd'].iloc[-1]
        return {"ret": ((v_end / v_start) - 1) * 100, "gain": v_end - v_start}

    # 4. ביצועי חודש שוטף (מה-10 לחודש)
    anchor = 10
    curr_start = now.replace(day=anchor) if now.day >= anchor else (now.replace(day=anchor) - timedelta(days=30))
    p_curr = calc_return(curr_start, now)
    
    if p_curr:
        output.append("## 🏆 ביצועים (מה-10 לחודש)")
        output.append(f"- **תשואה:** `{p_curr['ret']:+.2f}%` | **רווח/הפסד:** `₪{p_curr['gain'] * usd_to_ils:,.0f}`\n")

    # 5. דיבידנדים (מצריך קריאת API קלה)
    total_div_usd, div_details = get_dividends(tickers, holdings)
    output.append("## 💰 צפי הכנסה מדיבידנדים (שנתי)")
    output.append(f"- **סכום שנתי:** `₪{total_div_usd * usd_to_ils:,.0f}`")
    output.append(f"- **ממוצע חודשי:** `₪{(total_div_usd * usd_to_ils / 12):,.0f}`\n")

    # 6. היסטוריית 12 חודשים (מה-10 ל-10)
    output.append("## 🗓️ היסטוריית רווח חודשית (₪)")
    output.append("| תקופה | רווח | תשואה |\n|---|---|---|")
    
    for i in range(12):
        target_end = (now.replace(day=anchor) - timedelta(days=30 * i))
        target_start = (target_end - timedelta(days=31)).replace(day=anchor)
        
        p = calc_return(target_start, target_end)
        if p:
            icon = "🟢" if p['gain'] >= 0 else "🔴"
            period_str = f"{target_start.strftime('%m/%y')} - {target_end.strftime('%m/%y')}"
            output.append(f"| {period_str} | {icon} ₪{p['gain'] * usd_to_ils:,.0f} | {p['ret']:.2f}% |")

    # 7. פירוט אחזקות
    output.append("\n## 📊 פירוט אחזקות נוכחי")
    output.append("| מניה | כמות | שווי (₪) | דיבידנד |\n|---|---|---|---|")
    
    last_prices = df.iloc[-1]
    for t in tickers:
        val_ils = last_prices[t] * holdings[t] * usd_to_ils
        div = div_details.get(t, 0)
        output.append(f"| {t} | {holdings[t]} | ₪{val_ils:,.0f} | ${div:.2f} |")

    output.append(f"\n**שווי תיק כולל:** `₪{df['portfolio_val_usd'].iloc[-1] * usd_to_ils:,.0f}`")

    # שמירה ל-README
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    
    print("Report generated successfully!")

if __name__ == "__main__":
    main()
