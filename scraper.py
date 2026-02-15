import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import pytz
import pandas as pd
import re

# הגדרות קבצים
URLS_FILE = "urls.txt"
DATA_FILE = "data.json"
README_FILE = "README.md"
TZ_ISRAEL = pytz.timezone('Asia/Jerusalem')

def get_product_data(product_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        response = requests.get(product_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price = None
        title = None

        # --- שלב 1: שליפת כותרת ---
        # ננסה קודם מטא-דאטה (הכי אמין)
        title_meta = soup.find("meta", property="og:title") or soup.find("meta", dict(name="title"))
        if title_meta:
            title = title_meta["content"]
        else:
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "מוצר ללא שם"

        # --- שלב 2: שליפת מחיר (שיטה גנרית חכמה) ---
        
        # א. חיפוש במטא-דאטה של מחיר (נפוץ מאוד באתרים מקצועיים)
        price_meta = (
            soup.find("meta", property="product:price:amount") or 
            soup.find("meta", property="og:price:amount") or
            soup.find("meta", dict(name="twitter:data1")) # לעיתים המחיר כאן
        )
        if price_meta:
            price = price_meta["content"]

        # ב. אם לא נמצא, חיפוש ב-JSON-LD (פורמט נתונים של גוגל שנמצא ברוב האתרים)
        if not price:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    json_data = json.loads(script.string)
                    # מחפש את שדה המחיר בתוך מבנה גמיש
                    if isinstance(json_data, dict):
                        offers = json_data.get('offers')
                        if isinstance(offers, dict):
                            price = offers.get('price')
                        elif isinstance(offers, list):
                            price = offers[0].get('price')
                    if price: break
                except:
                    continue

        # ג. גיבוי אחרון: חיפוש תגיות HTML נפוצות למחיר
        if not price:
            # מחפש אלמנטים שמכילים class עם המילה price
            price_elements = soup.find_all(class_=re.compile(r'price|final-price|current-price', re.I))
            for elem in price_elements:
                text = elem.get_text(strip=True)
                # מחלץ רק מספרים ונקודה עשרונית
                numbers = re.findall(r'\d+\.?\d*', text.replace(',', ''))
                if numbers:
                    price = numbers[0]
                    break

        # ניקוי סופי למחיר
        if price:
            # הסרת תווים שאינם מספרים (כמו ₪ או פסיקים)
            price = str(price).replace(',', '').replace('₪', '').strip()
            price = float(re.findall(r'\d+\.?\d*', price)[0])

        return {
            "timestamp": datetime.now(TZ_ISRAEL).strftime("%Y-%m-%d %H:%M:%S"),
            "price": price if price else 0,
            "title": title.strip() if title else "מוצר לא מזוהה",
            "url": product_url
        }
    except Exception as e:
        print(f"Error scraping {product_url}: {e}")
        return None

def update_database(new_entries):
    data = []
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    
    data.extend(new_entries)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return data

def generate_readme(all_data):
    if not all_data:
        return

    df = pd.DataFrame(all_data)
    readme_content = "# 🤖 בוט מעקב מחירים אוטומטי\n\n"
    readme_content += f"**עדכון אחרון:** {datetime.now(TZ_ISRAEL).strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for url in df['url'].unique():
        p_df = df[df['url'] == url]
        latest = p_df.iloc[-1]
        
        # חישוב שינוי
        diff_text = "➖ יציב"
        if len(p_df) > 1:
            prev_price = p_df.iloc[-2]['price']
            if latest['price'] > 0 and prev_price > 0:
                if latest['price'] < prev_price:
                    diff_text = f"🔻 ירידה של ₪{round(prev_price - latest['price'], 2)}"
                elif latest['price'] > prev_price:
                    diff_text = f"🔺 עלייה של ₪{round(latest['price'] - prev_price(), 2)}"

        status_icon = "✅" if latest['price'] > 0 else "❌ תקלה בסריקה"
        
        readme_content += f"### {status_icon} [{latest['title']}]({url})\n"
        readme_content += f"- **מחיר נוכחי:** `₪{latest['price']}`\n"
        readme_content += f"- **מצב:** {diff_text}\n"
        readme_content += f"- **הכי זול שנצפה:** ₪{p_df[p_df['price'] > 0]['price'].min() if not p_df[p_df['price'] > 0].empty else 0}\n\n"
        
        readme_content += "| תאריך | מחיר |\n|---|---|\n"
        for _, row in p_df.tail(5).iloc[::-1].iterrows():
            readme_content += f"| {row['timestamp']} | ₪{row['price']} |\n"
        readme_content += "\n---\n"

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)

if __name__ == "__main__":
    if not os.path.exists(URLS_FILE):
        with open(URLS_FILE, 'w') as f: f.write("") # יצירת קובץ ריק אם לא קיים

    with open(URLS_FILE, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    results = []
    for url in urls:
        print(f"🔍 בודק: {url}")
        res = get_product_data(url)
        if res:
            results.append(res)
    
    if results:
        full_data = update_database(results)
        generate_readme(full_data)
        print("✅ הסריקה הושלמה.")
