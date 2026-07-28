import os
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "8981396014:AAE9EnLaZDrYPjcoSPMsIlk_7IyStmoU0JM"
FIREBASE_PROJECT_ID = "xtube-6ea1d"

# 1. RENDER WEB SERVICE HEALTH-CHECK SERVER (Runs on background thread)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"XTube Earn Telegram Bot is 100% Active & Healthy!")

    def log_message(self, format, *args):
        return # Disable console HTTP logs

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Health-Check HTTP Server listening on port {port}")
    server.serve_forever()

# 2. BOT COMMAND: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    # A. Normal /start command (No video code)
    if not args:
        welcome_msg = (
            "👋 **স্বাগতম XTube Earn বটের মধ্যে!**\n\n"
            "🎬 আমাদের মিনি অ্যাপ থেকে প্রতিদিন ভিডিও দেখে এবং টাস্ক পূরণ করে ইনকাম করুন!\n\n"
            "👇 অ্যাপে প্রবেশ করতে নিচের বাটনে ক্লিক করুন:"
        )
        await context.bot.send_message(
            chat_id=chat_id, 
            text=welcome_msg, 
            parse_mode="Markdown"
        )
        return

    # B. Deep Link /start vid_101 (Unlocked Video Request)
    video_code = args[0] # e.g. vid_101
    
    # Query Firebase Firestore REST API for video document
    firestore_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{video_code}"

    try:
        response = requests.get(firestore_url)
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})

            file_id = fields.get('fileId', {}).get('stringValue', '')
            title = fields.get('title', {}).get('stringValue', 'Exclusive Video')

            if file_id:
                # 1. Send Unlocked Video
                sent_video = await context.bot.send_video(
                    chat_id=chat_id, 
                    video=file_id, 
                    caption=f"🎥 **{title}**\n\n📌 Unlocked via **XTube Earn**",
                    parse_mode="Markdown"
                )

                # 2. Send Expiration Notice Message
                sent_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text="✅ **Video Unlocked Successfully!**\n\n⚠️ **Note:** This video will automatically delete in **5 minutes** for security reasons.",
                    parse_mode="Markdown"
                )

                # 3. Schedule 5 Minutes Auto-Delete (300 seconds)
                await asyncio.sleep(300)
                
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_video.message_id)
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="🗑️ ৫ মিনিট সময় পার হয়ে যাওয়ায় নিরাপত্তা স্বার্থে ভিডিওটি অটো-ডিলিট করা হলো।"
                    )
                except Exception as del_err:
                    print(f"Auto-delete failed: {del_err}")

            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ ভিডিও ফাইল আইডি পাওয়া যায়নি।")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ ভিডিওটি ডিলিট হয়ে গেছে বা পাওয়া যায়নি।")

    except Exception as e:
        print(f"Error in start command: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ কোনো সমস্যা হয়েছে। আবার চেষ্টা করুন।")

# 3. EASY FILE ID GENERATOR (When Admin sends or forwards any video to bot)
async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.video:
        file_id = update.message.video.file_id
        msg_text = (
            f"📹 **Video File ID Generated:**\n\n"
            f"`{file_id}`\n\n"
            f"👆 উপর থেকে File ID টি কপি করে আপনার এডমিন প্যানেলে পেস্ট করুন!"
        )
        await update.message.reply_text(text=msg_text, parse_mode="Markdown")

if __name__ == '__main__':
    # Start Port 8080 HTTP Health Server for Render Free Tier
    threading.Thread(target=run_health_server, daemon=True).start()

    print("🤖 XTube Earn Bot is starting...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    
    app.run_polling()
