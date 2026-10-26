import requests
import random
import os
import time
import threading
from flask import Flask

# --- قراءة المتغيرات من إعدادات Render ---
TOK = os.environ.get("BOT_TOKEN")
ID = os.environ.get("CHAT_ID")

if not TOK or not ID:
    print("Error: BOT_TOKEN or CHAT_ID environment variables are missing.")
    exit(1)

# --- إعداد خادم الويب (لإبقاء Render مستيقظاً) ---
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health_check():
    return "Bots are running!", 200

# --- دالة إرسال الإشعار إلى تيليجرام ---
def send_notification(platform, username):
    msg = f"< {platform} USERNAME > Good\n[•] < @{username} > 🔸\n_______"
    try:
        requests.get(f'https://api.telegram.org/bot{TOK}/sendMessage?chat_id={ID}&text={msg}', timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")

# ==========================================
# 1. قسم فحص يوزرات تيليجرام (5 و 6 حروف)
# ==========================================
def telegram_worker():
    print("Started Telegram (5 & 6 chars) searching...")
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    
    while True:
        try:
            # اختيار عشوائي بين 5 و 6 حروف
            length = random.choice([5, 6])
            username = "".join(random.choices(chars, k=length))
            
            url = f"https://fragment.com/username/{username}"
            response = requests.get(url, timeout=10)
            
            # إذا كانت الصفحة قصيرة، يعني اليوزر متاح
            if len(response.text) < 20000:
                print(f"[TG - Good]: {username}")
                send_notification("TELEGRAM", username)
            else:
                print(f"[TG - Bad]: {username}")
                
        except Exception as e:
            print(f"TG Error: {e}")
        
        time.sleep(3) # انتظار 3 ثواني لتجنب الحظر

# ==========================================
# 2. قسم فحص يوزرات تيك توك (3 و 4 حروف)
# ==========================================
def tiktok_worker():
    print("Started TikTok (3 & 4 chars) searching...")
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    
    # تيك توك يحتاج Headers عشان يحسبه متصفح وليس بوت
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    while True:
        try:
            # اختيار عشوائي بين 3 و 4 حروف
            length = random.choice([3, 4])
            username = "".join(random.choices(chars, k=length))
            
            url = f"https://www.tiktok.com/@{username}"
            response = requests.get(url, headers=headers, timeout=10)
            
            # تيك توك يرجع 404 إذا كان الحساب غير موجود
            if response.status_code == 404 or "Couldn't find this account" in response.text:
                print(f"[TT - Good]: {username}")
                send_notification("TIKTOK", username)
            else:
                print(f"[TT - Bad]: {username}")
                
        except Exception as e:
            print(f"TT Error: {e}")
        
        # الانتظار 5 ثواني لتيك توك عشان ما يحظرنا بسرعة
        time.sleep(5) 

# --- التشغيل الرئيسي ---
if __name__ == "__main__":
    # 1. تشغيل بوت تيليجرام في خيط (Thread) منفصل
    tg_thread = threading.Thread(target=telegram_worker)
    tg_thread.daemon = True
    tg_thread.start()

    # 2. تشغيل بوت تيك توك في خيط (Thread) منفصل
    tt_thread = threading.Thread(target=tiktok_worker)
    tt_thread.daemon = True
    tt_thread.start()
    
    # 3. تشغيل خادم الويب (عشان Render ما يطفي السيرفر)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
