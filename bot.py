import os
import asyncio
import urllib.parse

# Python 3.9 / Pyrogram Event Loop Fix
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import aiohttp
from aiohttp import web
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")

bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_app = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call_py = PyTgCalls(user_app)

async def get_audio_stream(query):
    # 1. JioSaavn Direct High-Quality API
    try:
        clean_query = urllib.parse.quote(query)
        saavn_url = f"https://saavn.dev/api/search/songs?query={clean_query}&page=1&limit=1"
        async with aiohttp.ClientSession() as session:
            async with session.get(saavn_url, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    songs = data.get("data", {}).get("results", [])
                    if songs:
                        song = songs[0]
                        title = song.get("name", query)
                        download_urls = song.get("downloadUrl", [])
                        if download_urls:
                            return download_urls[-1].get("url"), title
    except Exception:
        pass

    # 2. SoundCloud fallback
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'scsearch1',
        'noplaylist': True
    }
    def _sc_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"scsearch1:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                return entry['url'], entry.get('title', 'SoundCloud Track')
            elif info and 'url' in info:
                return info['url'], info.get('title', 'SoundCloud Track')
            return None, None

    audio_url, title = await asyncio.to_thread(_sc_extract)
    if audio_url:
        return audio_url, title

    raise Exception("Gaana nahi mila. Kripya doosra naam try karein!")

@bot.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    bot_info = await client.get_me()
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Me To Group/Channel", url=f"https://t.me/{bot_info.username}?startgroup=true")
        ]
    ])
    await message.reply_text(
        f"👋 **Namaste {message.from_user.first_name}!**\n\n"
        "Main VC Music Bot hoon.\n\n"
        "**Group Commands:**\n"
        "• `/play [gaane ka naam]`\n"
        "• `/stop`\n\n"
        "**Channel Commands:**\n"
        "• `/cplay @channelusername [gaane ka naam]`\n"
        "• `/cstop @channelusername`",
        reply_markup=keyboard
    )

# --- Group Commands ---
@bot.on_message(filters.command("play") & filters.group)
async def play_cmd(client: Client, message: Message):
    query = " ".join(message.command[1:])
    if not query:
        await message.reply_text("❌ Gaane ka naam likhein: `/play Kesariya`")
        return

    status = await message.reply_text("🔍 Gaana dhoondh raha hoon...")
    try:
        audio_url, title = await get_audio_stream(query)
        await status.edit_text(f"🎶 **Playing:** `{title}`")
        await call_py.join_group_call(
            message.chat.id,
            AudioPiped(audio_url)
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

# --- Channel Commands ---
@bot.on_message(filters.command("cplay"))
async def cplay_cmd(client: Client, message: Message):
    if len(message.command) < 3:
        await message.reply_text("❌ Sahi format: `/cplay @channelusername GaaneKaNaam`")
        return

    channel_username = message.command[1]
    query = " ".join(message.command[2:])
    status = await message.reply_text("🔍 Channel verify aur gaana search ho raha hai...")
    try:
        chat = await client.get_chat(channel_username)
        audio_url, title = await get_audio_stream(query)
        await status.edit_text(f"🎶 **Playing in Channel:** `{title}`")
        await call_py.join_group_call(
            chat.id,
            AudioPiped(audio_url)
        )
    except Exception as e:
        await status.edit_text(f"⚠️ Error: `{e}`\nCheck karein ki Assistant Channel me Admin hai!")

@bot.on_message(filters.command("cstop"))
async def cstop_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Format: `/cstop @channelusername`")
        return
    channel_username = message.command[1]
    try:
        chat = await client.get_chat(channel_username)
        await call_py.leave_group_call(chat.id)
        await message.reply_text("⏹️ Channel VC band kar diya.")
    except Exception as e:
        await message.reply_text(f"Error: `{e}`")

# Render keep-alive server
async def web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def start_services():
    await user_app.start()
    await bot.start()
    await call_py.start()
    await web_server()
    print("Bot aur VC Assistant successfully started!")
    await idle()

if __name__ == "__main__":
    loop.run_until_complete(start_services())
