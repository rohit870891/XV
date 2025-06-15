from aiohttp import web
import asyncio, os, re
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import subprocess, sys

import aiohttp
import pyromod.listen
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import (
    Message, CallbackQuery, InlineQueryResultArticle,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
)

# ---------------- CONFIG ---------------- #
from config import *  # Define APP_ID, API_HASH, TG_BOT_TOKEN, OWNER_ID, PORT, LOGGER, START_MSG, START_PIC
from database import *  # Your database file

# ---------------- WEB SERVER ---------------- #
routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_handler(request):
    return web.json_response("Rohit")

async def web_server():
    web_app = web.Application(client_max_size=9000000000)
    web_app.add_routes(routes)
    return web_app

# ---------------- BOT INIT ---------------- #
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="nhentaiBot",
            api_id=APP_ID,
            api_hash=API_HASH,
            bot_token=TG_BOT_TOKEN,
            workers=4
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.set_parse_mode(ParseMode.HTML)
        self.username = me.username
        self.uptime = datetime.now()
        self.LOGGER(__name__).info(f"Bot Running...! @{self.username}")

        runner = web.AppRunner(await web_server())
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()

        try:
            await self.send_message(OWNER_ID, "<b><blockquote>Bot restarted.</blockquote></b>")
        except:
            pass

    async def stop(self):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Interrupted.")
        finally:
            loop.run_until_complete(self.stop())

app = Bot()

# ---------------- START HANDLER ---------------- #
@app.on_message(filters.command('start') & filters.private)
async def start_command(_, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search Manga", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("💻 Contact Developer", url="https://t.me/rohit_1888")]
    ])
    await message.reply_photo(
        photo=START_PIC,
        caption=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=('@' + message.from_user.username) if message.from_user.username else None,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=keyboard
    )

# ---------------- INLINE SEARCH ---------------- #
@app.on_inline_query()
async def inline_search(client: Client, inline_query):
    query = inline_query.query.strip()
    page = int(inline_query.offset) if inline_query.offset else 1

    results = await search_xvideos(query or None, page)
    next_offset = str(page + 1) if len(results) == 10 else ""
    await inline_query.answer(results, cache_time=1, is_personal=True, next_offset=next_offset)

async def search_xvideos(query=None, page=1):
    from urllib.parse import quote
    query_url = f"https://www.xvideos.com/?k={quote(query)}&p={page}" if query else f"https://www.xvideos.com/new/{page}"
    results = []
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(query_url) as resp:
            if resp.status != 200:
                return []
            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.thumb-block")[:10]

    for item in items:
        a = item.select_one("a")
        link = a["href"]
        title = a["title"]
        code = link.strip("/").split("/")[-1]
        thumb = item.select_one("img")
        thumb_url = thumb.get("data-src") or thumb.get("src")
        if thumb_url.startswith("//"):
            thumb_url = "https:" + thumb_url

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Video ID: {code}",
                thumb_url=thumb_url,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n🔗 [Watch Now](https://www.xvideos.com{link})\n\n`Video ID:` {code}",
                    disable_web_page_preview=False
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Video", callback_data=f"xdown_{code}")]
                ])
            )
        )
    return results

# ---------------- PAGE DOWNLOADER ---------------- #
async def extract_xvideos_download_link(video_id):
    url = f"https://www.xvideos.com/video{video_id}/"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception("Failed to fetch video page.")
            html = await resp.text()

    match = re.search(r'"setVideoUrlHigh"\s*,\s*"([^"]+)"', html)
    if not match:
        raise Exception("Download link not found.")

    return match.group(1)

# ---------------- CALLBACK HANDLER ---------------- #
@app.on_callback_query(filters.regex(r"^xdown_(\w+)$"))
async def handle_xvideos_download(client: Client, callback: CallbackQuery):
    video_id = callback.matches[0].group(1)
    msg = await callback.message.reply("📥 Getting video link...")

    try:
        dlink = await extract_xvideos_download_link(video_id)
        await msg.edit("📥 Downloading video...")

        async with aiohttp.ClientSession() as session:
            async with session.get(dlink) as resp:
                if resp.status != 200:
                    raise Exception("Download failed.")

                filename = f"xv_{video_id}.mp4"
                with open(filename, "wb") as f:
                    f.write(await resp.read())

        await msg.edit("📤 Uploading video...")
        await client.send_video(
            callback.message.chat.id,
            video=filename,
            caption=f"🎥 xVideos ID: {video_id}"
        )

    except Exception as e:
        await msg.edit(f"❌ Error: {e}")
    finally:
        if os.path.exists(f"xv_{video_id}.mp4"):
            os.remove(f"xv_{video_id}.mp4")

# ---------------- UPDATE CMD ---------------- #


@app.on_message(filters.command("update") & filters.user(OWNER_ID))
async def update_bot(client, message):
    msg = await message.reply_text("🔄 Pulling updates from GitHub...")
    try:
        pull = subprocess.run(["git", "pull"], capture_output=True, text=True)
        if pull.returncode == 0:
            await msg.edit(f"✅ Updated:\n<pre>{pull.stdout}</pre>")
        else:
            await msg.edit(f"❌ Git error:\n<pre>{pull.stderr}</pre>")
            return
        await asyncio.sleep(2)
        await msg.edit("♻️ Restarting bot...")
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await msg.edit(f"⚠️ Error: {e}")



# ---------------- RUN BOT ---------------- #
if __name__ == "__main__":
    app.run()