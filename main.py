import os
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "8981396014:AAFU9Jo5YQo01mek8ZURFTC_1khyRVsu7zI"
FIREBASE_PROJECT_ID = "xtube-6ea1d"

CHANNEL_USERNAME = "@XTubeearn_bot"
MINI_APP_URL = "https://yourname.blogspot.com"

# 1. RENDER WEB SERVICE HEALTH-CHECK SERVER
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"XTube Earn Telegram Bot is 100% Active & Healthy!")

    def log_message(self, format, *args):
        return

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Health-Check HTTP Server listening on port {port}")
    server.serve_forever()

# 2. BOT COMMAND: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        welcome_msg = (
            "👋 **স্বাগতম XTube Earn বটের মধ্যে!**\n\n"
            "🎬 আমাদের মিনি অ্যাপ থেকে প্রতিদিন ভিডিও দেখে এবং টাস্ক পূরণ করে ইনকাম করুন!\n\n"
            "👇 অ্যাপে প্রবেশ করতে নিচের বাটনে ক্লিক করুন:"
        )
        keyboard = [[InlineKeyboardButton("🚀 Open XTube Earn App", web_app={"url": MINI_APP_URL})]]
        await context.bot.send_message(
            chat_id=chat_id, 
            text=welcome_msg, 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    video_code = args[0] # e.g. vid_101
    firestore_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{video_code}"

    try:
        response = requests.get(firestore_url)
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})

            file_id = fields.get('fileId', {}).get('stringValue', '')
            title = fields.get('title', {}).get('stringValue', 'Exclusive Video')

            if file_id:
                sent_video = await context.bot.send_video(
                    chat_id=chat_id, 
                    video=file_id, 
                    caption=f"🎥 **{title}**\n\n📌 Unlocked via **XTube Earn**",
                    parse_mode="Markdown"
                )

                sent_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text="✅ **Video Unlocked Successfully!**\n\n⚠️ **Note:** This video will automatically delete in **5 minutes** for security reasons.",
                    parse_mode="Markdown"
                )

                await asyncio.sleep(300)
                
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_video.message_id)
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="🗑️ ৫ মিনিট পার হয়ে যাওয়ায় নিরাপত্তা স্বার্থে ভিডিওটি অটো-ডিলিট করা হলো।"
                    )
                except Exception as del_err:
                    print(f"Auto-delete failed: {del_err}")

            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ ভিডিও ফাইল আইডি পাওয়া যায়নি।")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ ভিডিওটি পাওয়া যায়নি।")

    except Exception as e:
        print(f"Error in start command: {e}")

# 3. EASY FILE ID GENERATOR FOR ADMIN
async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.video:
        file_id = update.message.video.file_id
        msg_text = (
            f"📹 **Video File ID Generated:**\n\n"
            f"`{file_id}`\n\n"
            f"👆 উপর থেকে File ID টি কপি করে এডমিন প্যানেলে পেস্ট করুন!"
        )
        await update.message.reply_text(text=msg_text, parse_mode="Markdown")

# 4. BACKGROUND TASK: AUTO BROADCAST NEW VIDEOS & PAYOUTS
async def auto_channel_broadcaster(app: Application):
    while True:
        try:
            vids_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos"
            res = requests.get(vids_url)
            if res.status_code == 200:
                docs = res.json().get('documents', [])
                for doc in docs:
                    fields = doc.get('fields', {})
                    vid_code = doc['name'].split('/')[-1]
                    is_sent = fields.get('channelBroadcasted', {}).get('booleanValue', False)
                    title = fields.get('title', {}).get('stringValue', 'New Video')
                    img_url = fields.get('imgUrl', {}).get('stringValue', '')

                    if not is_sent and CHANNEL_USERNAME != "@your_channel_username":
                        post_text = (
                            f"🎁 **Dear friends, don't miss the video! / Watch Now!**\n\n"
                            f"📌 **Title:** {title}\n\n"
                            f"💸 **Watch the video and earn a lot!**"
                        )
                        btn_url = f"https://t.me/XTubeearn_bot/app?startapp={vid_code}"
                        keyboard = [[InlineKeyboardButton("🚀 Unlock full videos", url=btn_url)]]

                        if img_url:
                            await app.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_url, caption=post_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
                        else:
                            await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=post_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

                        update_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{vid_code}?updateMask.fieldPaths=channelBroadcasted"
                        requests.patch(update_url, json={"fields": {"channelBroadcasted": {"booleanValue": True}}})

            payouts_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/withdrawals"
            res_p = requests.get(payouts_url)
            if res_p.status_code == 200:
                docs_p = res_p.json().get('documents', [])
                for doc in docs_p:
                    fields = doc.get('fields', {})
                    tx_id = doc['name'].split('/')[-1]
                    status = fields.get('status', {}).get('stringValue', '')
                    is_sent = fields.get('channelBroadcasted', {}).get('booleanValue', False)
                    username = fields.get('username', {}).get('stringValue', 'user')
                    amount = fields.get('amount', {}).get('stringValue', '100.00')
                    method = fields.get('method', {}).get('stringValue', 'UPI')

                    if status == "Success" and not is_sent and CHANNEL_USERNAME != "@your_channel_username":
                        payout_text = (
                            f"💸 **New Payment Received!**\n\n"
                            f"👤 **User:** {username}\n"
                            f"💰 **Amount:** ₹{amount}\n"
                            f"🏦 **Method:** {method}\n\n"
                            f"🔥 If @{username} can earn this much daily, why are you waiting? Start watching videos and get paid today!"
                        )
                        keyboard = [[InlineKeyboardButton("🚀 Start Earning Now", web_app={"url": MINI_APP_URL})]]
                        await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=payout_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

                        update_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/withdrawals/{tx_id}?updateMask.fieldPaths=channelBroadcasted"
                        requests.patch(update_url, json={"fields": {"channelBroadcasted": {"booleanValue": True}}})

        except Exception as err:
            print("Broadcaster Loop Error:", err)

        await asyncio.sleep(20)

async def post_init(app: Application):
    asyncio.create_task(auto_channel_broadcaster(app))

if __name__ == '__main__':
    # ১. পুরোনো কোনো ঝুলন্ত কানেকশন বা ওয়েবহুক থাকলে অটোম্যাটিক ডিলিট করা
    try:
        delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        requests.get(delete_url, timeout=5)
        print("🧹 Cleared old webhooks & ghost connections successfully!")
    except Exception as e:
        print("Webhook clear note:", e)

    # ২. রেন্ডার পোর্ট ৮০৮০ হেলথ-চেক সার্ভার স্টার্ট
    threading.Thread(target=run_health_server, daemon=True).start()

    print("🤖 XTube Earn Bot is running...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    
    # ৩. drop_pending_updates=True দিয়ে নতুন কানেকশন স্টার্ট
    app.run_polling(drop_pending_updates=True)
