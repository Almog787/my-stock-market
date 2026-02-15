import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import pytz
import pandas as pd

# הגדרות רשימת מוצרים
PRODUCTS = [
    {"name": "ACE Product", "url": "https://www.ace.co.il/5760921"},
    {"name": "S25 Ultra GoMobile", "url": "https://www.gomobile.co.il/product/samsung-galaxy-s25-ultra-sm-s938b-ds-256gb-12gb-ram/?variation=124394"}
]

DATA_FILE = "data.json"
README_FILE = "README.md"
TZ_ISRAEL = pytz.timezone('Asia/Jerusalem')

def get_product_data(product_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price = 0
        title = "לא נמצא שם מוצר"

        # לוגיקה ל-ACE
        if "ace.co.il" in product_url:
            title_tag = soup.find('h1', class_='page-title')
            title = title_tag.get_text(strip=True) if title_tag else title
            price_meta = soup.find('meta', property='product:price:amount')
            if price_meta:
                price = price_meta['content']
            else:
                price_span = soup.find('span', {'data-price-type': 'finalPrice'})
                if price_span:
                    price = price_span.get_text(strip=True).replace('₪', '').replace(',', '')

        # לוגיקה ל-GoMobile
        elif "gomobile.co.il" in product_url:
            title_tag = soup.find('h1', class_='product_title')
            title = title_tag.get_text(strip=True) if title_tag else title
            # חיפוש מחיר ב-GoMobile (בד"כ נמצא בתוך תגית bdi או span עם class של price)
            price_tag = soup.find('ins') or soup.find('span', class_='woocommerce-Price-amount')
            if price_tag:
                price = price_tag.get_text(strip=True).replace('₪', '').replace(',', '')
        
        return {
            "timestamp": datetime.now(TZ_ISRAEL).strftime("%Y-%m-%d %H:%M:%S"),
            "price": float(price),
            "title": title,
            "url": product_url
        }
    except Exception as e:
        print(f"Error scraping {product_url}: {e}")
        return None

def update_database(new_entries):
    if not os.path.exists(DATA_FILE):
        data = []
    else:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    
    # הוספת כל התוצאות החדשות
    data.extend(new_entries)
    
    # שמירה (שומרים את הכל)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return data

def generate_readme(all_data):
    if not all_data:
        return

    df = pd.DataFrame(all_data)
    df['price'] = pd.to_numeric(df['price'])
    
    readme_content = "# 🤖 בוט מעקב מחירים אוטומטי\n\n"
    readme_content += f"עודכן לאחרונה: {datetime.now(TZ_ISRAEL).strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # יצירת מקטע לכל מוצר בנפרד
    for url in df['url'].unique():
        product_df = df[df['url'] == url]
        latest = product_df.iloc[-1]
        
        min_price = product_df['price'].min()
        max_price = product_df['price'].max()
        
        readme_content += f"## [{latest['title']}]({url})\n"
        readme_content += f"- **מחיר נוכחי:** ₪{latest['price']}\n"
        readme_content += f"- **מחיר הכי נמוך שנצפה:** ₪{min_price}\n"
        readme_content += f"- **מחיר הכי גבוה שנצפה:** ₪{max_price}\n\n"
        
        # טבלת היסטוריה קצרה לכל מוצר
        readme_content += "| תאריך | מחיר | שינוי |\n|---|---|---|\n"
        
        history = product_df.tail(10).to_dict('records')
        prev_price = None
        for entry in reversed(history):
            change = "➖"
            # כאן החישוב פשוט - השוואה לדגימה הקודמת בהיסטוריה
            readme_content += f"| {entry['timestamp']} | ₪{entry['price']} | {change} |\n"
        
        readme_content += "\n---\n"

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)

if __name__ == "__main__":
    new_results = []
    for product in PRODUCTS:
        print(f"Checking: {product['name']}...")
        result = get_product_data(product['url'])
        if result:
            new_results.append(result)
    
    if new_results:
        updated_full_data = update_database(new_results)
        generate_readme(updated_full_data)
        print("Done!")
    else:
        print("No data was fetched.")
