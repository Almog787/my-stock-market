import json
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz
import os
import logging

# --- Paths & Configuration ---
DATA_DIR = "data_hub"
HISTORY_FILE = os.path.join(DATA_DIR, "stock_history.json")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
LOG_FILE = os.path.join(DATA_DIR, "error_log.txt")
CHART_FILE = os.path.join(DATA_DIR, "portfolio_performance.png")
PIE_FILE = os.path.join(DATA_DIR, "asset_allocation.png")
README_FILE = "README.md"
TZ = pytz.timezone('Israel')
DEFAULT_HISTORICAL_ILS = 3.65 # שער היסטורי משוער לצורך הדגמת השפעת מט"ח

os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helpers ---
def get_live_usd_ils():
    """Fetching live USD to ILS conversion rate"""
    try:
        ticker = yf.Ticker("ILS=X")
        data = ticker.history(period="1d")
        return data['Close'].iloc[-1] if not data.empty else DEFAULT_HISTORICAL_ILS
    except Exception as e:
        logging.error(f"Exchange rate error: {e}")
        return DEFAULT_HISTORICAL_ILS

def get_performance_bar(pct):
    """Generates a visual progress bar for the Markdown table"""
    if pd.isna(pct): return "⬜⬜⬜⬜⬜"
    bars = int(min(abs(pct) / 10, 5)) # מקסימום 5 בלוקים, כל בלוק מייצג 10%
    if pct > 0:
        return "🟩" * bars + "⬜" * (5 - bars)
    return "🟥" * bars + "⬜" * (5 - bars)

def generate_visuals(df, holdings_data):
    """Generates advanced charts including Drawdown and Asset Allocation"""
    plt.switch_backend('Agg')
    plt.style.use('dark_background') # סגנון מקצועי וקריא
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['savefig.dpi'] = 300
    
    # --- 1. Performance & Drawdown Graph (Subplots) ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    portfolio_norm = (df['total_usd'] / df['total_usd'].iloc[0]) * 100
    ax1.plot(df['ts'], portfolio_norm, label='My Portfolio', color='#007AFF', linewidth=3)
    
    # Benchmark integration
    try:
        spy = yf.Ticker("^GSPC").history(start=df['ts'].min(), end=df['ts'].max() + timedelta(days=1))
        if not spy.empty:
            spy.index = spy.index.tz_localize(None) 
            spy_norm = (spy['Close'] / spy['Close'].iloc[0]) * 100
            ax1.plot(spy.index, spy_norm, label='S&P 500 (Benchmark)', color='#FF9500', linestyle='--', alpha=0.8, linewidth=2)
    except Exception as e:
        logging.error(f"Benchmark error: {e}")

    ax1.set_title('Performance vs Benchmark (Normalized to 100)', fontsize=14, fontweight='bold')
    ax1.grid(True, linestyle=':', alpha=0.3)
    ax1.legend(frameon=True, shadow=True, loc='upper left')
    
    # Drawdown Calculation
    rolling_max = portfolio_norm.cummax()
    drawdown = ((portfolio_norm - rolling_max) / rolling_max) * 100
    ax2.fill_between(df['ts'], drawdown, 0, color='#FF3B30', alpha=0.3)
    ax2.plot(df['ts'], drawdown, color='#FF3B30', linewidth=1.5)
    ax2.set_title('Portfolio Drawdown (%)', fontsize=10)
    ax2.set_ylabel('% from Peak')
    ax2.grid(True, linestyle=':', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    plt.close()

    # --- 2. Asset Allocation (Donut) ---
    plt.figure(figsize=(10, 10))
    last_row = df.iloc[-1]
    tickers = list(holdings_data.keys())
    values = [last_row[t] * holdings_data[t]['amount'] for t in tickers if t in last_row and pd.notnull(last_row[t])]
    labels = [t for t in tickers if t in last_row and pd.notnull(last_row[t])]
    
    if values:
        colors = ['#FF595E', '#FFCA3A', '#8AC926', '#1982C4', '#6A4C93', '#4267B2']
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors[:len(values)], pctdistance=0.85, explode=[0.02]*len(values))
        centre_circle = plt.Circle((0,0), 0.70, fc='#121212') # מותאם לרקע הכהה
        plt.gcf().gca().add_artist(centre_circle)
        plt.title('Asset Allocation (USD Weight)', fontsize=16, fontweight='bold', color='white')
        plt.savefig(PIE_FILE, transparent=True)
    plt.close()

def main():
    if not os.path.exists(HISTORY_FILE) or not os.path.exists(PORTFOLIO_FILE):
        logging.error("Required data files missing.")
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
    
    # Forward Fill missing prices
    price_cols = [t for t in tickers if t in df.columns]
    df[price_cols] = df[price_cols].ffill()
    
    # Calculate Total Value
    df['total_usd'] = df.apply(lambda r: sum(r[t] * holdings[t]['amount'] for t in tickers if t in r and pd.notnull(r[t])), axis=1)
    
    current_val_usd = df['total_usd'].iloc[-1]
    
    # KPIs Calculation
    total_invested_usd = sum(h['amount'] * h['avg_price'] for h in holdings.values())
    total_pnl_usd = current_val_usd - total_invested_usd
    total_pnl_pct = (total_pnl_usd / total_invested_usd) * 100 if total_invested_usd > 0 else 0

    # Max Drawdown for KPI
    portfolio_norm = (df['total_usd'] / df['total_usd'].iloc[0]) * 100
    rolling_max = portfolio_norm.cummax()
    max_drawdown = (((portfolio_norm - rolling_max) / rolling_max) * 100).min()

    # Daily Change
    one_day_ago = df['ts'].max() - timedelta(days=1)
    past_day_df = df[df['ts'] <= one_day_ago]
    prev_val_usd = past_day_df['total_usd'].iloc[-1] if not past_day_df.empty else df['total_usd'].iloc[0]
    daily_change_pct = ((current_val_usd / prev_val_usd) - 1) * 100

    # Generate the charts
    generate_visuals(df, holdings)

    # --- Build Stock Table with UX Upgrades ---
    stock_rows = []
    for t in tickers:
        if t in df.columns:
            curr_p = df[t].iloc[-1]
            avg_p = holdings[t]['avg_price']
            amt = holdings[t]['amount']
            
            gain_pct = ((curr_p / avg_p) - 1) * 100 if avg_p > 0 else 0
            gain_usd = (curr_p - avg_p) * amt
            gain_ils = gain_usd * usd_to_ils
            
            emoji = "🟢" if gain_pct > 0 else "🔴"
            visual_bar = get_performance_bar(gain_pct)
            
            stock_rows.append(f"| **{t}** | {visual_bar} | {amt} | ${avg_p:,.2f} | ${curr_p:,.2f} | {emoji} **{gain_pct:+.2f}%** | ₪{gain_ils:,.0f} |")

    update_time = datetime.now(TZ).strftime('%d/%m/%Y %H:%M')
    
    # --- Generate Markdown Report ---
    output = [
        f"# 📊 Active Portfolio Dashboard | מעקב תיק השקעות",
        f"> **Last Update:** `{update_time}` | **Live USD/ILS Rate:** `₪{usd_to_ils:.3f}`\n",
        
        f"## 💎 Portfolio Snapshot | תמונת מצב",
        f"| Metric | Value | נתון |",
        f"| :--- | :--- | :--- |",
        f"| **Current Value** | `₪{current_val_usd * usd_to_ils:,.0f}` | **שווי נוכחי** |",
        f"| **Total Invested** | `₪{total_invested_usd * usd_to_ils:,.0f}` | **סך השקעה** |",
        f"| **Total Profit/Loss** | `{total_pnl_pct:+.2f}%` (₪{total_pnl_usd * usd_to_ils:,.0f}) | **רווח/הפסד כולל** |",
        f"| **Daily Change** | `{daily_change_pct:+.2f}%` | **שינוי יומי** |",
        f"| **Max Drawdown** | `{max_drawdown:.2f}%` ⚠️ | **סיכון: צניחה מקסימלית** |",
        
        f"\n## 📜 Position Breakdown | פירוט החזקות",
        f"| Ticker | Momentum | Shares | Avg. Cost | Current Price | P&L % | P&L ILS |",
        f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        "\n".join(stock_rows),
        
        f"\n## 📈 Visual Analytics | ניתוח ויזואלי",
        f"### Performance & Risk (Drawdown)",
        f"![Performance & Drawdown](./{CHART_FILE})",
        f"### Asset Allocation",
        f"![Allocation](./{PIE_FILE})",
        f"\n---",
        f"🛠️ *Automated by Stock-Mentor-Engine v5.0 | Created by Almog787*"
    ]

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    main()
