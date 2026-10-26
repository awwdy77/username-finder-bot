import telebot
import os
import threading
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- إعدادات البوت ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
USDT_TON_WALLET = os.environ.get("USDT_TON_WALLET", "UQ_Your_TON_Wallet_Address_Here")

if not BOT_TOKEN or not ADMIN_ID:
    print("Error: BOT_TOKEN or ADMIN_ID is missing.")
    exit(1)

# --- إعداد خادم الويب ---
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Turbo Rashq Bot is running!", 200

# --- إعداد البوت ---
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}
ORDERS = {}

# --- قائمة الخدمات ---
SERVICES = {
    "1": {"name": "متابعين تيك توك", "price_usd": 2.50},
    "2": {"name": "أعضاء تيليجرام", "price_usd": 1.50},
    "3": {"name": "متابعين إنستغرام", "price_usd": 3.00}
}

# --- القائمة الرئيسية ---
def main_menu():
    text = (
        "👑 مرحباً بك في **تربو رشق**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "المزود الأول لخدمات النمو في وسائل التواصل الاجتماعي.\n\n"
        "• تنفيذ سريع ⚡\n"
        "• جودة عالية 💎\n"
        "• دعم فني 24/7 📞\n\n"
        "الرجاء اختيار الخدمة للمتابعة:"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("متابعين تيك توك ($2.50)", callback_data="srv_1"),
        InlineKeyboardButton("أعضاء تيليجرام ($1.50)", callback_data="srv_2"),
        InlineKeyboardButton("متابعين إنستغرام ($3.00)", callback_data="srv_3")
    )
    return text, kb

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text, kb = main_menu()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# --- اختيار الخدمة ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("srv_"))
def handle_service(call):
    chat_id = call.message.chat.id
    service_id = call.data.split("_")[1]
    service = SERVICES[service_id]
    
    user_states[chat_id] = {"service_id": service_id, "service": service}
    
    bot.answer_callback_query(call.id)
    
    msg = bot.edit_message_text(
        f"الخدمة المختارة: **{service['name']}**\n"
        f"السعر لكل 1000: **${service['price_usd']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"الرجاء إرسال الرابط (الحساب أو القناة):",
        chat_id=chat_id, 
        message_id=call.message.message_id,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, handle_link)

# --- استلام الرابط ---
def handle_link(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        bot.reply_to(message, "انتهت الجلسة. الرجاء إرسال /start للبدء من جديد.")
        return
    
    user_states[chat_id]["link"] = message.text
    
    msg = bot.reply_to(
        message, 
        f"تم حفظ الرابط: `{message.text}`\n\n"
        f"الرجاء إدخال الكمية المطلوبة (الحد الأدنى 100، مثال: 1000):", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, handle_quantity)

# --- استلام الكمية وإنشاء الفاتورة ---
def handle_quantity(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        bot.reply_to(message, "انتهت الجلسة. الرجاء إرسال /start للبدء من جديد.")
        return
    
    try:
        qty = int(message.text)
        if qty < 100: 
            bot.reply_to(message, "الحد الأدنى للكمية هو 100.")
            return
    except ValueError:
        bot.reply_to(message, "خطأ. الرجاء إرسال أرقام فقط.")
        return

    state = user_states[chat_id]
    service = state["service"]
    link = state["link"]
    
    total_price = (service["price_usd"] / 1000) * qty
    order_id = str(chat_id)[-5:] + str(qty)[-3:]
    
    ORDERS[order_id] = {
        "customer_id": chat_id,
        "qty": qty,
        "service_name": service['name'],
        "link": link,
        "price": total_price
    }
    
    # تصميم الفاتورة
    invoice_text = (
        f"🧾 **فاتورة**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"رقم الطلب: `#{order_id}`\n\n"
        f"الخدمة: {service['name']}\n"
        f"الكمية: {qty}\n"
        f"الرابط: `{link}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**الإجمالي: {total_price:.2f} USDT**\n\n"
        f"**طريقة الدفع:**\n"
        f"الشبكة: TON (The Open Network)\n"
        f"المحفظة:\n"
        f"`{USDT_TON_WALLET}`\n\n"
        f"⚠️ يرجى تحويل المبلغ إلى المحفظة أعلاه، ثم الضغط على زر (تم الدفع)."
    )
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ تم الدفع", callback_data=f"paid_{order_id}"))
    kb.add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel_order"))
    
    bot.reply_to(message, invoice_text, parse_mode="Markdown", reply_markup=kb)
    del user_states[chat_id]

# --- إلغاء الطلب ---
@bot.callback_query_handler(func=lambda call: call.data == "cancel_order")
def cancel_order(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text("تم إلغاء الطلب.", chat_id=call.message.chat.id, message_id=call.message.message_id)

# --- استلام الدفع وإشعار الأدمن ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def handle_payment(call):
    order_id = call.data.split("_")[1]
    
    if order_id not in ORDERS:
        bot.answer_callback_query(call.id, "الطلب غير موجود.", show_alert=True)
        return

    order = ORDERS[order_id]
    
    bot.answer_callback_query(call.id, "جاري المراجعة...")
    bot.edit_message_text(
        "تم استلام الطلب. بانتظار تأكيد الإدارة.",
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id
    )
    
    # رسالة الأدمن
    admin_text = (
        f"🔔 **طلب جديد**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"رقم الطلب: `#{order_id}`\n"
        f"آي دي الزبون: `{order['customer_id']}`\n"
        f"الخدمة: {order['service_name']}\n"
        f"الكمية: {order['qty']}\n"
        f"الرابط: `{order['link']}`\n"
        f"المبلغ: {order['price']:.2f} USDT\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"تأكد من وصول المبلغ في محفظتك، ونفذ الطلب في لوحة SMM، ثم اضغط تأكيد."
    )
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ تأكيد التنفيذ", callback_data=f"approve_{order_id}"))
    
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=kb)

# --- تأكيد الأدمن للطلب ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def handle_approve(call):
    order_id = call.data.split("_")[1]
    order = ORDERS.get(order_id)
    
    if not order:
        bot.answer_callback_query(call.id, "الطلب غير موجود.", show_alert=True)
        return
        
    customer_id = order["customer_id"]
    
    bot.answer_callback_query(call.id, "تم التأكيد")
    bot.edit_message_text(f"تم تأكيد الطلب #{order_id} واكتماله.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    try:
        bot.send_message(
            customer_id, 
            f"✅ **تم اكتمال الطلب**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"طلبك `#{order_id}` تمت معالجته بنجاح.\n"
            f"شكراً لاستخدامك تربو رشق."
        , parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to message customer: {e}")
    
    if order_id in ORDERS:
        del ORDERS[order_id]

if __name__ == "__main__":
    t = threading.Thread(target=bot.infinity_polling)
    t.daemon = True
    t.start()
    print("Turbo Rashq Bot is polling...")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
