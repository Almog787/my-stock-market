import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

DATA_DIR = "data_hub"
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
REPORT_FILE = "ANALYSIS_REPORT.md"
PREDICTION_CHART = os.path.join(DATA_DIR, "predictions.png")

def calculate_mean_reversion(df, ticker):
    current_price = df[ticker].iloc[-1]
    avg_price = df[ticker].mean()
    std_dev = df[ticker].std()
    z_score = (current_price - avg_price) / std_dev if std_dev > 0 else 0
    if z_score > 1.5: return "🔴 יקרה היסטורית (Overvalued)"
    if z_score < -1.5: return "🟢 זולה היסטורית (Undervalued)"
    return "⚪ בטווח הממוצע"

def analyze_momentum(df, ticker):
    prices = df[ticker].dropna()
    if len(prices) < 50: return "אין מספיק נתונים"
    ma50 = prices.rolling(window=50).mean().iloc[-1]
    ma200 = prices.rolling(window=min(len(prices), 200)).mean().iloc[-1]
    return "🚀 מומנטום חיובי (Golden Cross)" if ma50 > ma200 else "⚠️ מומנטום שלילי (Death Cross)"

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        print("Data missing."); return
    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts'])
    df = df.sort_values('ts')
    tickers = list(holdings.keys())
    analysis_rows = []
    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background')
    for t in tickers:
        if t not in df.columns: continue
        reversion = calculate_mean_reversion(df, t)
        momentum = analyze_momentum(df, t)
        delta = df[t].diff(); gain = delta.where(delta > 0, 0).rolling(14).mean(); loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss; rsi = 100 - (100 / (1 + rs.iloc[-1]))
        status = "קנייה" if rsi < 30 else "מכירה" if rsi > 70 else "המתנה"
        analysis_rows.append(f"| {t} | {reversion} | {momentum} | {rsi:.1f} | **{status}** |")
        plt.plot(df['ts'], (df[t]/df[t].iloc[0])*100, label=t, alpha=0.7)
    plt.legend(); plt.savefig(PREDICTION_CHART, bbox_inches='tight'); plt.close()
    report = ["# 🧠 דוח ניתוח טכני ותחזיות הסתברותיות", f"עדכון: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n", "| מניה | מצב ערך | מומנטום | RSI | המלצה |", "|:---|:---|:---|:---|:---|", "\n".join(analysis_rows), f"\n![Predictions](./{PREDICTION_CHART})"]
    with open(REPORT_FILE, 'w', encoding='utf-8') as f: f.write("\n".join(report))
if __name__ == "__main__": main()
