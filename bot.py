from aiohttp import web
import asyncio, os, re
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import subprocess, sys
from urllib.parse import quote
import cloudscraper

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
        [InlineKeyboardButton("🔎 sᴇᴀʀᴄʜ ᴘᴏʀɴ", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("💻 ᴄᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/rohit_1888")]
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
async def inline_search(client, inline_query):
    query = inline_query.query.strip()
    page = int(inline_query.offset) if inline_query.offset else 1

    results = await search_xvideos(query or None, page)
    next_offset = str(page + 1) if len(results) == 10 else ""

    if not results:
        results.append(
            InlineQueryResultArticle(
                title="No results found",
                description="Try a different keyword",
                input_message_content=InputTextMessageContent("No results found.")
            )
        )

    await inline_query.answer(results, cache_time=1, is_personal=True, next_offset=next_offset)

async def search_xvideos(query=None, page=1):

    results = []
    base_url = "https://www.xvideos.com"
    search_url = f"{base_url}/?k={query.replace(' ', '+')}&p={page - 1}" if query else f"{base_url}/{page - 1}"

#/new/{page - 1}"

    print(f"[DEBUG] Fetching: {search_url}")
    scraper = cloudscraper.create_scraper()

    try:
        html = scraper.get(search_url).text
    except Exception as e:
        print("[ERROR] Failed to fetch page:", e)
        return []

    soup = BeautifulSoup(html, "html.parser")
    video_blocks = soup.select("div.thumb-block")

    if not video_blocks:
        print("[DEBUG] No videos found")
        return []

    print(f"[DEBUG] Found {len(video_blocks)} video items")

    for block in video_blocks[:10]:
        a = block.find("a", href=True)
        if not a:
            continue

        href = a["href"]
        code = href.split("/")[-1].split("_")[0]

        # Title
        title_tag = block.select_one("p.title") or block.select_one("a.title")
        title = title_tag.text.strip() if title_tag else f"Video {code}"

        # Duration
        duration_tag = block.select_one("span.duration")
        duration = duration_tag.text.strip() if duration_tag else "Unknown"

        # Rating (as title attribute from .rating)
        rating_tag = block.select_one("div.rating")
        rating = rating_tag.get("title", "").strip() if rating_tag else "Unrated"

        # Thumbnail
        img = block.find("img")
        thumb = img.get("data-src") if img and img.has_attr("data-src") else img.get("src") if img else ""
        if thumb.startswith("//"):
            thumb = "https:" + thumb
        elif not thumb.startswith("http"):
            thumb = "https://telegra.ph/file/3d2f07a1675f7c90fda94.jpg"  # fallback

        description = f"⏱ {duration} | ⭐ {rating}"

        results.append(
            InlineQueryResultArticle(
                title=title[:64],
                description=description,
                thumb_url=thumb,
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"<b>{title}</b>\n"
                        f"⏱ Duration: {duration}\n"
                        f"⭐ Rating: {rating}\n"
                        f"🔗 <a href='https://www.xvideos.com{href}'>Watch on xVideos</a>\n\n"
                        f"<code>Video ID:</code> {code}"
                    ),
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download Video", callback_data=f"xdown_{code[:50]}")]
                ])
            )
        )

    return results

# ---------------- PAGE DOWNLOADER ---------------- #
async def extract_xvideos_download_links(video_id):
    url = f"https://www.xvideos.com/video{video_id}/"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception("Failed to fetch video page.")
            html = await resp.text()

    qualities = {}

    # Match different quality URLs
    matches = {
        "240p": re.search(r'setVideoUrlLow"\s*,\s*"([^"]+)"', html),
        "480p": re.search(r'setVideoUrl"\s*,\s*"([^"]+)"', html),
        "720p": re.search(r'setVideoUrlHigh"\s*,\s*"([^"]+)"', html),
        "1080p": re.search(r'setVideoHLS"\s*,\s*"([^"]+)"', html)  # May be m3u8
    }

    for quality, match in matches.items():
        if match:
            qualities[quality] = match.group(1)

    if not qualities:
        raise Exception("No downloadable qualities found.")

    return qualities

# ---------------- CALLBACK HANDLER ---------------- #

# Helper to reply or send fallback message
async def safe_send_text(client, msg, user_id, text):
    if msg:
        return await msg.edit(text)
    else:
        return await client.send_message(user_id, text)


@app.on_callback_query(filters.regex(r"^xdown_(\d+)$"))
async def handle_xvideos_download(client: Client, callback: CallbackQuery):
    code = callback.matches[0].group(1)
    msg = await callback.message.reply("🔍 Fetching available video qualities...")

    try:
        qualities = await extract_xvideos_download_links(code)

        buttons = [
            [InlineKeyboardButton(f"⬇️ {q}", callback_data=f"xvqual_{code}_{q}")]
            for q in sorted(qualities.keys())
        ]
        buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="close")])

        await msg.edit(
            "Select the video quality you want to download:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")

@app.on_callback_query(filters.regex(r"^xvqual_(\d+)_(\w+)$"))
async def handle_xvideos_quality_choice(client: Client, callback: CallbackQuery):
    code, quality = callback.matches[0].group(1), callback.matches[0].group(2)
    msg = await callback.message.edit(f"📥 Preparing {quality} video...")

    try:
        qualities = await extract_xvideos_download_links(code)
        url = qualities.get(quality)

        if not url:
            raise Exception(f"{quality} quality not available.")

        filename = f"xvideo_{code}_{quality}.mp4"

        # Download video
        await msg.edit("⬇️ Downloading video...")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception("❌ Failed to download video.")
                with open(filename, "wb") as f:
                    while True:
                        chunk = await resp.content.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)

        await msg.edit("📤 Uploading to Telegram...")

        await client.send_video(
            chat_id=callback.from_user.id,
            video=filename,
            caption=f"✅ Downloaded {quality} video.\n🔗 <a href='https://www.xvideos.com/video{code}'>Watch on xVideos</a>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit(f"❌ Error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

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