import requests
import random
import os
import time
import threading
from flask import Flask

# --- إعدادات البوت ---
TOK = os.environ.get("BOT_TOKEN")
ID = os.environ.get("CHAT_ID")
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"

# --- خادم الويب الصغير (لإبقاء Render مستيقظاً) ---
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health_check():
    return "Bot is running!", 200

# --- منطق البوت (نفس الكود السابق) ---
def run_bot():
    print("Started searching...")
    while True:
        try:
            length = random.choice([5, 6])
            username = "".join(random.choices(CHARS, k=length))
            url = f"https://fragment.com/username/{username}"
            response = requests.get(url, timeout=10)
            
            if len(response.text) < 20000:
                print(f"[•] Good: {username}")
                msg = f"< TELEGRAM USERNAME > Good\n[•] < @{username} > 🔸\n_______"
                requests.get(f'https://api.telegram.org/bot{TOK}/sendMessage?chat_id={ID}&text={msg}')
            else:
                print(f"[✗] Bad: {username}")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(3) # الانتظار 3 ثواني

# --- تشغيل البوت في خيط منفصل ---
if __name__ == "__main__":
    # تشغيل البوت في الخلفية
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # تشغيل خادم الويب (الذي سيستقبل الـ ping)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
