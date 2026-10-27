import telebot
import os
import threading
import re
import requests
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
    return "Telegram Username Checker Bot is running!", 200

# --- إعداد البوت ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- نمط اليوزرات المطلوب: 3 خانات مفصولة بشرطتين، كل خانة 1-2 حرف/رقم ---
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9]{1,2}_[A-Za-z0-9]{1,2}_[A-Za-z0-9]{1,2}$')

def matches_pattern(username: str) -> bool:
    """التحقق من أن اليوزر يطابق النمط المطلوب"""
    username = username.lstrip('@')
    return bool(USERNAME_PATTERN.fullmatch(username))

def check_telegram_availability(username: str) -> bool:
    """
    فحص توفر اليوزر على تيليجرام.
    ترجع True إذا كان اليوزر غير مملوك (متاح)، False إذا كان مملوكًا.
    """
    try:
        # استخدام Telegram Bot API للتحقق من وجود الدردشة
        # إذا كان اليوزر غير موجود، سيرفع البوت استثناءً
        bot.get_chat(f"@{username}")
        return False  # اليوزر موجود ومملوك
    except telebot.apihelper.ApiTelegramException as e:
        error_msg = str(e).lower()
        # إذا كان الخطأ يشير إلى عدم وجود الدردشة، فاليوزر متاح
        if "chat not found" in error_msg or "user not found" in error_msg:
            return True
        # أخطاء أخرى (مثل حظر البوت) قد تعني أن اليوزر موجود ولكن لا يمكن الوصول إليه
        # نعتبره غير متاح لتجنب النتائج الإيجابية الخاطئة
        return False
    except Exception:
        return False

def check_fragment_availability(username: str) -> bool:
    """
    فحص توفر اليوزر على Fragment.com.
    ترجع True إذا كان اليوزر غير موجود في Fragment (أي غير متاح للبيع)، False إذا كان موجودًا.
    """
    try:
        url = f"https://fragment.com/username/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        # إذا كانت الصفحة تحتوي على كلمة "unavailable" فهذا يعني أن اليوزر غير متاح (مملوك أو محجوز)
        if "unavailable" in response.text.lower():
            return False
        # إذا لم تكن الصفحة موجودة (404) أو لا تحتوي على معلومات البيع، فاليوزر غير موجود في Fragment
        return True
    except Exception:
        # في حالة فشل الطلب، نفترض أن اليوزر غير موجود في Fragment (للأمان)
        return True

def is_username_fully_available(username: str) -> bool:
    """
    فحص شامل: اليوزر غير مملوك على تيليجرام وغير موجود في Fragment.
    """
    if not matches_pattern(username):
        return False
    
    # فحص تيليجرام
    if not check_telegram_availability(username):
        return False
    
    # فحص Fragment
    if not check_fragment_availability(username):
        return False
    
    return True

# --- القائمة الرئيسية ---
def main_menu():
    text = (
        "🔍 **بوت فحص يوزرات تيليجرام**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "يقوم البوت بفحص اليوزرات التي تطابق النمط التالي:\n"
        "`X_Y_Z`\n"
        "حيث كل خانة هي حرف أو رقم (1-2 حرف كحد أقصى).\n\n"
        "مثال: `g_d_g` أو `a_dd_r` أو `1_22_3`\n\n"
        "**شروط الفحص:**\n"
        "• غير مملوك على تيليجرام ✅\n"
        "• غير موجود في Fragment.com ✅\n\n"
        "الرجاء إرسال اليوزر الذي تريد فحصه (بدون @):"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📢 قناتنا الرسمية", url="https://t.me/TurboRashq"))
    
    return text, kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text, kb = main_menu()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# --- استلام اليوزر من المستخدم وفحصه ---
@bot.message_handler(func=lambda message: True)
def handle_username_check(message):
    chat_id = message.chat.id
    raw_username = message.text.strip().lstrip('@')
    
    # التحقق من النمط أولاً
    if not matches_pattern(raw_username):
        bot.reply_to(
            message,
            f"❌ اليوزر `{raw_username}` لا يطابق النمط المطلوب.\n\n"
            f"النمط المسموح: `X_Y_Z` (3 خانات، كل خانة 1-2 حرف/رقم، مفصولة بشرطة سفلية).",
            parse_mode="Markdown"
        )
        return
    
    # إرسال رسالة انتظار
    wait_msg = bot.reply_to(
        message,
        f"⏳ جاري فحص اليوزر `{raw_username}`...\n"
        f"يتم التحقق من تيليجرام و Fragment، يرجى الانتظار.",
        parse_mode="Markdown"
    )
    
    try:
        # فحص تيليجرام
        tg_available = check_telegram_availability(raw_username)
        # فحص Fragment
        fr_available = check_fragment_availability(raw_username)
        
        # إعداد النتيجة
        if tg_available and fr_available:
            status_emoji = "✅"
            status_text = "**متاح بالكامل!**"
            details = (
                f"• تيليجرام: غير مملوك ✅\n"
                f"• Fragment: غير موجود ✅"
            )
        elif tg_available and not fr_available:
            status_emoji = "⚠️"
            status_text = "**متاح على تيليجرام ولكن موجود في Fragment**"
            details = (
                f"• تيليجرام: غير مملوك ✅\n"
                f"• Fragment: موجود (قد يكون معروضًا للبيع) ⚠️"
            )
        elif not tg_available and fr_available:
            status_emoji = "⚠️"
            status_text = "**مملوك على تيليجرام وغير موجود في Fragment**"
            details = (
                f"• تيليجرام: مملوك ❌\n"
                f"• Fragment: غير موجود ✅"
            )
        else:
            status_emoji = "❌"
            status_text = "**غير متاح**"
            details = (
                f"• تيليجرام: مملوك ❌\n"
                f"• Fragment: موجود ❌"
            )
        
        result_text = (
            f"{status_emoji} **نتيجة الفحص لليوزر:** `{raw_username}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{status_text}\n\n"
            f"{details}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        # إضافة زر إعادة الفحص
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔄 فحص يوزر آخر", callback_data="check_again"))
        
        bot.edit_message_text(
            result_text,
            chat_id=chat_id,
            message_id=wait_msg.message_id,
            parse_mode="Markdown",
            reply_markup=kb
        )
        
    except Exception as e:
        bot.edit_message_text(
            f"❌ حدث خطأ أثناء الفحص: `{str(e)}`",
            chat_id=chat_id,
            message_id=wait_msg.message_id,
            parse_mode="Markdown"
        )

# --- زر إعادة الفحص ---
@bot.callback_query_handler(func=lambda call: call.data == "check_again")
def check_again(call):
    bot.answer_callback_query(call.id)
    text, kb = main_menu()
    bot.edit_message_text(
        text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=kb
    )

if __name__ == "__main__":
    t = threading.Thread(target=bot.infinity_polling)
    t.daemon = True
    t.start()
    print("Username Checker Bot is polling...")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
