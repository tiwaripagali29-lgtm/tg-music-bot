import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import InputAudioStream
from pytgcalls.types.input_stream.quality import HighQualityAudio
import yt_dlp

# Credentials read from Render Environment Variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")

bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_app = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call_py = PyTgCalls(user_app)

def get_audio_stream(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info['url'], info['title']

@bot.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    bot_info = await client.get_me()
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Me To Your Group", 
                url=f"https://t.me/{bot_info.username}?startgroup=true"
            )
        ]
    ])
    await message.reply_text(
        f"👋 **Namaste {message.from_user.first_name}!**\n\n"
        "Main VC Music Bot hoon. Group mein add karein aur `/play [song]` likhein.",
        reply_markup=keyboard
    )

@bot.on_message(filters.command("play") & filters.group)
async def play_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    query = " ".join(message.command[1:])
    if not query:
        await message.reply_text("❌ Gaane ka naam likhein: `/play Song Name`")
        return

    status = await message.reply_text("🔍 Gaana dhoondh raha hoon...")
    try:
        audio_url, title = get_audio_stream(query)
        await status.edit_text(f"🎶 **Playing:** `{title}`")
        await call_py.join_group_call(
            chat_id,
            InputAudioStream(audio_url, HighQualityAudio())
        )
    except Exception as e:
        await status.edit_text(f"⚠️ Error: `{e}`")

@bot.on_message(filters.command("stop") & filters.group)
async def stop_cmd(client: Client, message: Message):
    try:
        await call_py.leave_group_call(message.chat.id)
        await message.reply_text("⏹️ Gaana band kar diya gaya.")
    except Exception:
        await message.reply_text("Bot abhi VC mein nahi hai.")

@call_py.on_stream_end()
async def stream_end_handler(client, update):
    await call_py.leave_group_call(update.chat_id)
    await bot.send_message(update.chat_id, "✅ Gaana khatam ho gaya.")

async def main():
    await user_app.start()
    await bot.start()
    await call_py.start()
    print("Bot aur VC Assistant successfully started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
