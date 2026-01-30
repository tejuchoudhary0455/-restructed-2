import os, asyncio, time, re
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, RPCError, SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from pyromod import listen

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID", "23708017"))
API_HASH = os.environ.get("API_HASH", "bb43c2e9f011dea16cad362d56c889b6")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8422932464:AAEhXencYfAL108lGAjEGySXw_9nwvUhm3o")
MONGO_URI = "mongodb+srv://tejuchoudhary0456_db_user:rQiNVxZvKfDAWVzA@teju.1z1ohk0.mongodb.net/?appName=Teju"

bot = Client("SamratBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = AsyncIOMotorClient(MONGO_URI)['SamratBot']
user_sessions = db['sessions']

stop_batch = {}

# --- OTP LOGIN LOGIC ---
async def login_with_otp(client, message):
    try:
        phone_ask = await bot.ask(message.chat.id, "📲 अपना **Mobile Number** भेजें (Country Code के साथ, e.g. +919876543210):", timeout=300)
        phone_number = phone_ask.text.replace(" ", "")
        
        # Temporary client for OTP
        temp_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
        await temp_client.connect()
        
        try:
            code_data = await temp_client.send_code(phone_number)
        except Exception as e:
            return await message.reply(f"❌ **Error:** `{str(e)}`")

        otp_ask = await bot.ask(message.chat.id, "📩 आपके Telegram पर एक **OTP** आया है। उसे यहाँ लिखें (Format: 1 2 3 4 5):", timeout=300)
        otp_code = otp_ask.text.replace(" ", "")

        try:
            await temp_client.sign_in(phone_number, code_data.phone_code_hash, otp_code)
        except SessionPasswordNeeded:
            # 2-Step Verification
            pwd_ask = await bot.ask(message.chat.id, "🔐 आपके अकाउंट पर **2-Step Verification** लगा है। अपना Password भेजें:", timeout=300)
            await temp_client.check_password(pwd_ask.text)
        except (PhoneCodeInvalid, PhoneCodeExpired):
            return await message.reply("❌ OTP गलत है या एक्सपायर हो गया है।")

        # Session String Generation
        string_session = await temp_client.export_session_string()
        await user_sessions.update_one({"user_id": message.from_user.id}, {"$set": {"session": string_session}}, upsert=True)
        
        me = await temp_client.get_me()
        await message.reply(f"✅ **Login Successful!**\nWelcome {me.first_name}\n\nAb aap links bhej sakte hain.")
        await temp_client.disconnect()

    except Exception as e:
        await message.reply(f"❌ **Login Failed:** `{str(e)}`")

# --- START & CALLBACK ---
@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    buttons = [[InlineKeyboardButton("🔐 OTP Login", callback_data="otp_login")],
               [InlineKeyboardButton("📊 Status", callback_data="bot_status")]]
    await message.reply_text("🏆 **𝐒𝐀𝐌𝐑𝐀𝐓 𝟓𝐆 𝐁𝐎𝐓** 🏆\n\nAb Restricted Content download karein bina session ke tension ke!", reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_callback_query()
async def callbacks(client, query: CallbackQuery):
    if query.data == "otp_login":
        await query.message.delete()
        await login_with_otp(client, query.message)
    elif query.data == "stop":
        stop_batch[query.from_user.id] = True
        await query.answer("🛑 Batch Stopped!", show_alert=True)

# --- PROGRESS BAR ---
async def progress_bar(current, total, status_msg, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 4.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        bar = "🟢" * int(percentage/10) + "⚪" * (10 - int(percentage/10))
        try:
            await status_msg.edit(
                f"📥 **Downloading...**\n`{bar}` {round(percentage, 2)}%\n⚡ **Speed:** {round(speed / 1024, 2)} KB/s",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop", callback_data="stop")]])
            )
        except: pass

# --- DOWNLOAD HANDLER ---
@bot.on_message(filters.text & filters.private)
async def main_handler(client, message):
    if "t.me/" not in message.text: return
    
    # Check Session from DB
    data = await user_sessions.find_one({"user_id": message.from_user.id})
    if not data:
        return await message.reply("❌ Pehle login karein!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔐 Login Now", callback_data="otp_login")]]))

    link = message.text.strip()
    try:
        if "t.me/c/" in link: chat_id = int("-100" + link.split("/")[-2])
        else: chat_id = link.split("/")[-2]
        msg_id = int(link.split("/")[-1])
    except: return await message.reply("❌ Invalid Link!")

    wm = await bot.ask(message.chat.id, "🖋️ **Watermark Likhein:**")
    count = await bot.ask(message.chat.id, "🔢 **Count:**")
    
    u_bot = Client("SamratUser", api_id=API_ID, api_hash=API_HASH, session_string=data['session'])
    await u_bot.start()
    
    stop_batch[message.from_user.id] = False
    
    for i in range(int(count.text)):
        if stop_batch.get(message.from_user.id): break
        curr_id = msg_id + i
        sts = await bot.send_message(message.chat.id, f"📡 **Processing ID:** `{curr_id}`")
        
        try:
            msg = await u_bot.get_messages(chat_id, curr_id)
            if not (msg and not msg.empty): continue

            if not msg.media:
                await bot.send_message(message.chat.id, f"{msg.text}\n\n{wm.text}")
            else:
                st_t = time.time()
                file = await u_bot.download_media(msg, progress=progress_bar, progress_args=(sts, st_t))
                
                await sts.edit("⬆️ **Uploading...**")
                cap = f"{msg.caption if msg.caption else ''}\n\n{wm.text}"
                
                if msg.video: await bot.send_video(message.chat.id, file, caption=cap, supports_streaming=True)
                elif msg.photo: await bot.send_photo(message.chat.id, file, caption=cap)
                else: await bot.send_document(message.chat.id, file, caption=cap)

                if file and os.path.exists(file): os.remove(file)
            await sts.delete()
            await asyncio.sleep(2)
        except Exception as e:
            await bot.send_message(message.chat.id, f"❌ Error `{curr_id}`: {e}")

    await u_bot.stop()
    await message.reply("✅ **Batch Done!**")

async def main():
    await bot.start()
    print("Samrat 5G Pro is Active with OTP Login!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
