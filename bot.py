import telebot
import os
import threading
import time
import json
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- إعدادات البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

if not BOT_TOKEN or not ADMIN_ID or not CHANNEL_ID:
    print("Error: Missing environment variables.")
    exit(1)

ADMIN_ID = int(ADMIN_ID)
POSTS_FILE = "posts.json"

# --- خادم الويب ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Scheduled Poster Bot is running!", 200

# --- إعداد البوت ---
bot = telebot.TeleBot(BOT_TOKEN)

# --- إدارة الملفات ---
def load_posts():
    if os.path.exists(POSTS_FILE):
        try:
            with open(POSTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_posts(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=4)

def today_str():
    return time.strftime("%Y-%m-%d")

def current_time_str():
    return time.strftime("%H:%M")

# --- خيط النشر التلقائي (مراقبة أوقات كل منشور) ---
def auto_poster():
    time.sleep(10)
    print("✅ بدأ مراقبة أوقات المنشورات...")
    
    while True:
        try:
            now_time = current_time_str()
            today = today_str()
            posts = load_posts()
            
            for post in posts:
                # إذا وصل وقت المنشور، ولم ينشر اليوم
                if post.get("time") == now_time and post.get("last_posted_date") != today:
                    try:
                        if "media_id" in post:
                            bot.send_photo(
                                CHANNEL_ID,
                                post["media_id"],
                                caption=post.get("text", ""),
                                parse_mode="Markdown"
                            )
                        else:
                            bot.send_message(
                                CHANNEL_ID,
                                post["text"],
                                parse_mode="Markdown"
                            )
                        
                        # تحديث تاريخ النشر لهذا المنشور
                        post["last_posted_date"] = today
                        save_posts(posts)
                        
                        try:
                            bot.send_message(
                                ADMIN_ID,
                                f"✅ تم النشر المجدول بنجاح!\n"
                                f"🕐 الوقت: {now_time}\n"
                                f"📅 التاريخ: {today}"
                            )
                        except: pass
                        
                    except Exception as e:
                        try:
                            bot.send_message(ADMIN_ID, f"❌ خطأ في النشر:\n`{e}`", parse_mode="Markdown")
                        except: pass
            
            time.sleep(30)  # فحص كل 30 ثانية
            
        except Exception as e:
            print(f"Error in auto_poster: {e}")
            time.sleep(60)

# --- القائمة الرئيسية ---
def main_menu():
    posts = load_posts()
    today = today_str()
    posted_today = sum(1 for p in posts if p.get("last_posted_date") == today)
    
    text = (
        "🤖 **بوت النشر المجدول (وقت لكل منشور)**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📝 **إجمالي المنشورات:** {len(posts)}\n"
        f"📅 **المنشورة اليوم:** {posted_today} / {len(posts)}\n"
        f"⏰ **الوقت الحالي:** `{current_time_str()}`\n\n"
        "كل منشور له وقت محدد يُنشر فيه يومياً.\n"
        "اختر من القائمة:"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕ إضافة منشور جديد (مع وقت)", callback_data="add_post"),
        InlineKeyboardButton("📋 عرض المنشورات وأوقاتها", callback_data="list_posts"),
        InlineKeyboardButton("🗑️ حذف كل المنشورات", callback_data="clear_posts"),
        InlineKeyboardButton("📢 قناتنا الرسمية", url="https://t.me/TurboRashq")
    )
    return text, kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ هذا البوت خاص.")
        return
    text, kb = main_menu()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# --- إضافة منشور (الخطوة 1: طلب الوقت) ---
@bot.callback_query_handler(func=lambda call: call.data == "add_post")
def add_post_step1(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "⏰ **أرسل وقت نشر هذا المنشور (بنظام 24 ساعة):**\n\n"
        "مثال: `14:30` أو `09:00`\n\n"
        "لإلغاء أرسل /cancel",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_post_time)

def process_post_time(message):
    if message.text and message.text == "/cancel":
        bot.send_message(message.chat.id, "تم الإلغاء.")
        return
    
    time_str = message.text.strip()
    try:
        h, m = time_str.split(":")
        assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        assert len(h) == 2 and len(m) == 2
        formatted_time = f"{int(h):02d}:{int(m):02d}"
        
        # الخطوة 2: طلب محتوى المنشور
        msg = bot.send_message(
            message.chat.id,
            f"✅ تم تحديد الوقت: `{formatted_time}`.\n\n"
            f"📝 **الآن أرسل محتوى المنشور** (نص، صورة، أو فيديو مع وصف):",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_post_content, formatted_time)
        
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ صيغة خاطئة. أرسل الوقت بهذا الشكل: `14:30`"
        )

def process_post_content(message, post_time):
    if message.text and message.text == "/cancel":
        bot.send_message(message.chat.id, "تم الإلغاء.")
        return
    
    posts = load_posts()
    post_data = {"time": post_time}
    
    if message.photo:
        post_data["media_id"] = message.photo[-1].file_id
        post_data["type"] = "photo"
        post_data["text"] = message.caption if message.caption else ""
    elif message.video:
        post_data["media_id"] = message.video.file_id
        post_data["type"] = "video"
        post_data["text"] = message.caption if message.caption else ""
    elif message.text:
        post_data["type"] = "text"
        post_data["text"] = message.text
    else:
        bot.send_message(message.chat.id, "❌ نوع غير مدعوم.")
        return
    
    post_data["last_posted_date"] = ""
    posts.append(post_data)
    
    # ترتيب المنشورات حسب الوقت (من الأقدم للأحدث)
    posts.sort(key=lambda x: x.get("time", "00:00"))
    save_posts(posts)
    
    bot.send_message(
        message.chat.id, 
        f"✅ **تم حفظ المنشور بنجاح!**\n"
        f"⏰ سيتم نشره يومياً الساعة `{post_time}`\n"
        f"📝 إجمالي المنشورات: {len(posts)}", 
        parse_mode="Markdown"
    )
    text, kb = main_menu()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# --- عرض المنشورات ---
@bot.callback_query_handler(func=lambda call: call.data == "list_posts")
def list_posts(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    
    posts = load_posts()
    if not posts:
        bot.send_message(call.message.chat.id, "📭 لا توجد منشورات محفوظة.")
        return
    
    today = today_str()
    text = "📋 **المنشورات حسب وقت النشر:**\n\n"
    for i, p in enumerate(posts, 1):
        content = (p.get("text", "")[:30] + "...") if p.get("text") else p.get("type", "وسائط")
        status = "✅ اننشر اليوم" if p.get("last_posted_date") == today else "🕐 بانتظار وقته"
        text += f"**{p.get('time')}** - {content}\n_{status}_\n\n"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# --- حذف الكل ---
@bot.callback_query_handler(func=lambda call: call.data == "clear_posts")
def clear_posts(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id)
    save_posts([])
    bot.send_message(call.message.chat.id, "🗑️ تم حذف كل المنشورات.")
    text, kb = main_menu()
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# --- التشغيل ---
if __name__ == "__main__":
    poster_thread = threading.Thread(target=auto_poster)
    poster_thread.daemon = True
    poster_thread.start()

    bot_thread = threading.Thread(target=bot.infinity_polling)
    bot_thread.daemon = True
    bot_thread.start()
    print("Scheduled Poster Bot is running...")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
