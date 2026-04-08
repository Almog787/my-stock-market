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
CHART_FILE = os.path.join(DATA_DIR, "enhanced_analysis.png")

def calculate_rsi(series, period=14):
    """חישוב RSI מקצועי בשיטת Wilder"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))
    # שימוש ב-Exponential Moving Average לדיוק
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def analyze_ticker(df, ticker):
    """ניתוח מתקדם למניה בודדת"""
    prices = df[ticker].dropna()
    if len(prices) < 50: return None

    # 1. Z-Score דינמי (90 יום האחרונים) - מזהה בועות או הזדמנויות מקומיות
    window = 90
    rolling_mean = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    z_score = (prices.iloc[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]

    # 2. RSI עדכני
    rsi_val = calculate_rsi(prices).iloc[-1]

    # 3. מומנטום (EMA Cross)
    ema_20 = prices.ewm(span=20).mean().iloc[-1]
    ema_50 = prices.ewm(span=50).mean().iloc[-1]
    
    # לוגיקה לקביעת סטטוס
    if z_score > 1.8: rev = "🔴 **מתיחת יתר** (מחיר גבוה מדי)"
    elif z_score < -1.8: rev = "🟢 **הזדמנות ערך** (מכירת יתר)"
    else: rev = "⚪ **טווח נורמלי**"

    if rsi_val > 70: rsi_desc = "🔥 קניית יתר"
    elif rsi_val < 30: rsi_desc = "🧊 מכירת יתר"
    else: rsi_desc = "⚖️ ניטרלי"

    mom = "🚀 חיובי" if ema_20 > ema_50 else "⚠️ שלילי"

    return {
        "ticker": ticker,
        "z_score": z_score,
        "rev": rev,
        "rsi": rsi_val,
        "rsi_desc": rsi_desc,
        "mom": mom,
        "last_price": prices.iloc[-1]
    }

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        print("Error: Missing data files.")
        return

    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.sort_values('ts')

    results = []
    tickers = list(holdings.keys())

    # יצירת גרף משופר (Subplots)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    plt.style.use('dark_background')

    for t in tickers:
        if t not in df.columns: continue
        
        analysis = analyze_ticker(df, t)
        if analysis: results.append(analysis)

        # גרף 1: מחיר מנורמל
        norm_price = (df[t] / df[t].dropna().iloc[0]) * 100
        ax1.plot(df['ts'], norm_price, label=f"{t} ({analysis['mom']})", linewidth=2)
        
    ax1.set_title("Portfolio Relative Performance (Base 100)", fontsize=14)
    ax1.legend(loc='upper left', ncol=2)
    ax1.grid(alpha=0.2)

    # גרף 2: אינדיקטור RSI כללי (דוגמה למניה הראשונה או ממוצע)
    ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
    ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI Level")
    
    plt.tight_layout()
    plt.savefig(CHART_FILE)

    # בניית הדו"ח ב-Markdown
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    report = [
        f"# 🧠 דוח ניתוח שוק חכם - {now_str}",
        "\n## 📊 מבט על מהיר",
        "| מניה | סטטוס מחיר | RSI | מומנטום |",
        "| :--- | :--- | :--- | :--- |"
    ]

    for r in results:
        report.append(f"| **{r['ticker']}** | {r['rev']} | {r['rsi']:.1f} | {r['mom']} |")

    report.append("\n## 🔍 פירוט לפי נכס")
    for r in results:
        report.append(f"### 📈 {r['ticker']}\n- **מצב טכני:** {r['rev']}\n- **מדד RSI:** {r['rsi']:.1f} ({r['rsi_desc']})\n- **מומנטום:** {r['mom']}")

    report.append("\n## 📈 ויזואליזציה של ביצועים")
    report.append(f"![Analysis Chart](./{CHART_FILE})")
    
    report.append("\n---\n*הערה: הניתוח מתבסס על Z-Score מתגלגל של 90 יום ו-EMA Cross 20/50.*")

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    main()
