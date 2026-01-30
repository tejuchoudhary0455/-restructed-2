import os, asyncio, time
from pyrogram import Client, filters, idle
from pyrogram.errors import FloodWait, RPCError, SessionPasswordNeeded
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from pyromod import listen

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID", "23708017"))
API_HASH = os.environ.get("API_HASH", "bb43c2e9f011dea16cad362d56c889b6")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8422932464:AAEhXencYfAL108lGAjEGySXw_9nwvUhm3o")
MONGO_URI = "mongodb+srv://tejuchoudhary0456_db_user:rQiNVxZvKfDAWVzA@teju.1z1ohk0.mongodb.net/?appName=Teju"

bot = Client("SamratBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client['SamratBot']
user_sessions = db['sessions']

# --- CHECK LOGIN STATUS COMMAND ---
@bot.on_message(filters.command(["status", "check", "me"]) & filters.private)
async def check_login(client, message):
    user_id = message.from_user.id
    # डेटाबेस में सर्च करना
    user_data = await user_sessions.find_one({"user_id": user_id})
    
    if user_data and "session" in user_data:
        try:
            # चेक करना कि सेशन वैलिड है या एक्सपायर हो गया
            temp_client = Client("CheckClient", api_id=API_ID, api_hash=API_HASH, session_string=user_data["session"])
            await temp_client.start()
            me = await temp_client.get_me()
            await temp_client.stop()
            
            await message.reply_text(
                f"✅ **Login Status: ACTIVE**\n\n"
                f"👤 **Name:** {me.first_name}\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📱 **Status:** Connect via UserBot",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑 Logout / Reset", callback_data="logout")]])
            )
        except Exception as e:
            await message.reply_text(f"⚠️ **Login Expired:** Session invalid ho gaya hai. Dobara login karein.\nError: `{e}`")
    else:
        await message.reply_text(
            "❌ **Login Status: NOT FOUND**\n\nAapne abhi tak login nahi kiya hai.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔐 Login Now", callback_data="do_login")]])
        )

# --- LOGOUT HANDLER ---
@bot.on_callback_query(filters.regex("logout"))
async def logout_user(client, query):
    await user_sessions.delete_one({"user_id": query.from_user.id})
    await query.message.edit_text("✅ **Logged Out!** Aapka session delete kar diya gaya hai.", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔐 Login Again", callback_data="do_login")]]))

# --- OTP LOGIN LOGIC ---
async def login_with_otp(message):
    try:
        phone_ask = await bot.ask(message.chat.id, "📲 अपना **Mobile Number** भेजें (+91...):", timeout=300)
        phone_number = phone_ask.text.replace(" ", "")
        
        # Unique memory session for each attempt
        temp_client = Client(f"session_{message.from_user.id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await temp_client.connect()
        
        code_data = await temp_client.send_code(phone_number)
        otp_ask = await bot.ask(message.chat.id, "📩 **OTP** भेजें (Format: 1 2 3 4 5):", timeout=300)
        otp_code = otp_ask.text.replace(" ", "")

        try:
            await temp_client.sign_in(phone_number, code_data.phone_code_hash, otp_code)
        except SessionPasswordNeeded:
            pwd_ask = await bot.ask(message.chat.id, "🔐 **2-Step Password** भेजें:", timeout=300)
            await temp_client.check_password(pwd_ask.text)

        string_session = await temp_client.export_session_string()
        
        # DATABASE UPDATE
        await user_sessions.update_one(
            {"user_id": message.from_user.id}, 
            {"$set": {"session": string_session, "phone": phone_number}}, 
            upsert=True
        )
        
        await message.reply_text("✅ **Login Successful!**\nAb aap `/status` check kar sakte hain ya link bhej sakte hain.")
        await temp_client.disconnect()

    except Exception as e:
        await message.reply(f"❌ Error: `{str(e)}`")

# --- CALLBACK FOR LOGIN ---
@bot.on_callback_query(filters.regex("do_login"))
async def cb_login(client, query):
    await query.message.delete()
    await login_with_otp(query.message)

@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("🏆 **𝐒𝐀𝐌𝐑𝐀𝐓 𝟓𝐆 𝐁𝐎𝐓** 🏆\n\nKaise ho? Private content save karne ke liye login karein.", 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Login", callback_data="do_login")],
            [InlineKeyboardButton("🔍 Check Status", callback_data="check_status_cb")]
        ]))

@bot.on_callback_query(filters.regex("check_status_cb"))
async def cb_status(client, query):
    await query.message.delete()
    await check_login(client, query.message)

# --- START BOT ---
async def main():
    await bot.start()
    print("Samrat Bot with Status Check is Live!")
    await idle()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
