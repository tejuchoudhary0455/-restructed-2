import os, asyncio, shutil, time, sys, re
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import PeerIdInvalid, FloodWait
from motor.motor_asyncio import AsyncIOMotorClient
from pyromod import listen
from aiohttp import web

# --- CONFIGURATION (Render variables se connect hai) ---
API_ID = int(os.environ.get("API_ID", "23708017"))
API_HASH = os.environ.get("API_HASH", "bb43c2e9f011dea16cad362d56c889b6")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8422932464:AAEhXencYfAL108lGAjEGySXw_9nwvUhm3o")
OWNER = 1306149967
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tejuchoudhary0456_db_user:rQiNVxZvKfDAWVzA@teju.1z1ohk0.mongodb.net/?appName=Teju")
CREDIT = "Teju"

# Clients Setup
bot = Client("SamratBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=100)
user_bot = Client("SamratUser", api_id=API_ID, api_hash=API_HASH)

# Database Setup
db_client = AsyncIOMotorClient(MONGO_URI, tlsAllowInvalidCertificates=True)
db = db_client['SamratBot']
premium_db = db['premium_users']
stop_batch = {}

# --- WEB SERVER (Render Fix) ---
async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', lambda r: web.Response(text="Samrat 5G is Live! 🚀"))])
    return app

# --- SMART PEER RESOLVER ---
async def get_chat_id(link):
    try:
        if "t.me/c/" in link:
            return int("-100" + link.split("/")[-2])
        elif "t.me/" in link:
            parts = link.split("/")
            if len(parts) >= 4:
                chat_id = parts[-2]
                if chat_id.isdigit():
                    return int("-100" + chat_id)
                return chat_id
        return None
    except: return None

# --- PROGRESS BAR (5G Status) ---
async def progress_bar(current, total, message, start_time, action):
    now = time.time()
    diff = now - start_time
    if round(diff % 3.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        ui = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))
        status = (f"⚡ **Samrat {action}...**\n\n"
                  f"📊 **Status:** `{ui}` **{round(percentage, 2)}%**\n"
                  f"🚀 **Speed:** `{round(speed / 1024 / 1024, 2)} MB/s` (5G)")
        try: await message.edit(status)
        except: pass

# --- CORE LOGIC (Text + Media + Thumbnail) ---
async def download_and_send(message, chat_id, msg_id, custom_wm):
    try:
        try: await user_bot.get_chat(chat_id)
        except: pass
            
        content = await user_bot.get_messages(chat_id, msg_id)
        if not content or content.empty: return False
        
        # TEXT MESSAGE HANDLING
        if not (content.video or content.photo or content.document or content.audio):
            if content.text:
                await bot.send_message(message.chat.id, f"{content.text}\n\n✨ **Save by {CREDIT}**\n🖋️ **WM:** {custom_wm}")
                return True
            return True

        # MEDIA HANDLING
        p = await bot.send_message(message.chat.id, f"📥 **Extracting:** `{msg_id}`...")
        st = time.time()
        file = await user_bot.download_media(content, progress=progress_bar, progress_args=(p, st, "Downloading"))
        
        if file:
            await p.edit("⬆️ **Uploading...**")
            cap = content.caption if content.caption else f"✨ **Save by {CREDIT}**\n🖋️ **WM:** {custom_wm}"
            thumb = await user_bot.download_media(content.video.thumbs[0]) if content.video and content.video.thumbs else None

            if content.video:
                await bot.send_video(message.chat.id, file, caption=cap, thumb=thumb, supports_streaming=True)
            elif content.photo:
                await bot.send_photo(message.chat.id, file, caption=cap)
            else:
                await bot.send_document(message.chat.id, file, caption=cap, thumb=thumb)
                
            if os.path.exists(file): os.remove(file)
            if thumb and os.path.exists(thumb): os.remove(thumb)
            await p.delete()
            return True
    except Exception as e:
        await bot.send_message(message.chat.id, f"❌ Error ID {msg_id}: {e}")
    return True

# --- MAIN RUNNER ---
async def main():
    await bot.start()
    # User bot ko start karna zaroori hai
    try:
        if not user_bot.is_connected: await user_bot.start()
    except: pass
    
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()
    print("🚀 SAMRAT IS ONLINE!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
