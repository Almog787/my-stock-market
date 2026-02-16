import json
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import os
import shutil
import logging

# --- Configuration & Constants ---
HISTORY_FILE = "stock_history.json"
PORTFOLIO_FILE = "portfolio.json"
README_FILE = "README.md"
LOG_FILE = "error_log.txt"
CHART_FILE = "portfolio_performance.png"
PIE_FILE = "asset_allocation.png"
ARCHIVE_DIR = "archive/charts" # New archive directory
TZ = pytz.timezone('Israel')
ANCHOR_DAY = 10

# Initialize logging
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, 'w').close()

logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def archive_old_visuals():
    """Moves existing charts to the archive folder with a timestamp."""
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    timestamp = datetime.now(TZ).strftime("%Y%m%d_%H%M")
    
    for filename in [CHART_FILE, PIE_FILE]:
        if os.path.exists(filename):
            name, ext = os.path.splitext(filename)
            new_name = f"{timestamp}_{name}{ext}"
            try:
                shutil.move(filename, os.path.join(ARCHIVE_DIR, new_name))
            except Exception as e:
                logging.error(f"Failed to archive {filename}: {e}")

def get_live_usd_ils():
    """Fetches the current USD/ILS exchange rate."""
    try:
        ticker = yf.Ticker("ILS=X")
        data = ticker.history(period="1d")
        return data['Close'].iloc[-1] if not data.empty else 3.65
    except Exception as e:
        logging.error(f"Exchange rate error: {e}")
        return 3.65

def calculate_portfolio_value(row, holdings, tickers):
    """Calculates total portfolio value in USD for a given row of prices."""
    return sum(row[t] * holdings[t] for t in tickers if t in row)

def generate_visuals(df, holdings):
    """Generates performance and allocation charts using matplotlib."""
    plt.switch_backend('Agg') # Non-GUI backend for CI/CD
    
    # 1. Performance Chart
    plt.figure(figsize=(10, 5))
    portfolio_norm = (df['total_usd'] / df['total_usd'].iloc[0]) * 100
    plt.plot(df['ts'], portfolio_norm, label='My Portfolio', color='#1f77b4', linewidth=2)
    
    try:
        spy = yf.Ticker("^GSPC").history(start=df['ts'].min(), end=df['ts'].max() + timedelta(days=1))
        if not spy.empty:
            spy_norm = (spy['Close'] / spy['Close'].iloc[0]) * 100
            plt.plot(spy.index, spy_norm, label='S&P 500 (Benchmark)', color='#ff7f0e', linestyle='--')
    except:
        pass

    plt.title('Portfolio vs Benchmark (Normalized to 100)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(CHART_FILE)
    plt.close()

    # 2. Allocation Pie Chart
    last_prices = df.iloc[-1]
    values = [last_prices[t] * holdings[t] for t in holdings.keys() if t in last_prices]
    labels = [t for t in holdings.keys() if t in last_prices]
    
    plt.figure(figsize=(7, 7))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
    plt.title('Asset Allocation')
    plt.savefig(PIE_FILE)
    plt.close()

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        return

    # Archive old charts before generating new ones
    archive_old_visuals()

    try:
        with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
        with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    except:
        return

    if not history: return

    usd_to_ils = get_live_usd_ils()
    tickers = list(holdings.keys())
    
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)
    df = df.sort_values('ts')
    df['total_usd'] = df.apply(lambda r: calculate_portfolio_value(r, holdings, tickers), axis=1)
    
    current_val_usd = df['total_usd'].iloc[-1]
    initial_val_usd = df['total_usd'].iloc[0]
    total_ret = ((current_val_usd / initial_val_usd) - 1) * 100
    
    generate_visuals(df, holdings)

    # Building README
    output = [
        f"# 📊 Portfolio Dashboard",
        f"**עודכן ב:** {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')} | **שער דולר:** ₪{usd_to_ils:.3f}\n",
        f"## 📈 גרף ביצועים נוכחי",
        f"![Performance](./{CHART_FILE})\n",
        f"## 🥧 התפלגות נכסים",
        f"![Allocation](./{PIE_FILE})\n",
        f"## 📑 ארכיון דוחות",
        f"ניתן למצוא את כל הגרפים ההיסטוריים בתיקיית `archive/charts/`.\n",
        f"## 📊 פירוט אחזקות",
        f"| מניה | כמות | שווי (₪) | משקל |",
        f"| :--- | :--- | :--- | :--- |"
    ]

    for t in tickers:
        if t in df.columns:
            val_ils = df.iloc[-1][t] * holdings[t] * usd_to_ils
            weight = (df.iloc[-1][t] * holdings[t] / current_val_usd) * 100
            output.append(f"| {t} | {holdings[t]} | ₪{val_ils:,.0f} | {weight:.1f}% |")

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    main()
