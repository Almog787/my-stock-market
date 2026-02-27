import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

# --- הגדרות נתיבים ---
DATA_DIR = "data_hub"
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
REPORT_FILE = "ANALYSIS_REPORT.md"
PREDICTION_CHART = os.path.join(DATA_DIR, "predictions.png")

def calculate_mean_reversion(df, ticker):
    """חישוב מרחק מהמכפיל הממוצע (Mean Reversion)"""
    if ticker not in df.columns or 'pe_ratios' not in df:
        return "N/A"
    
    # שליפת היסטוריית המכפילים (אם קיימת בנתונים המורחבים)
    # במידה ואין עדיין מספיק היסטוריה, נשתמש במחיר ביחס לממוצע נע כפרוקסי
    current_price = df[ticker].iloc[-1]
    avg_price = df[ticker].mean()
    std_dev = df[ticker].std()
    
    z_score = (current_price - avg_price) / std_dev if std_dev > 0 else 0
    
    if z_score > 1.5: return "🔴 יקרה היסטורית (Overvalued)"
    if z_score < -1.5: return "🟢 זולה היסטורית (Undervalued)"
    return "⚪ בטווח הממוצע"

def analyze_momentum(df, ticker):
    """ניתוח מומנטום: ממוצע 50 מול 200 (Golden/Death Cross)"""
    prices = df[ticker].dropna()
    if len(prices) < 50:
        return "אין מספיק נתונים"
    
    ma50 = prices.rolling(window=50).mean().iloc[-1]
    ma200 = prices.rolling(window=min(len(prices), 200)).mean().iloc[-1]
    
    if ma50 > ma200:
        return "🚀 מומנטום חיובי (Golden Cross)"
    else:
        return "⚠️ מומנטום שלילי (Death Cross)"

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        print("שגיאה: קבצי הנתונים לא נמצאו.")
        return

    # טעינת נתונים
    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    
    # יצירת DataFrame
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.sort_values('ts')
    
    tickers = list(holdings.keys())
    analysis_rows = []

    # יצירת גרף תחזיות
    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background')

    for t in tickers:
        if t not in df.columns: continue
        
        reversion = calculate_mean_reversion(df, t)
        momentum = analyze_momentum(df, t)
        
        # חישוב RSI פשוט (מדד עוצמה יחסית) ל-14 יום
        delta = df[t].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        
        status = "קנייה" if rsi < 30 else "מכירה" if rsi > 70 else "המתנה"
        
        analysis_rows.append(f"| {t} | {reversion} | {momentum} | {rsi:.1f} | **{status}** |")
        
        # הוספה לגרף
        plt.plot(df['ts'], (df[t]/df[t].iloc[0])*100, label=t, alpha=0.7)

    plt.title("Portfolio Tickers - Relative Growth Comparison")
    plt.legend()
    plt.savefig(PREDICTION_CHART, bbox_inches='tight')
    plt.close()

    # כתיבת הדו"ח
    report = [
        f"# 🧠 דוח ניתוח טכני ותחזיות הסתברותיות",
        f"עדכון אחרון: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n",
        f"## 🔭 ניתוח חזרה לממוצע ומומנטום",
        f"הדוח מנתח האם המניה נמצאת בסטייה קיצונית מהמחיר הממוצע שלה והאם המגמה הנוכחית חיובית.",
        f"\n| מניה | מצב ערך (Mean Reversion) | מומנטום (Moving Averages) | RSI (14) | המלצת מערכת |",
        f"| :--- | :--- | :--- | :--- | :--- |",
        "\n".join(analysis_rows),
        f"\n## 📈 גרף השוואתי (צמיחה יחסית)",
        f"![Predictions](./{PREDICTION_CHART})",
        f"\n---",
        f"### 💡 הסבר על המדדים:",
        f"1. **Mean Reversion**: בודק כמה המניה רחוקה מהממוצע שלה. Z-Score גבוה מ-1.5 מעיד על 'מתיחת יתר'.",
        f"2. **Moving Averages**: חצייה של ממוצע 50 יום מעל 200 יום נחשבת לסימן שורי חזק.",
        f"3. **RSI**: מדד בין 0 ל-100. מתחת ל-30 נחשב 'מכירת יתר' (הזדמנות), מעל 70 'קניית יתר' (סיכון)."
    ]

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    print(f"הדו"ח נוצר בהצלחה: {REPORT_FILE}")

if __name__ == "__main__":
    main()

