import yfinance as yf
import json
import os
from datetime import datetime
import pytz
import pandas as pd
import logging

# --- Configuration & Paths ---
BASE_DATA_DIR = "data_hub"
PORTFOLIO_FILE = os.path.join(BASE_DATA_DIR, "portfolio.json")
HISTORY_FILE = os.path.join(BASE_DATA_DIR, "stock_history.json")
LOG_FILE = os.path.join(BASE_DATA_DIR, "error_log.txt")
TZ = pytz.timezone('Israel')
MAX_HISTORY_ROWS = 10000

# Ensure directory exists
os.makedirs(BASE_DATA_DIR, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_base_files():
    """Initializes JSON files if missing."""
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f: json.dump([], f)
    if not os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f: json.dump({"SPY": 1}, f)

def main():
    ensure_base_files()
    
    # Load portfolio
    try:
        with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
    except: holdings = {"SPY": 1}

    tickers = list(holdings.keys())
    if "SPY" not in tickers: tickers.append("SPY")

    # Load history
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f: history = json.load(f)
    except: history = []

    # 1. Backfill if empty
    if not history:
        print("Backfilling initial data...")
        data = yf.download(tickers, period="1y", interval="1d", progress=False)['Close']
        if not data.empty:
            data = data.ffill().bfill()
            for date, row in data.iterrows():
                history.append({
                    "timestamp": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "prices": {t: round(float(v), 2) for t, v in row.to_dict().items() if pd.notna(v)}
                })

    # 2. Current sampling
    try:
        current = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
        if not current.empty:
            last_row = current.iloc[-1]
            ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
            # Deduplicate by minute
            if not history or history[-1]['timestamp'][:16] != ts[:16]:
                history.append({
                    "timestamp": ts,
                    "prices": {t: round(float(v), 2) for t, v in last_row.to_dict().items() if pd.notna(v)}
                })
    except Exception as e:
        logging.error(f"Sampling error: {e}")

    # 3. Save
    history = sorted(history, key=lambda x: x['timestamp'])[-MAX_HISTORY_ROWS:]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)

if __name__ == "__main__":
    main()
