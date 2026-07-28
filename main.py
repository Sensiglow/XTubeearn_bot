import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# আপনার নতুন বটের টোকেন ও ফায়ারবেস প্রজেক্ট আইডি
BOT_TOKEN = "8981396014:AAE9EnLaZDrYPjcoSPMsIlk_7IyStmoU0JM"
FIREBASE_PROJECT_ID = "xtube-6ea1d"

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

    # ফায়ারবেস থেকে লাইভ ফাইল আইডি আনা
    firestore_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{video_code}"
    
    try:
        response = requests.get(firestore_url)
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})

            file_id = fields.get('fileId', {}).get('stringValue', '')
            title = fields.get('title', {}).get('stringValue', 'Exclusive Video')

            if file_id:
                # ১. ভিডিও পাঠানো
                sent_video = await context.bot.send_video(
                    chat_id=chat_id, 
                    video=file_id, 
                    caption=f"🎥 {title}\n📌 Uploaded for Trend VideoTube Pro"
                )

                # ২. নোটিশ পাঠানো
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
    print("🤖 New Bot is starting on Render...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
