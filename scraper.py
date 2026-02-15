import requests
from bs4 import BeautifulSoup
import json
import datetime

# ה-URL של דף המוצר
URL = "https://www.ace.co.il/5760921"

# הגדרות כדי לדמות דפדפן
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    # שליחת בקשה לדף
    page = requests.get(URL, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")

    # מציאת שם המוצר
    product_title_element = soup.find("span", class_="base")
    product_title = product_title_element.text.strip() if product_title_element else "שם מוצר לא נמצא"

    # מציאת מחיר המוצר
    price_element = soup.find("span", class_="special-price").find("span", class_="price")
    price_text = price_element.text.strip().replace('₪', '').replace(',', '')
    current_price = float(price_text)

    # טעינת נתונים קיימים
    try:
        with open('prices.json', 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"history": [], "count": 0}

    # קבלת המחיר הקודם, אם קיים
    last_price = data["history"][-1]["price"] if data["history"] else None

    # הוספת הרשומה החדשה
    data["count"] += 1
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["history"].append({"timestamp": timestamp, "price": current_price})

    # שמירת הנתונים המעודכנים
    with open('prices.json', 'w') as f:
        json.dump(data, f, indent=4)

    # עדכון קובץ ה-README
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(f"# מעקב אחר מחיר: {product_title}\n\n")
        f.write(f"**המחיר הנוכחי: {current_price} ₪**\n\n")
        f.write(f"נבדק לאחרונה: {timestamp}\n")
        f.write(f"סך הבדיקות: {data['count']}\n\n")

        if last_price and current_price < last_price:
            f.write(f"## 🎉 **המחיר ירד!** 🎉\n")
            f.write(f"המחיר הקודם היה {last_price} ₪.\n\n")

        # הוספת תצוגה של היסטוריית המחירים
        f.write("## היסטוריית מחירים\n")
        f.write("| תאריך | מחיר (₪) |\n")
        f.write("|---|---|\n")
        # הצגת 10 הרשומות האחרונות
        for entry in reversed(data["history"][-10:]):
            f.write(f"| {entry['timestamp']} | {entry['price']} |\n")

    print(f"הבדיקה הושלמה. המחיר הנוכחי: {current_price}")

except Exception as e:
    print(f"אירעה שגיאה: {e}")
