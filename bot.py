import telebot
import os
import threading
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- إعدادات البوت (تقرأ من Environment Variables في Render) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
USDT_TON_WALLET = os.environ.get("USDT_TON_WALLET", "UQ_Your_TON_Wallet_Address_Here")

if not BOT_TOKEN or not ADMIN_ID:
    print("Error: BOT_TOKEN or ADMIN_ID is missing.")
    exit(1)

# --- إعداد خادم الويب (لإبقاء Render مستيقظاً) ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "SMM Store Bot (USDT-TON) is running!", 200

# --- إعداد البوت ---
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}
ORDERS = {} # لحفظ الطلبات مؤقتاً لتجنب خطأ طول الرابط في الأزرار

# --- قائمة الخدمات ---
SERVICES = {
    "1": {"name": "متابعين تيك توك (1000)", "price_usd": 4.00}, 
    "2": {"name": "أعضاء قناة تيليجرام (1000)", "price_usd": 2.50}, 
    "3": {"name": "متابعين إنستغرام (1000)", "price_usd": 4.50}
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = (
        "🚀 أهلاً بك في متجر الرشق الاحترافي!\n"
        "🔗 قناتنا الرسمية: @YourChannelHere\n" # <-- غير هذا إلى معرف قناتك
        "━━━━━━━━━━━━━━━━━━\n\n"
        "اختر الخدمة التي تريدها:\n"
        "1️⃣ متابعين تيك توك (1000) - $4.00\n"
        "2️⃣ أعضاء تيليجرام (1000) - $2.50\n"
        "3️⃣ متابعين إنستغرام (1000) - $4.50\n\n"
        "أرسل رقم الخدمة (1 أو 2 أو 3):"
    )
    bot.reply_to(message, text)

@bot.message_handler(func=lambda message: message.text in ['1', '2', '3'])
def handle_service(message):
    chat_id = message.chat.id
    service_id = message.text
    service = SERVICES[service_id]
    
    user_states[chat_id] = {"service": service}
    
    msg = bot.reply_to(message, f"✅ اخترت: {service['name']}\n\n🔗 أرسل الآن رابط الحساب أو القناة:")
    bot.register_next_step_handler(msg, handle_link)

def handle_link(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        bot.reply_to(message, "⚠️ أرسل /start للبدء من جديد.")
        return
    
    user_states[chat_id]["link"] = message.text
    msg = bot.reply_to(message, "🔢 أرسل الكمية المطلوبة (مثال: 1000):")
    bot.register_next_step_handler(msg, handle_quantity)

def handle_quantity(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        bot.reply_to(message, "⚠️ أرسل /start للبدء من جديد.")
        return
    
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError
    except ValueError:
        bot.reply_to(message, "❌ أرسل رقم صحيح (مثال: 1000).")
        return

    state = user_states[chat_id]
    service = state["service"]
    link = state["link"]
    
    # حساب السعر النهائي
    total_price = (service["price_usd"] / 1000) * qty
    order_id = str(chat_id)[-5:] + str(qty)[-3:]
    
    # حفظ الطلب في الذاكرة لتجنب خطأ طول الرابط داخل زر تيليجرام
    ORDERS[order_id] = {
        "customer_id": chat_id,
        "qty": qty,
        "service_name": service['name'],
        "link": link
    }
    
    # رسالة الدفع للزبون (USDT عبر شبكة TON)
    payment_text = (
        f"🧾 **فاتورة الطلب #{order_id}**\n\n"
        f"📦 الخدمة: {service['name']}\n"
        f"🔢 الكمية: {qty}\n"
        f"🔗 الرابط: {link}\n"
        f"💰 المبلغ المطلوب: **{total_price:.2f} USDT**\n\n"
        f"🌐 **الشبكة المطلوبة: TON (The Open Network)**\n"
        f"💳 **عنوان المحفظة:**\n"
        f"`{USDT_TON_WALLET}`\n\n"
        f"⚠️ **هام جداً:** عند التحويل من محفظتك (مثل Tonkeeper)، تأكد من اختيار عملة **USDT** وشبكة **TON**. لا ترسل عبر شبكات أخرى وإلا ستضيع الأموال.\n\n"
        f"بعد التحويل، اضغط على زر (لقد قمت بالدفع) بالأسفل."
    )
    
    kb = InlineKeyboardMarkup()
    # وضعنا فقط رقم الطلب في الزر لتجنب خطأ حجم البيانات
    kb.add(InlineKeyboardButton("✅ لقد قمت بالدفع", callback_data=f"paid_{order_id}"))
    
    bot.reply_to(message, payment_text, parse_mode="Markdown", reply_markup=kb)
    del user_states[chat_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def handle_payment(call):
    order_id = call.data.split("_")[1]
    
    if order_id not in ORDERS:
        bot.answer_callback_query(call.id, "❌ حدث خطأ، الطلب غير موجود.", show_alert=True)
        return

    order_data = ORDERS[order_id]
    customer_id = order_data["customer_id"]
    qty = order_data["qty"]
    service_name = order_data["service_name"]
    link = order_data["link"]
    
    bot.answer_callback_query(call.id, "⏳ جاري مراجعة الدفع...")
    bot.edit_message_text("⏳ تم استلام إشعار الدفع. يرجى الانتظار حتى يقوم المتجر بمراجعة التحويل وتنفيذ الطلب.", chat_id=customer_id, message_id=call.message.message_id)
    
    # إرسال الطلب للأدمن (أنت)
    admin_text = (
        f"🔔 **طلب جديد #{order_id}**\n\n"
        f"👤 الآي دي: `{customer_id}`\n"
        f"📦 الخدمة: {service_name}\n"
        f"🔢 الكمية: {qty}\n"
        f"🔗 الرابط: {link}\n\n"
        f"⚠️ اذهب إلى محفظتك وتأكد من وصول مبلغ USDT (شبكة TON).\n"
        f"إذا وصل المبلغ، اذهب لموقع SMM واطلب الخدمة، ثم اضغط (تأكيد التنفيذ) هنا."
    )
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ تأكيد التنفيذ", callback_data=f"approve_{order_id}_{customer_id}"))
    
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def handle_approve(call):
    data = call.data.split("_")
    order_id = data[1]
    customer_id = data[2]
    
    bot.answer_callback_query(call.id, "✅ تم التأكيد")
    bot.edit_message_text(f"✅ تم تأكيد الطلب #{order_id} وخصم الرصيد.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    # إبلاغ الزبون
    try:
        bot.send_message(customer_id, f"🎉 **مبروك!**\nتم تأكيد طلبك #{order_id} وبدأ تنفيذه. شكراً لثقتك بنا!")
    except Exception as e:
        print(f"Failed to message customer: {e}")

if __name__ == "__main__":
    # تم إصلاح هذا السطر هنا (حذف non_stop)
    t = threading.Thread(target=bot.infinity_polling)
    t.daemon = True
    t.start()
    print("SMM Store Bot (USDT-TON) is polling...")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
