import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

# --- הגדרות וקבועים ---
DATA_DIR = "data_hub"
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
REPORT_FILE = "ANALYSIS_REPORT.md"
CHART_FILE = os.path.join(DATA_DIR, "portfolio_analysis.png")

# סטיל גרפי מקצועי
plt.style.use('dark_background')

def calculate_rsi(series, period=14):
    """חישוב RSI בשיטת Wilder (סטנדרט תעשייתי)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_market_signals(df, ticker):
    """ניתוח אותות וסיכונים למניה בודדת"""
    prices = df[ticker].dropna()
    if len(prices) < 20:
        return "⏳ נתונים חסרים", 50, 0
    
    # 1. Mean Reversion (Z-Score)
    avg = prices.mean()
    std = prices.std()
    z_score = (prices.iloc[-1] - avg) / std if std > 0 else 0
    
    # 2. RSI
    rsi_val = calculate_rsi(prices).iloc[-1]
    
    # 3. Volatility (Annualized)
    volatility = prices.pct_change().std() * np.sqrt(252) * 100
    
    status = "⚖️ ניטרלי"
    if z_score > 1.5 or rsi_val > 70: status = "🔴 מתיחת יתר (Overbought)"
    elif z_score < -1.5 or rsi_val < 30: status = "🟢 הזדמנות ערך (Oversold)"
    
    return status, rsi_val, volatility

def generate_visuals(df, tickers):
    """יצירת גרף מקצועי עם Subplots"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, 
                                   gridspec_kw={'height_ratios': [3, 1]})
    
    for t in tickers:
        # גרף מחיר מנורמל (Base 100)
        normalized_price = (df[t] / df[t].iloc[0]) * 100
        ax1.plot(df['ts'], normalized_price, label=f"{t} (Normalized)", linewidth=2)
        
        # חישוב RSI לצורך הגרף התחתון (נציג את הממוצע או את הראשונה)
        if t == tickers[0]:
            rsi_series = calculate_rsi(df[t])
            ax2.plot(df['ts'], rsi_series, color='orange', alpha=0.8, label=f'RSI {t}')
            ax2.axhline(70, color='red', linestyle='--', alpha=0.3)
            ax2.axhline(30, color='green', linestyle='--', alpha=0.3)
            ax2.fill_between(df['ts'], 70, 100, color='red', alpha=0.1)
            ax2.fill_between(df['ts'], 0, 30, color='green', alpha=0.1)

    ax1.set_title("Portfolio Growth & Momentum Analysis", fontsize=16)
    ax1.set_ylabel("Price Index (Start = 100)")
    ax1.legend(loc='upper left')
    ax1.grid(alpha=0.2)
    
    ax2.set_ylabel("RSI")
    ax2.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

def main():
    if not os.path.exists(HISTORY_FILE):
        print("❌ Error: History file not found.")
        return

    # טעינת נתונים
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.sort_values('ts')
    
    tickers = [c for c in df.columns if c != 'ts']
    
    report_sections = []
    
    # ניתוח כל מניה
    for t in tickers:
        status, rsi, vol = get_market_signals(df, t)
        report_sections.append(
            f"### 📈 {t}\n"
            f"- **סטטוס שוק:** {status}\n"
            f"- **מדד RSI:** `{rsi:.1f}`\n"
            f"- **תנודתיות שנתית:** `{vol:.1f}%`\n"
        )
    
    generate_visuals(df, tickers)
    
    # בניית הדוח הסופי
    full_report = [
        f"# 🧠 דוח ניתוח ארכיטקטוני - {datetime.now().strftime('%d/%m/%Y')}",
        "## 📊 מבט על הפורטפוליו",
        "![Market Analysis](./data_hub/portfolio_analysis.png)",
        "## 🔍 פירוט אחזקות",
        "\n".join(report_sections),
        "---",
        "*הדוח נוצר אוטומטית על ידי Stock-Mentor-Engine v5.0*"
    ]
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(full_report))
    
    print(f"✅ Report generated successfully: {REPORT_FILE}")

if __name__ == "__main__":
    main()
