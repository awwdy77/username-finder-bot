import requests
import random
import os
import time

# قراءة التوكن والآي دي من إعدادات السيرفر (Render Environment Variables)
TOK = os.environ.get("BOT_TOKEN")
ID = os.environ.get("CHAT_ID")

if not TOK or not ID:
    print("Error: BOT_TOKEN or CHAT_ID environment variables are missing.")
    exit(1)

# الحروف والأرقام المسموحة (بدون شرطات)
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"

print("—" * 60)
print("Started searching for 5 & 6 character usernames (No Underscores)...")

def check_username():
    # اختيار عشوائي: إما 5 حروف أو 6 حروف
    length = random.choice([5, 6])
    
    # توليد اليوزر (حروف وأرقام فقط)
    username = "".join(random.choices(CHARS, k=length))
    
    try:
        url = f"https://fragment.com/username/{username}"
        # إرسال طلب للموقع
        response = requests.get(url, timeout=10)
        
        # إذا كان طول الصفحة أقل من 20000، يعني اليوزر متاح
        if len(response.text) < 20000:
            print(f"[•] Good: {username}")
            
            # رسالة تيليجرام
            msg = f"""< TELEGRAM USERNAME > Good
[•] < @{username} > 🔸
_______
BY : [ @KoXVX ]\nCHANNEL: [ @l27_0 ]"""
            
            # إرسال الإشعار عبر البوت
            requests.get(f'https://api.telegram.org/bot{TOK}/sendMessage?chat_id={ID}&text={msg}')
        else:
            print(f"[✗] Bad: {username}")
            
    except Exception as e:
        print(f"Request error: {e}")

while True:
    check_username()
    # الانتظار 3 ثواني بين كل محاولة لتجنب الحظر
    time.sleep(3)
