import os
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# আপনার বটের টোকেন ও ফায়ারবেস প্রজেক্ট আইডি
BOT_TOKEN = "8981396014:AAE9EnLaZDrYPjcoSPMsIlk_7IyStmoU0JM"
FIREBASE_PROJECT_ID = "xtube-6ea1d"

# Render Web Service Port Health-Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Trend VideoTube Bot is 100% Live and Running!")

    def log_message(self, format, *args):
        return  # স্ট্যাক লগ বন্ধ রাখা

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"🌐 Health check server listening on port {port}")
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await context.bot.send_message(
            chat_id=chat_id, 
            text="👋 Trend VideoTube Pro বটে স্বাগতম! অ্যাপ থেকে ভিডিও আনলক করে এখানে দেখুন।"
        )
        return

    video_code = args[0] # e.g. vid_101

    # ফায়ারবেস থেকে লাইভ ফাইল আইডি ও টাইটেল ডাটা টেনে আনা
    firestore_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{video_code}"
    
    try:
        response = requests.get(firestore_url)
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})

            file_id = fields.get('fileId', {}).get('stringValue', '')
            title = fields.get('title', {}).get('stringValue', 'Exclusive Video')

            if file_id:
                # ১. ভিডিও ইনবক্সে সেন্ড করা
                sent_video = await context.bot.send_video(
                    chat_id=chat_id, 
                    video=file_id, 
                    caption=f"🎥 {title}\n📌 Uploaded for Trend VideoTube Pro"
                )

                # ২. নোটিশ মেসেজ
                sent_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text="✅ Video Unlocked Successfully!\n\n⚠️ It will auto delete in 5 minutes."
                )

                # ৩. ঠিক ৫ মিনিট (৩০০ সেকেন্ড) পর অটো ডিলিট
                await asyncio.sleep(300)
                
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_video.message_id)
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="🗑️ ৫ মিনিট পার হয়ে যাওয়ায় নিরাপত্তা স্বার্থে ভিডিওটি অটো-ডিলিট করা হলো।"
                    )
                except Exception as del_err:
                    print(f"Delete Error: {del_err}")

            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ ভিডিও আইডি পাওয়া যায়নি।")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ ভিডিওটি ডিলিট হয়ে গেছে বা পাওয়া যায়নি।")

    except Exception as e:
        print(f"Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text="❌ কোনো একটি সমস্যা হয়েছে। আবার চেষ্টা করুন।")

if __name__ == '__main__':
    # ব্যাকগ্রাউন্ডে হেলথ-চেক ওয়েব সার্ভার স্টার্ট
    threading.Thread(target=run_health_server, daemon=True).start()

    print("🤖 Bot is starting on Render Free Web Service...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
