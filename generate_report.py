import json
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import os
import logging

# --- Paths Configuration ---
DATA_DIR = "data_hub"
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
LOG_FILE = os.path.join(DATA_DIR, "error_log.txt")
CHART_FILE = os.path.join(DATA_DIR, "portfolio_performance.png")
PIE_FILE = os.path.join(DATA_DIR, "asset_allocation.png")
README_FILE = "README.md"
TZ = pytz.timezone('Israel')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# Logging setup
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_live_usd_ils():
    """Fetch live USD/ILS exchange rate with fail-safe."""
    try:
        ticker = yf.Ticker("ILS=X")
        data = ticker.history(period="1d")
        return data['Close'].iloc[-1] if not data.empty else 3.65
    except Exception as e:
        logging.error(f"Exchange rate error: {e}")
        return 3.65

def generate_visuals(df, holdings):
    """Generate high-resolution performance and allocation charts."""
    # הגדרות איכות גבוהה (DPI 300)
    plt.switch_backend('Agg')
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    
    # 1. Performance Graph (High Res)
    plt.figure(figsize=(12, 6))
    portfolio_norm = (df['total_usd'] / df['total_usd'].iloc[0]) * 100
    
    # קו תיק עבה וברור יותר
    plt.plot(df['ts'], portfolio_norm, label='My Portfolio', color='#007AFF', linewidth=3)
    
    try:
        spy = yf.Ticker("^GSPC").history(start=df['ts'].min(), end=df['ts'].max() + timedelta(days=1))
        if not spy.empty:
            spy.index = spy.index.tz_localize(None) 
            spy_norm = (spy['Close'] / spy['Close'].iloc[0]) * 100
            plt.plot(spy.index, spy_norm, label='S&P 500 (Benchmark)', color='#FF9500', linestyle='--', alpha=0.8, linewidth=2)
    except Exception as e:
        logging.error(f"Benchmark error: {e}")

    plt.title('Performance vs Benchmark (Normalized to 100)', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(frameon=True, shadow=True)
    plt.xlabel('Date')
    plt.ylabel('Relative Change (%)')
    
    # שמירה ברזולוציה גבוהה עם חיתוך שוליים אוטומטי
    plt.savefig(CHART_FILE, dpi=300, bbox_inches='tight')
    plt.close()

    # 2. Asset Allocation (Modern Donut Style)
    plt.figure(figsize=(10, 10))
    last_row = df.iloc[-1]
    tickers = list(holdings.keys())
    values = [last_row[t] * holdings[t] for t in tickers if t in last_row and pd.notnull(last_row[t])]
    labels = [t for t in tickers if t in last_row and pd.notnull(last_row[t])]
    
    if values:
        # פלטת צבעים מודרנית
        colors = ['#FF595E', '#FFCA3A', '#8AC926', '#1982C4', '#6A4C93', '#4267B2']
        
        wedges, texts, autotexts = plt.pie(
            values, labels=labels, autopct='%1.1f%%', 
            startangle=140, colors=colors[:len(values)],
            pctdistance=0.85, explode=[0.02]*len(values)
        )
        
        # עיצוב טקסט בתוך הגרף
        plt.setp(autotexts, size=10, weight="bold", color="white")
        plt.setp(texts, size=12)
        
        # יצירת מראה ה"דונאט"
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)
        
        plt.title('Asset Allocation (USD Weight)', fontsize=16, fontweight='bold')
        plt.savefig(PIE_FILE, dpi=300, bbox_inches='tight')
    plt.close()

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        print("Missing required data files.")
        return

    try:
        with open(PORTFOLIO_FILE, 'r') as f: holdings = json.load(f)
        with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    except Exception as e:
        logging.error(f"JSON Load error: {e}")
        return

    if not history: return

    usd_to_ils = get_live_usd_ils()
    tickers = list(holdings.keys())
    
    df = pd.DataFrame([{"ts": e['timestamp'], **e['prices']} for e in history])
    df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)
    df = df.sort_values('ts')
    
    price_cols = [t for t in tickers if t in df.columns]
    df[price_cols] = df[price_cols].ffill()
    
    df['total_usd'] = df.apply(lambda r: sum(r[t] * holdings[t] for t in tickers if t in r and pd.notnull(r[t])), axis=1)
    
    current_val_usd = df['total_usd'].iloc[-1]
    initial_val_usd = df['total_usd'].iloc[0]
    
    # Cumulative Return
    total_ret_pct = ((current_val_usd / initial_val_usd) - 1) * 100
    total_ret_ils = (current_val_usd - initial_val_usd) * usd_to_ils

    # Change Calculations
    one_day_ago = df['ts'].max() - timedelta(days=1)
    past_day_df = df[df['ts'] <= one_day_ago]
    prev_val_usd = past_day_df['total_usd'].iloc[-1] if not past_day_df.empty else df['total_usd'].iloc[0]
    daily_change_pct = ((current_val_usd / prev_val_usd) - 1) * 100
    daily_change_ils = (current_val_usd - prev_val_usd) * usd_to_ils

    # Risk Metrics
    rolling_max = df['total_usd'].cummax()
    max_drawdown = ((df['total_usd'] / rolling_max) - 1).min() * 100

    # Performance Mapping
    perf_map = {}
    for t in tickers:
        if t in df.columns:
            valid_prices = df[t].dropna() 
            if len(valid_prices) >= 2:
                perf_map[t] = ((valid_prices.iloc[-1] / valid_prices.iloc[0]) - 1) * 100
    best_stock = max(perf_map, key=perf_map.get) if perf_map else "N/A"

    # יצירת הגרפים המשופרים
    generate_visuals(df, holdings)

    # --- Build README ---
    update_time = datetime.now(TZ).strftime('%d/%m/%Y %H:%M')
    
    output = [
        f"![Python](https://img.shields.io/badge/python-3.8%2B-blue?logo=python)",
        f"![License](https://img.shields.io/badge/license-MIT-green)",
        f"![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-orange)\n",
        f"# 📊 Portfolio Dashboard | מעקב תיק השקעות",
        f"**Last Update / עדכון אחרון:** {update_time} | **USD/ILS:** ₪{usd_to_ils:.3f}\n",
        
        f"## 💰 Performance Summary | סיכום ביצועים",
        f"| Metric | Value | נתון |",
        f"| :--- | :--- | :--- |",
        f"| **Portfolio Value** | `₪{current_val_usd * usd_to_ils:,.0f}` | **שווי תיק** |",
        f"| **Daily Change** | `{daily_change_pct:+.2f}%` (₪{daily_change_ils:,.0f}) | **שינוי יומי** |",
        f"| **Total Return** | `{total_ret_pct:+.2f}%` (₪{total_ret_ils:,.0f}) | **תשואה מצטברת** |",
        f"| **Max Drawdown** | `{max_drawdown:.2f}%` | **ירידה מקסימלית** |",
        f"| **Best Stock 🚀** | {best_stock} | **המניה המנצחת** |",
        
        f"\n## 📈 Charts | גרפים",
        f"![Performance](./{CHART_FILE})",
        f"![Allocation](./{PIE_FILE})\n",
        
        f"## ⚙️ How to Update? | הוראות עדכון",
        f"### 🇺🇸 English",
        f"1. Open `data_hub/portfolio.json`.\n2. Click the **Edit** icon.\n3. Modify symbols/amounts and **Commit changes**.\n",
        f"### 🇮🇱 עברית",
        f"1. פתחו את הקובץ `data_hub/portfolio.json`.\n2. לחצו על אייקון ה**עריכה**.\n3. עדכנו מניות/כמויות ולחצו על **Commit changes**.\n",
        
        f"---",
        f"📂 *Created by [Almog787](https://github.com/Almog787)* | [Live Site](https://almog787.github.io/Sapa/)"
    ]

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    main()
