import os
import asyncio
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "8981396014:AAGpznHF9Z6tgk92nvh700lT_UxevLkaoD4" # Your original bot token
FIREBASE_PROJECT_ID = "xtube-6ea1d"          # Firebase Project ID
BOT_USERNAME = "XTubeearn_bot"              # Bot Username (without @)
MINI_APP_SHORTNAME = "app"                   # Mini App short_name (configured in BotFather)
CHANNEL_USERNAME = "@chotigolpobangla25"          # Your official channel username
MINI_APP_URL = "https://xtubeearn.blogspot.com" # Your Mini App site link

# 1. RENDER HEALTH-CHECK SERVER
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

# 🛠️ HELPER: FIRESTORE REFERRAL PROCESSOR
def process_firestore_referral(new_user, referrer_id):
    new_user_id = str(new_user.id)
    user_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{new_user_id}"

    try:
        res = requests.get(user_url)
        
        # User does not exist -> Create user & Credit Referrer
        if res.status_code == 404:
            payload = {
                "fields": {
                    "user_id": {"integerValue": int(new_user.id)},
                    "first_name": {"stringValue": new_user.first_name or "User"},
                    "username": {"stringValue": new_user.username or ""},
                    "balance": {"doubleValue": 5.00}, # 5 Signup Bonus
                    "watchedVideosCount": {"integerValue": 0},
                    "dailyAdCount": {"integerValue": 0},
                    "referredBy": {"stringValue": str(referrer_id) if referrer_id else ""},
                    "isActive": {"booleanValue": False},
                    "hasJoinedChannel": {"booleanValue": False},
                    "pendingReferBonus": {"doubleValue": 0.00},
                    "totalJoined": {"integerValue": 0},
                    "activeCount": {"integerValue": 0},
                    "inactiveCount": {"integerValue": 0}
                }
            }
            requests.patch(user_url, json=payload)
            print(f"✅ New user created in Firestore: {new_user_id}")

            # Credit Referrer in Firestore
            if referrer_id and str(referrer_id) != new_user_id:
                ref_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{referrer_id}"
                ref_res = requests.get(ref_url)
                
                if ref_res.status_code == 200:
                    ref_data = ref_res.json().get('fields', {})
                    cur_tj = int(ref_data.get('totalJoined', {}).get('integerValue', 0))
                    cur_inact = int(ref_data.get('inactiveCount', {}).get('integerValue', 0))
                    
                    pend_field = ref_data.get('pendingReferBonus', {})
                    cur_pend = float(pend_field.get('doubleValue', pend_field.get('integerValue', 0)))

                    patch_ref_url = f"{ref_url}?updateMask.fieldPaths=totalJoined&updateMask.fieldPaths=inactiveCount&updateMask.fieldPaths=pendingReferBonus"
                    patch_ref_payload = {
                        "fields": {
                            "totalJoined": {"integerValue": cur_tj + 1},
                            "inactiveCount": {"integerValue": cur_inact + 1},
                            "pendingReferBonus": {"doubleValue": cur_pend + 5.00}
                        }
                    }
                    requests.patch(patch_ref_url, json=patch_ref_payload)
                    print(f"🎉 Referrer {referrer_id} credited +₹5.00 pending bonus!")

    except Exception as e:
        print("Error processing referral in Firestore:", e)


# 2. BOT COMMAND: /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    args = context.args

    # A. Normal /start command (No Parameter)
    if not args:
        process_firestore_referral(user, None)
        welcome_msg = (
            f"👋 **Welcome {user.first_name}!**\n\n"
            "🎬 Earn money daily by watching videos and completing tasks in our Mini App!\n\n"
            "👇 Click the button below to open the app:"
        )
        keyboard = [[InlineKeyboardButton("🚀 Open XTube Earn App", web_app={"url": MINI_APP_URL})]]
        await context.bot.send_message(
            chat_id=chat_id, 
            text=welcome_msg, 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    param = args[0]

    # B. REFERRAL DEEP LINK (e.g. /start 7480551514 or /start ref_7480551514)
    if param.startswith("ref_") or param.isdigit():
        referrer_id = param.replace("ref_", "")
        process_firestore_referral(user, referrer_id)

        welcome_msg = (
            f"👋 **Welcome {user.first_name}!**\n\n"
            "🎉 You joined using your friend's referral link!\n"
            "🎬 Open the Mini App to start working and earning money.\n\n"
            "👇 Click the button below to enter the app:"
        )
        keyboard = [[InlineKeyboardButton("🚀 Open XTube Earn App", web_app={"url": MINI_APP_URL})]]
        await context.bot.send_message(
            chat_id=chat_id, 
            text=welcome_msg, 
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # C. UNLOCKED VIDEO DEEP LINK REQUEST FROM BOT INBOX (e.g. /start vid_101)
    video_code = param.replace("vid_", "")
    firestore_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{video_code}"

    try:
        response = requests.get(firestore_url)
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', {})

            file_id = fields.get('fileId', {}).get('stringValue', '')
            title = fields.get('title', {}).get('stringValue', 'Exclusive Video')

            if file_id:
                # 1. Send video to inbox
                sent_video = await context.bot.send_video(
                    chat_id=chat_id, 
                    video=file_id, 
                    caption=f"🎥 **{title}**\n\n📌 Unlocked via **XTube Earn**",
                    parse_mode="Markdown"
                )

                # 2. 5-minute timer notice
                sent_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text="✅ **Video Unlocked Successfully!**\n\n⚠️ **Note:** This video will automatically delete in **5 minutes** for security reasons.",
                    parse_mode="Markdown"
                )

                # 3. Auto-delete after 5 minutes (300 seconds)
                await asyncio.sleep(300)
                
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_video.message_id)
                    await context.bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
                    await context.bot.send_message(
                        chat_id=chat_id, 
                        text="🗑️ Video automatically deleted after 5 minutes for security reasons."
                    )
                except Exception as del_err:
                    print(f"Auto-delete failed: {del_err}")

            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ Video file ID not found.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="❌ Video not found.")

    except Exception as e:
        print(f"Error in video unlock command: {e}")

# 3. EASY FILE ID GENERATOR FOR ADMIN
async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.video:
        file_id = update.message.video.file_id
        msg_text = (
            f"📹 **Video File ID Generated:**\n\n"
            f"`{file_id}`\n\n"
            f"👆 Copy the File ID above and paste it into the admin panel!"
        )
        await update.message.reply_text(text=msg_text, parse_mode="Markdown")

# 4. INSTANT AUTO-BROADCASTER TO ALL BOT USERS & CHANNEL
async def auto_bot_broadcaster(app: Application):
    while True:
        try:
            # -------------------------------------------------------------
            # A. Broadcast New Videos to All Bot Users & Channel
            # -------------------------------------------------------------
            vids_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos"
            res_v = requests.get(vids_url)
            
            if res_v.status_code == 200:
                docs = res_v.json().get('documents', [])
                for doc in docs:
                    fields = doc.get('fields', {})
                    vid_code = doc['name'].split('/')[-1]
                    is_sent = fields.get('channelBroadcasted', {}).get('booleanValue', False)
                    title = fields.get('title', {}).get('stringValue', 'New Video')
                    img_url = fields.get('imgUrl', {}).get('stringValue', fields.get('thumbnailUrl', {}).get('stringValue', ''))

                    if not is_sent:
                        # Prepare post content
                        post_text = (
                            f"🎁 **Dear friends, don't miss the video! / Watch Now!**\n\n"
                            f"📌 **Title:** {title}\n\n"
                            f"💸 **Watch the video and earn a lot!**"
                        )
                        # 🌟 DIRECT MINI APP DIRECT-LINK WITH VIDEO CODE PARAMETER
                        btn_url = f"https://t.me/{BOT_USERNAME}/{MINI_APP_SHORTNAME}?startapp=vid_{vid_code}"
                        keyboard = [[InlineKeyboardButton("🚀 Unlock full video", url=btn_url)]]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        # 1. Post to Official Telegram Channel
                        try:
                            if img_url and img_url.startswith("http"):
                                await app.bot.send_photo(chat_id=CHANNEL_USERNAME, photo=img_url, caption=post_text, parse_mode="Markdown", reply_markup=reply_markup)
                            else:
                                await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=post_text, parse_mode="Markdown", reply_markup=reply_markup)
                        except Exception as ch_err:
                            print(f"Channel post video err: {ch_err}")

                        # 2. Broadcast to ALL Users who started the Bot
                        users_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users"
                        res_users = requests.get(users_url)
                        
                        if res_users.status_code == 200:
                            user_docs = res_users.json().get('documents', [])
                            for u_doc in user_docs:
                                u_fields = u_doc.get('fields', {})
                                u_id = u_fields.get('user_id', {}).get('integerValue')
                                if u_id:
                                    try:
                                        if img_url and img_url.startswith("http"):
                                            await app.bot.send_photo(chat_id=int(u_id), photo=img_url, caption=post_text, parse_mode="Markdown", reply_markup=reply_markup)
                                        else:
                                            await app.bot.send_message(chat_id=int(u_id), text=post_text, parse_mode="Markdown", reply_markup=reply_markup)
                                    except Exception:
                                        pass
                                    await asyncio.sleep(0.04)

                        # Mark as broadcasted in Firestore
                        patch_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/videos/{vid_code}?updateMask.fieldPaths=channelBroadcasted"
                        requests.patch(patch_url, json={"fields": {"channelBroadcasted": {"booleanValue": True}}})
                        print(f"✅ New Video {vid_code} broadcasted to all users and channel!")

            # -------------------------------------------------------------
            # B. Broadcast Successful Payouts to All Bot Users & Channel
            # -------------------------------------------------------------
            payouts_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/withdrawals"
            res_p = requests.get(payouts_url)
            
            if res_p.status_code == 200:
                docs_p = res_p.json().get('documents', [])
                for doc in docs_p:
                    fields = doc.get('fields', {})
                    tx_id = doc['name'].split('/')[-1]
                    status = fields.get('status', {}).get('stringValue', '')
                    is_sent = fields.get('channelBroadcasted', {}).get('booleanValue', False)
                    username = fields.get('username', {}).get('stringValue', 'User')
                    amount = fields.get('amount', {}).get('stringValue', '100.00')
                    method = fields.get('method', {}).get('stringValue', 'UPI')

                    if status == "Success" and not is_sent:
                        payout_text = (
                            f"💸 **New Payment Received! (Payment Proof)** 💸\n\n"
                            f"👤 **User:** @{username}\n"
                            f"💰 **Amount:** ₹{amount}\n"
                            f"🏦 **Method:** {method}\n"
                            f"✅ **Status:** Successfully Paid 🟢\n\n"
                            f"🔥 If @{username} can earn this much daily, why are you waiting? Start watching videos and get paid today!"
                        )
                        keyboard = [[InlineKeyboardButton("🚀 Start Earning Now", web_app={"url": MINI_APP_URL})]]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        # 1. Post to Channel
                        try:
                            await app.bot.send_message(chat_id=CHANNEL_USERNAME, text=payout_text, parse_mode="Markdown", reply_markup=reply_markup)
                        except Exception as ch_err:
                            print(f"Channel post payout err: {ch_err}")

                        # 2. Broadcast to ALL Users
                        users_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users"
                        res_users = requests.get(users_url)
                        if res_users.status_code == 200:
                            user_docs = res_users.json().get('documents', [])
                            for u_doc in user_docs:
                                u_fields = u_doc.get('fields', {})
                                u_id = u_fields.get('user_id', {}).get('integerValue')
                                if u_id:
                                    try:
                                        await app.bot.send_message(chat_id=int(u_id), text=payout_text, parse_mode="Markdown", reply_markup=reply_markup)
                                    except Exception:
                                        pass
                                    await asyncio.sleep(0.04)

                        # Mark as broadcasted
                        patch_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/withdrawals/{tx_id}?updateMask.fieldPaths=channelBroadcasted"
                        requests.patch(patch_url, json={"fields": {"channelBroadcasted": {"booleanValue": True}}})
                        print(f"✅ Payout {tx_id} broadcasted to all users and channel!")

        except Exception as loop_err:
            print("Broadcaster loop error:", loop_err)

        await asyncio.sleep(10)

async def post_init(app: Application):
    asyncio.create_task(auto_bot_broadcaster(app))

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()

    print("🤖 XTube Earn Bot is running with Auto-Broadcaster & Referral System...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_file))
    
    app.run_polling()
