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

# --- قائمة الخدمات (الأسعار الجديدة المخفضة) ---
SERVICES = {
    "1": {"name": "TikTok Followers", "name_ar": "متابعين تيك توك", "price_usd": 2.50},
    "2": {"name": "Telegram Members", "name_ar": "أعضاء تيليجرام", "price_usd": 1.50},
    "3": {"name": "Instagram Followers", "name_ar": "متابعين إنستغرام", "price_usd": 3.00}
}

# --- القائمة الرئيسية ---
def main_menu():
    text = (
        "Welcome to **Turbo Rashq** | مرحباً بك في تربو رشق\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "The premier provider for social media growth.\n"
        "المزود الأول لخدمات النمو في وسائل التواصل الاجتماعي.\n\n"
        "• Fast Delivery (تنفيذ سريع)\n"
        "• High Quality (جودة عالية)\n"
        "• 24/7 Support (دعم فني)\n\n"
        "Please select a service to continue:\n"
        "الرجاء اختيار الخدمة للمتابعة:"
    )
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("TikTok Followers ($2.50) | متابعين تيك توك", callback_data="srv_1"),
        InlineKeyboardButton("Telegram Members ($1.50) | أعضاء تيليجرام", callback_data="srv_2"),
        InlineKeyboardButton("Instagram Followers ($3.00) | متابعين إنستغرام", callback_data="srv_3")
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
        f"Selected Service: **{service['name']}**\n"
        f"الخدمة المختارة: **{service['name_ar']}**\n"
        f"Price per 1000: **${service['price_usd']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Please send the target link (Profile or Channel):\n"
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
        bot.reply_to(message, "Session expired. Please /start again.")
        return
    
    user_states[chat_id]["link"] = message.text
    service = user_states[chat_id]["service"]
    
    msg = bot.reply_to(
        message, 
        f"Link saved: `{message.text}`\n\n"
        f"Please enter the quantity (Min: 100, e.g., 1000):\n"
        f"الرجاء إدخال الكمية المطلوبة (الحد الأدنى 100، مثال: 1000):", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, handle_quantity)

# --- استلام الكمية وإنشاء الفاتورة ---
def handle_quantity(message):
    chat_id = message.chat.id
    if chat_id not in user_states:
        bot.reply_to(message, "Session expired. Please /start again.")
        return
    
    try:
        qty = int(message.text)
        if qty < 100: 
            bot.reply_to(message, "Minimum quantity is 100. / الحد الأدنى للكمية هو 100.")
            return
    except ValueError:
        bot.reply_to(message, "Invalid number. Please send digits only. / أرسل أرقام فقط.")
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
        "service_name_ar": service['name_ar'],
        "link": link,
        "price": total_price
    }
    
    # تصميم الفاتورة الرسمية
    invoice_text = (
        f"**INVOICE | فاتورة**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Order ID | رقم الطلب: `#{order_id}`\n\n"
        f"Service | الخدمة: {service['name']}\n"
        f"Quantity | الكمية: {qty}\n"
        f"Link | الرابط: `{link}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**Total | الإجمالي: {total_price:.2f} USDT**\n\n"
        f"**Payment Method | طريقة الدفع:**\n"
        f"Network | الشبكة: TON (The Open Network)\n"
        f"Wallet | المحفظة:\n"
        f"`{USDT_TON_WALLET}`\n\n"
        f"⚠️ Please transfer the exact amount to the wallet above, then click 'Payment Completed'.\n"
        f"يرجى تحويل المبلغ إلى المحفظة أعلاه، ثم الضغط على زر (تم الدفع)."
    )
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Payment Completed | تم الدفع", callback_data=f"paid_{order_id}"))
    kb.add(InlineKeyboardButton("Cancel | إلغاء", callback_data="cancel_order"))
    
    bot.reply_to(message, invoice_text, parse_mode="Markdown", reply_markup=kb)
    del user_states[chat_id]

# --- إلغاء الطلب ---
@bot.callback_query_handler(func=lambda call: call.data == "cancel_order")
def cancel_order(call):
    bot.answer_callback_query(call.id)
    bot.edit_message_text("Order cancelled. | تم إلغاء الطلب.", chat_id=call.message.chat.id, message_id=call.message.message_id)

# --- استلام الدفع وإشعار الأدمن ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def handle_payment(call):
    order_id = call.data.split("_")[1]
    
    if order_id not in ORDERS:
        bot.answer_callback_query(call.id, "Order not found. | الطلب غير موجود.", show_alert=True)
        return

    order = ORDERS[order_id]
    
    bot.answer_callback_query(call.id, "Processing... | جاري المراجعة...")
    bot.edit_message_text(
        "Order received. Waiting for admin approval.\n"
        "تم استلام الطلب. بانتظار تأكيد الإدارة.",
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id
    )
    
    # رسالة الأدمن (أنت)
    admin_text = (
        f"**NEW ORDER | طلب جديد**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Order: `#{order_id}`\n"
        f"User ID: `{order['customer_id']}`\n"
        f"Service: {order['service_name']}\n"
        f"Quantity: {order['qty']}\n"
        f"Link: `{order['link']}`\n"
        f"Amount: {order['price']:.2f} USDT\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Verify the payment in your TON wallet. If received, complete the order on the SMM panel and click Approve."
    )
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Approve Order | تأكيد التنفيذ", callback_data=f"approve_{order_id}"))
    
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=kb)

# --- تأكيد الأدمن للطلب ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_"))
def handle_approve(call):
    order_id = call.data.split("_")[1]
    order = ORDERS.get(order_id)
    
    if not order:
        bot.answer_callback_query(call.id, "Order not found.", show_alert=True)
        return
        
    customer_id = order["customer_id"]
    
    bot.answer_callback_query(call.id, "Approved")
    bot.edit_message_text(f"Order #{order_id} marked as Completed.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    try:
        bot.send_message(
            customer_id, 
            f"✅ **Order Completed | تم اكتمال الطلب**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Your order `#{order_id}` has been processed successfully.\n"
            f"تمت معالجة طلبك بنجاح. شكراً لاستخدامك تربو رشق."
        , parse_mode="Markdown")
    except Exception as e:
        print(f"Failed to message customer: {e}")
    
    # مسح الطلب من الذاكرة بعد الانتهاء
    if order_id in ORDERS:
        del ORDERS[order_id]

if __name__ == "__main__":
    t = threading.Thread(target=bot.infinity_polling)
    t.daemon = True
    t.start()
    print("Turbo Rashq Bot is polling...")

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
