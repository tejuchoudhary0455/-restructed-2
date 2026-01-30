import os, asyncio, shutil, time, sys, cv2
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import FloodWait
from pyromod import listen
from aiohttp import web

# --- CONFIGURATION ---
API_ID = int(os.environ.get("API_ID", "23708017"))
API_HASH = os.environ.get("API_HASH", "bb43c2e9f011dea16cad362d56c889b6")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8422932464:AAEhXencYfAL108lGAjEGySXw_9nwvUhm3o")
OWNER = int(os.environ.get("OWNER", "1306149967"))
CREDIT = "Teju"

# Max speed ke liye workers badhaye hain
bot = Client("SamratBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=100)
user = Client("SamratUserV7", api_id=API_ID, api_hash=API_HASH, workers=100) 

PREMIUM_USERS = [OWNER] 

async def web_server():
    app = web.Application()
    app.add_routes([web.get('/', lambda request: web.Response(text="Teju's Bot is Running Fast!"))])
    return app

async def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', port).start()

# --- THUMBNAIL GENERATOR ---
def generate_thumbnail(video_path):
    thumb_path = f"{video_path}.jpg"
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(thumb_path, frame)
        cap.release()
        return thumb_path
    cap.release()
    return None

# --- PROGRESS BAR ---
async def progress_bar(current, total, message, start_time, action):
    now = time.time()
    diff = now - start_time
    if round(diff % 3.00) == 0 or current == total: # Interval kam kiya for fast updates
        percentage = current * 100 / total
        speed = current / (diff if diff > 0 else 1)
        progress_ui = "▰" * int(percentage / 10) + "▱" * (10 - int(percentage / 10))
        tmp = (
            f"⚡ **𝐒𝐚𝐦𝐫𝐚𝐭 {action}...**\n\n"
            f"📊 **𝐒𝐭𝐚𝐭𝐮𝐬:** `{progress_ui}` **{round(percentage, 2)}%**\n"
            f"🚀 **𝐒𝐩𝐞𝐞𝐝:** `{round(speed / 1024 / 1024, 2)} MB/s`"
        )
        try: await message.edit(tmp)
        except: pass

# --- MEDIA HANDLER ---
async def download_and_send(client, message, chat_id, msg_id):
    if not user.is_connected: await user.start()
    
    try:
        content = await user.get_messages(chat_id, msg_id)
    except:
        try:
            await user.join_chat(chat_id)
            content = await user.get_messages(chat_id, msg_id)
        except: return False

    if not content or content.empty: return False
    
    p = await bot.send_message(message.chat.id, f"📥 **𝐄𝐱𝐭𝐫𝐚𝐜𝐭𝐢𝐧𝐠:** `{msg_id}`...")
    cap = content.caption if content.caption else f"✨ **𝐒𝐚𝐯𝐞 𝐛𝐲 {CREDIT}**"

    if not content.media:
        await bot.send_message(message.chat.id, content.text if content.text else "Empty")
        await p.delete()
        return True

    st = time.time()
    try:
        # Download with Max Speed
        file = await user.download_media(content, progress=progress_bar, progress_args=(p, st, "Downloading"))
        if not file: return False

        await p.edit("⬆️ **𝐔𝐩𝐥𝐨𝐚𝐝𝐢𝐧𝐠 𝐰𝐢𝐭𝐡 𝐓𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥...**")
        
        if content.video:
            thumb = generate_thumbnail(file)
            await bot.send_video(
                message.chat.id, file, caption=cap, 
                thumb=thumb, supports_streaming=True, 
                progress=progress_bar, progress_args=(p, time.time(), "Uploading")
            )
            if thumb and os.path.exists(thumb): os.remove(thumb)
        elif content.photo:
            await bot.send_photo(message.chat.id, file, caption=cap)
        else:
            await bot.send_document(message.chat.id, file, caption=cap, 
                                    progress=progress_bar, progress_args=(p, time.time(), "Uploading"))
        
        if os.path.exists(file): os.remove(file)
        await p.delete()
        return True
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await download_and_send(client, message, chat_id, msg_id)
    except Exception as e:
        await p.edit(f"❌ **Error:** `{e}`")
        return False

@bot.on_message(filters.text & filters.private)
async def handle_links(client, message):
    if "t.me/" not in message.text: return
    if message.chat.id not in PREMIUM_USERS: return await message.reply("❌ Buy Premium.")
    
    link = message.text.strip().rstrip('/')
    parts = link.split("/")
    
    try:
        start_id = int(parts[-1])
        chat_id = int("-100" + parts[-2]) if "t.me/c/" in link else parts[-2]
            
        ask_batch = await bot.ask(message.chat.id, "🔢 **Kitni posts?**")
        count = int(ask_batch.text)
        
        for i in range(count):
            if not await download_and_send(client, message, chat_id, start_id + i): break
            await asyncio.sleep(1) # Speed ke liye delay kam kiya
            
        await message.reply("✅ **Batch Complete!**")
    except Exception as e:
        await message.reply(f"❌ **Error:** `{e}`")

# --- LOGIN & START ---
@bot.on_callback_query(filters.regex("login"))
async def login_cb(client, cb):
    await cb.answer()
    ph = await bot.ask(cb.message.chat.id, "📱 **Enter Number with +91:**")
    phone = ph.text.strip()
    if not user.is_connected: await user.connect()
    try:
        ch = await user.send_code(phone)
        otp_ask = await bot.ask(cb.message.chat.id, "📩 **Enter OTP:**")
        await user.sign_in(phone, ch.phone_code_hash, otp_ask.text.replace(" ", ""))
        await bot.send_message(cb.message.chat.id, "🎉 **Login Success!**")
    except Exception as e: await bot.send_message(cb.message.chat.id, f"❌ {e}")

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await bot.send_photo(message.chat.id, photo="https://telegra.ph/file/0998a44c45b78f4477813.jpg", 
                         caption="🔥 **High Speed Bot Ready!**", 
                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Login", callback_data="login")]]))

async def main():
    await bot.start()
    asyncio.create_task(run_web_server())
    print("🚀 FAST BOT READY!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
