import requests
import random
import os
import time
import threading
from flask import Flask

# محاولة استيراد مكتبة إنستغرام، وإذا لم تكن موجودة سيتم تجاهلها واستخدام الطريقة المباشرة
try:
    from igkrx import check_username_availability
    IGKRX_AVAILABLE = True
except ImportError:
    IGKRX_AVAILABLE = False

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
    return "All Bots are running!", 200

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
            length = random.choice([5, 6])
            username = "".join(random.choices(chars, k=length))
            
            url = f"https://fragment.com/username/{username}"
            response = requests.get(url, timeout=10)
            
            if len(response.text) < 20000:
                print(f"[TG - Good]: {username}")
                send_notification("TELEGRAM", username)
            else:
                print(f"[TG - Bad]: {username}")
                
        except Exception as e:
            print(f"TG Error: {e}")
        
        time.sleep(random.uniform(3, 5)) 

# ==========================================
# 2. قسم فحص يوزرات تيك توك (3 و 4 حروف)
# ==========================================
def tiktok_worker():
    print("Started TikTok (3 & 4 chars) searching...")
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    while True:
        try:
            length = random.choice([3, 4])
            username = "".join(random.choices(chars, k=length))
            
            url = f"https://www.tiktok.com/@{username}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 404 or "Couldn't find this account" in response.text:
                print(f"[TT - Good]: {username}")
                send_notification("TIKTOK", username)
            else:
                print(f"[TT - Bad]: {username}")
                
        except Exception as e:
            print(f"TT Error: {e}")
        
        time.sleep(random.uniform(5, 7)) 

# ==========================================
# 3. قسم فحص يوزرات إنستغرام (3 و 4 حروف)
# ==========================================
def instagram_worker():
    print("Started Instagram (3 & 4 chars) searching...")
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    while True:
        try:
            length = random.choice([3, 4])
            username = "".join(random.choices(chars, k=length))
            
            is_available = False
            
            # المحاولة الأولى: استخدام مكتبة igkrx إذا كانت متوفرة
            if IGKRX_AVAILABLE:
                try:
                    is_available = check_username_availability(username)
                except Exception as e:
                    print(f"igkrx error, falling back: {e}")
                    is_available = False
            
            # المحاولة الثانية (الاحتياطية): الفحص المباشر عبر الرابط
            if not IGKRX_AVAILABLE or not is_available:
                # لا نستخدم الطريقة الاحتياطية إلا إذا فشلت igkrx تماماً أو أعطت False
                url = f"https://www.instagram.com/{username}/"
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 404:
                    is_available = True
            
            if is_available:
                print(f"[IG - Good]: {username}")
                send_notification("INSTAGRAM", username)
            else:
                print(f"[IG - Bad]: {username}")
                
        except Exception as e:
            print(f"IG Error: {e}")
        
        # الانتظار 8 إلى 10 ثواني لأن إنستغرام حساس جداً
        time.sleep(random.uniform(8, 10)) 

# --- التشغيل الرئيسي ---
if __name__ == "__main__":
    print("Starting all workers...")
    
    # تشغيل بوت تيليجرام
    tg_thread = threading.Thread(target=telegram_worker)
    tg_thread.daemon = True
    tg_thread.start()

    # تشغيل بوت تيك توك
    tt_thread = threading.Thread(target=tiktok_worker)
    tt_thread.daemon = True
    tt_thread.start()

    # تشغيل بوت إنستغرام
    ig_thread = threading.Thread(target=instagram_worker)
    ig_thread.daemon = True
    ig_thread.start()
    
    # تشغيل خادم الويب عشان Render ما يطفي السيرفر
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
