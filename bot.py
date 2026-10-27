import telebot
import os
import threading
import re
import requests
import string
import time
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- إعدادات البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

if not BOT_TOKEN or not ADMIN_ID:
    print("Error: BOT_TOKEN or ADMIN_ID is missing.")
    exit(1)

# --- إعداد خادم الويب ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Telegram Username Hunter is running!", 200

# --- إعداد البوت ---
bot = telebot.TeleBot(BOT_TOKEN)

is_scanning = False
scan_thread = None

# --- دالة توليد اليوزرات المتسلسلة ---
def generate_usernames():
    chars = string.ascii_letters + string.digits
    valid_parts = []
    for c in chars:
        valid_parts.append(c)
        for c2 in chars:
            valid_parts.append(c + c2)

    for p1 in valid_parts:
        for p2 in valid_parts:
            for p3 in valid_parts:
                yield f"{p1}_{p2}_{p3}"

# --- دوال الفحص الثلاثي ---
def check_telegram_api(username: str) -> bool:
    """الفحص عبر البوت"""
    try:
        bot.get_chat(f"@{username}")
        return False  # مملوك
    except telebot.apihelper.ApiTelegramException as e:
        if "chat not found" in str(e).lower() or "user not found" in str(e).lower():
            return True  # متاح
        return False
    except Exception:
        return False

def check_tme_web(username: str) -> bool:
    """الفحص عبر صفحة الويب t.me"""
    try:
        url = f"https://t.me/{username}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        # إذا كانت الصفحة تحتوي على عنوان أو وصف، يعني الحساب موجود ومملوك
        if 'tgme_page_title' in response.text or 'tgme_page_extra' in response.text:
            return False # مملوك
        return True # متاح
    except Exception:
        return False # في حال الخطأ نعتبره غير متاح للأمان

def check_fragment_availability(username: str) -> bool:
    """الفحص عبر Fragment"""
    try:
        url = f"https://fragment.com/username/{username}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if "unavailable" in response.text.lower():
            return False # موجود في Fragment
        return True
    except Exception:
        return True

# --- دالة الصيد المتسلسل ---
def hunt_usernames(chat_id):
    global is_scanning
    
    bot.send_message(chat_id, "🚀 **بدأ الصيد الثلاثي!**\nالآن البوت يفحص: (API) + (t.me) + (Fragment) لضمان دقة 100%.\nالتأخير: 5 ثواني بين كل فحص.\nلإيقاف الصيد أرسل /stop", parse_mode="Markdown")
    
    found_count = 0
    checked_count = 0
    
    for username in generate_usernames():
        if not is_scanning:
            break
            
        checked_count += 1
        
        # الفحص الثلاثي
        is_free_tg_api = check_telegram_api(username)
        is_free_tme_web = check_tme_web(username)
        
        # إذا كان متاح في الاثنين، نفحص Fragment
        if is_free_tg_api and is_free_tme_web:
            if check_fragment_availability(username):
                found_count += 1
                msg = (
                    f"🎯 **تم صيد يوزر متاح (دقة عالية)!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"اليوزر: `{username}`\n"
                    f"فحص API: متاح ✅\n"
                    f"فحص الويب: متاح ✅\n"
                    f"Fragment: غير موجود ✅\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"تم فحص: {checked_count} | تم صيد: {found_count}"
                )
                try:
                    bot.send_message(chat_id, msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"Error sending message: {e}")
        
        # إرسال تحديث كل 20 فحص
        if checked_count % 20 == 0:
            try:
                bot.send_message(chat_id, f"⏳ جاري الصيد الثلاثي...\nتم فحص: {checked_count} يوزر.\nتم صيد: {found_count} يوزر.\n(آخر يوزر: `{username}`)", parse_mode="Markdown")
            except:
                pass
                
        # التأخير 5 ثواني
        time.sleep(5)

    bot.send_message(chat_id, "🛑 تم إيقاف عملية الصيد.")

# --- القائمة الرئيسية ---
def main_menu():
    text = (
        "👑 **بوت صيد اليوزرات (النسخة الدقيقة)**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "يقوم البوت بفحص اليوزرات التي تطابق النمط:\n"
        "`X_Y_Z`\n\n"
        "الفحص يشمل:\n"
        "1. تيليجرام API\n"
        "2. موقع t.me\n"
        "3. موقع Fragment\n\n"
        "اختر من القائمة:"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("🚀 بدء الصيد", callback_data="start_hunt"),
        InlineKeyboardButton("🛑 إيقاف الصيد", callback_data="stop_hunt"),
        InlineKeyboardButton("📢 قناتنا الرسمية", url="https://t.me/TurboRashq")
    )
    return text, kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text, kb = main_menu()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "start_hunt")
def start_hunt(call):
    global is_scanning, scan_thread
    if is_scanning:
        bot.answer_callback_query(call.id, "البوت يعمل بالفعل!", show_alert=True)
        return
    
    is_scanning = True
    bot.answer_callback_query(call.id)
    
    scan_thread = threading.Thread(target=hunt_usernames, args=(call.message.chat.id,))
    scan_thread.daemon = True
    scan_thread.start()

@bot.callback_query_handler(func=lambda call: call.data == "stop_hunt")
def stop_hunt(call):
    global is_scanning
    is_scanning = False
    bot.answer_callback_query(call.id, "تم إيقاف الصيد.")
    bot.send_message(call.message.chat.id, "🛑 تم إرسال أمر الإيقاف...")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    global is_scanning
    is_scanning = False
    bot.reply_to(message, "🛑 تم إرسال أمر الإيقاف...")

if __name__ == "__main__":
    t = threading.Thread(target=bot.infinity_polling)
    t.daemon = True
    t.start()
    print("Username Hunter Bot is polling...")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
