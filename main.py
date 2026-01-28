import os, asyncio, shutil, time, sys, re
from datetime import datetime, timedelta
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import PeerIdInvalid, FloodWait
from motor.motor_asyncio import AsyncIOMotorClient
from pyromod import listen
from aiohttp import web

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "23708017"))
API_HASH = os.environ.get("API_HASH", "bb43c2e9f011dea16cad362d56c889b6")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8422932464:AAEhXencYfAL108lGAjEGySXw_9nwvUhm3o")
OWNER = 1306149967
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://tejuchoudhary0456_db_user:rQiNVxZvKfDAWVzA@teju.1z1ohk0.mongodb.net/?appName=Teju")
CREDIT = "Teju"

# Clients Setup (100 Workers for 5G Speed)
bot = Client("SamratBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=100)
user_bot = Client("SamratUser", api_id=API_ID, api_hash=API_HASH)

# Database
db_client = AsyncIOMotorClient(MONGO_URI, tlsAllowInvalidCertificates=True)
db = db_client['SamratBot']
premium_db = db['premium_users']
stop_batch = {}

# --- SMART PEER RESOLVER (Numeric Fix) ---
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

# --- DOWNLOAD & SEND (Now with Text Support) ---
async def download_and_send(message, chat_id, msg_id, custom_wm):
    try:
        # Force Resolve Peer
        try: await user_bot.get_chat(chat_id)
        except: pass
            
        content = await user_bot.get_messages(chat_id, msg_id)
        if not content or content.empty: return False
        
        # --- TEXT MESSAGE HANDLING ---
        if not (content.video or content.photo or content.document or content.audio):
            if content.text:
                await bot.send_message(
                    message.chat.id, 
                    f"{content.text}\n\n✨ **𝐒𝐚𝐯𝐞 𝐛𝐲 {CREDIT}**\n🖋️ **𝐖𝐌:** {custom_wm}"
                )
                return True
            return True # Skip empty/polls

        # --- MEDIA HANDLING (Photo/Video/Doc) ---
        p = await bot.send_message(message.chat.id, f"📥 **𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐢𝐧𝐠:** `{msg_id}`...")
        st = time.time()
        file = await user_bot.download_media(content)
        
        if file:
            await p.edit("⬆️ **𝐔𝐩𝐥𝐨𝐚𝐝𝐢𝐧𝐠...**")
            cap = content.caption if content.caption else f"✨ **𝐒𝐚𝐯𝐞 𝐛𝐲 {CREDIT}**\n🖋️ **𝐖𝐌:** {custom_wm}"
            
            # Auto-Thumbnail Extraction
            thumb = None
            if content.video and content.video.thumbs:
                thumb = await user_bot.download_media(content.video.thumbs[0])

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
        await bot.send_message(message.chat.id, f"❌ **Error ID {msg_id}:** {e}")
    return True

# (Baaki handlers jaise /start, /login, /stop aur Batch logic same rahega)
