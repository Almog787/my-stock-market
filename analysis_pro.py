import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

# הגדרות נתיבים
DATA_DIR = "data_hub"
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
REPORT_FILE = "ANALYSIS_REPORT.md"
PREDICTION_CHART = os.path.join(DATA_DIR, "analysis_chart.png")

def calculate_rsi(series, period=14):
    """חישוב RSI בשיטת Wilder המקצועית"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    
    # שימוש ב-EWM לחישוב ממוצע מוחלק
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_analysis(df, ticker):
    """ניתוח מעמיק הכולל Z-Score, RSI ומומנטום"""
    prices = df[ticker].dropna()
    if len(prices) < 50:
        return None

    # 1. Z-Score על חלון זמן של 90 יום (מניעת הטיות היסטוריות)
    window = min(len(prices), 90)
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    z_score = (prices.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]

    # 2. RSI
    rsi_series = calculate_rsi(prices)
    current_rsi = rsi_series.iloc[-1]

    # 3. Momentum (EMA Cross)
    ema_short = prices.ewm(span=20, adjust=False).mean().iloc[-1]
    ema_long = prices.ewm(span=50, adjust=False).mean().iloc[-1]
    
    # תרגום לטקסט
    if z_score > 1.8:
        rev_status = "🔴 מתיחת יתר (יקר)"
    elif z_score < -1.8:
        rev_status = "🟢 הזדמנות ערך (זול)"
    else:
        rev_status = "⚪ מחיר הוגן"

    if current_rsi > 70:
        rsi_desc = "🔥 קניית יתר"
    elif current_rsi < 30:
        rsi_desc = "🧊 מכירת יתר"
    else:
        rsi_desc = "⚖️ ניטרלי"

    mom_status = "🚀 מגמה עולה" if ema_short > ema_long else "⚠️ מגמה יורדת"

    return {
        "ticker": ticker,
        "price": f"{prices.iloc[-1]:.2f}",
        "z_score": z_score,
        "rev_status": rev_status,
        "rsi": current_rsi,
        "rsi_desc": rsi_desc,
        "momentum": mom_status
    }

def create_visuals(df, tickers):
    """יצירת גרפים מתקדמים עם Subplots"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, 
                                   gridspec_kw={'height_ratios': [3, 1]})
    plt.style.use('dark_background')
    
    for t in tickers:
        if t not in df.columns: continue
        
        # גרף מחיר מנורמל
        normalized = (df[t] / df[t].dropna().iloc[0]) * 100
        ax1.plot(df['ts'], normalized, label=t, linewidth=2, alpha=0.9)
        
        # גרף RSI (מציג רק את המניה האחרונה או הממוצעת לצורך בהירות)
        rsi_vals = calculate_rsi(df[t])
        ax2.plot(df['ts'], rsi_vals, alpha=0.5)

    # עיצוב גרף מחיר
    ax1.set_title("Portfolio Growth Comparison (Base 100)", fontsize=14, color='white')
    ax1.legend(loc='upper left')
    ax1.grid(alpha=0.2)

    # עיצוב גרף RSI
    ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
    ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI Indicators")
    ax2.grid(alpha=0.1)

    plt.tight_layout()
    plt.savefig(PREDICTION_CHART)
    plt.close()

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        print("Missing data files.")
        return

    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    # הכנת נתונים
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.sort_values('ts')

    analysis_results = []
    tickers = list(holdings.keys())

    for t in tickers:
        res = get_analysis(df, t)
        if res:
            analysis_results.append(res)

    # יצירת ויזואליזציה
    create_visuals(df, tickers)

    # בניית דו"ח Markdown
    report = [
        "# 🧠 דוח ניתוח שוק מתקדם",
        f"**תאריך עדכון:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n",
        "## 📊 טבלת סיכום מהירה",
        "| מניה | מחיר אחרון | סטטוס ערך | מדד RSI | מומנטום |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]

    for r in analysis_results:
        report.append(f"| **{r['ticker']}** | {r['price']} | {r['rev_status']} | {r['rsi']:.1f} ({r['rsi_desc']}) | {r['momentum']} |")

    report.extend([
        "\n## 📈 ניתוח טכני ויזואלי",
        f"![Analysis Chart](./{PREDICTION_CHART})",
        "\n---",
        "### 💡 מתודולוגיה והסברים:",
        "- **Z-Score (90d):** בוחן כמה המחיר רחוק מהממוצע של שלושת החודשים האחרונים. מעל 1.8 נחשב חריג סטטיסטית למעלה.",
        "- **Wilder's RSI:** חישוב עוצמה יחסית מוחלק המונע רעשים של תנודות יום בודד.",
        "- **EMA Cross:** השוואה בין ממוצע אקספוננציאלי 20 ל-50 יום לזיהוי שינוי כיוון המגמה."
    ])

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    print(f"הניתוח הושלם בהצלחה! הקובץ {REPORT_FILE} נוצר.")

if __name__ == "__main__":
    main()
