import telebot
import os
import threading
import requests
import string
import time
import asyncio
from flask import Flask
from telethon import TelegramClient, functions
from telethon.errors import UsernameOccupiedError, UsernameInvalidError
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- إعدادات البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")

if not BOT_TOKEN or not ADMIN_ID:
    print("Error: BOT_TOKEN or ADMIN_ID is missing.")
    exit(1)

ADMIN_ID = int(ADMIN_ID)

# --- قيم Telegram Desktop الثابتة ---
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

# --- إعداد خادم الويب ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Telegram Username Hunter is running!", 200

# --- إعداد البوت ---
bot = telebot.TeleBot(BOT_TOKEN)

# إعداد جلسة Telethon للفحص
client = TelegramClient('session_name', API_ID, API_HASH)

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

# --- دالة الفحص الدقيق عبر Telethon ---
async def check_username_telethon(username: str) -> bool:
    try:
        # دالة الفحص المخصصة للحسابات الحقيقية فقط
        await client(functions.account.CheckUsernameRequest(username=username))
        return True  # متاح
    except (UsernameOccupiedError, UsernameInvalidError):
        # إذا كان الاسم محجوزاً أو غير صالح
        return False
    except Exception as e:
        print(f"Error checking {username}: {e}")
        return False

# --- دالة الصيد المتسلسل ---
def hunt_usernames(chat_id):
    global is_scanning
    
    bot.send_message(chat_id, "🚀 **بدأ الصيد الدقيق!**\nالآن البوت يستخدم حساب حقيقي (Userbot) لفحص دقيق 100%.\nالتأخير: 5 ثواني بين كل فحص.\nلإيقاف الصيد أرسل /stop", parse_mode="Markdown")
    
    found_count = 0
    checked_count = 0
    
    # تشغيل الـ event loop للـ Telethon
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    with client:
        for username in generate_usernames():
            if not is_scanning:
                break
                
            checked_count += 1
            
            # الفحص الدقيق
            is_free = loop.run_until_complete(check_username_telethon(username))
            
            if is_free:
                found_count += 1
                msg = (
                    f"🎯 **تم صيد يوزر متاح (دقة 100%)!**\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"اليوزر: `{username}`\n"
                    f"الفحص: متاح ✅\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"تم فحص: {checked_count} | تم صيد: {found_count}"
                )
                try:
                    bot.send_message(chat_id, msg, parse_mode="Markdown")
                except Exception as e:
                    print(f"Error sending message: {e}")
            
            if checked_count % 20 == 0:
                try:
                    bot.send_message(chat_id, f"⏳ جاري الصيد...\nتم فحص: {checked_count} يوزر.\nتم صيد: {found_count} يوزر.\n(آخر يوزر: `{username}`)", parse_mode="Markdown")
                except:
                    pass
                    
            time.sleep(5)

    bot.send_message(chat_id, "🛑 تم إيقاف عملية الصيد.")

# --- القائمة الرئيسية ---
def main_menu():
    text = (
        "👑 **بوت صيد اليوزرات (النسخة الدقيقة 100%)**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "يقوم البوت بفحص اليوزرات التي تطابق النمط:\n"
        "`X_Y_Z`\n\n"
        "الفحص يتم عبر حساب تيليجرام حقيقي (Userbot) لضمان الدقة.\n\n"
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
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ عذراً، هذا البوت خاص ومغلق للاستخدام الشخصي.")
        return
    text, kb = main_menu()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# --- أوامر التحكم بالصيد ---
@bot.callback_query_handler(func=lambda call: call.data == "start_hunt")
def start_hunt(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ هذا البوت خاص!", show_alert=True)
        return
        
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
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ هذا البوت خاص!", show_alert=True)
        return
        
    global is_scanning
    is_scanning = False
    bot.answer_callback_query(call.id, "تم إيقاف الصيد.")
    bot.send_message(call.message.chat.id, "🛑 تم إرسال أمر الإيقاف...")

@bot.message_handler(commands=['stop'])
def stop_command(message):
    if message.from_user.id != ADMIN_ID:
        return
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
