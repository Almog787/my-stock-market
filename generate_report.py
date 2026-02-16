import json
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import os
import shutil
import logging

# --- Paths Configuration ---
DATA_DIR = "data_hub"
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
LOG_FILE = os.path.join(DATA_DIR, "error_log.txt")
CHART_FILE = os.path.join(DATA_DIR, "performance.png")
PIE_FILE = os.path.join(DATA_DIR, "allocation.png")
README_FILE = "README.md"
TZ = pytz.timezone('Israel')
ANCHOR_DAY = 10

os.makedirs(ARCHIVE_DIR, exist_ok=True)

def archive_visuals():
    """Moves old charts to archive with timestamp."""
    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M")
    for f in [CHART_FILE, PIE_FILE]:
        if os.path.exists(f):
            name = os.path.basename(f)
            shutil.move(f, os.path.join(ARCHIVE_DIR, f"{ts}_{name}"))

def get_usd_ils():
    try: return yf.Ticker("ILS=X").history(period="1d")['Close'].iloc[-1]
    except: return 3.65

def main():
    if not os.path.exists(HISTORY_FILE): return
    
    archive_visuals()
    
    with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    
    if not history: return
    
    usd_rate = get_usd_ils()
    tickers = list(holdings.keys())
    
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)
    df = df.sort_values('ts')
    
    # Calc values
    df['total_usd'] = df.apply(lambda r: sum(r[t]*holdings[t] for t in tickers if t in r), axis=1)
    current_usd = df['total_usd'].iloc[-1]
    
    # Generate Visuals
    plt.switch_backend('Agg')
    
    # Chart 1: Performance
    plt.figure(figsize=(10, 5))
    plt.plot(df['ts'], (df['total_usd']/df['total_usd'].iloc[0])*100, label='Portfolio', color='blue')
    plt.title('Portfolio Growth (%)')
    plt.grid(True, alpha=0.2)
    plt.savefig(CHART_FILE)
    plt.close()
    
    # Chart 2: Allocation
    plt.figure(figsize=(6, 6))
    last = df.iloc[-1]
    vals = [last[t]*holdings[t] for t in tickers if t in last]
    plt.pie(vals, labels=[t for t in tickers if t in last], autopct='%1.1f%%')
    plt.savefig(PIE_FILE)
    plt.close()

    # Build README (Note: Paths to images now include data_hub/)
    output = [
        f"# 📈 דוח תיק מניות",
        f"**עודכן:** {datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}\n",
        f"## 📊 ביצועים",
        f"![Growth](./{CHART_FILE})",
        f"## 🥧 פילוח",
        f"![Allocation](./{PIE_FILE})\n",
        f"## 💰 סיכום",
        f"- **שווי כולל:** `₪{current_usd * usd_rate:,.0f}`",
        f"- **רווח כולל:** `{((current_usd/df['total_usd'].iloc[0])-1)*100:+.2f}%`\n",
        f"---",
        f"*כל המידע הגולמי והארכיון נמצאים בתיקיית `{DATA_DIR}`*"
    ]
    
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    main()
