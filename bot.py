from aiohttp import web
import asyncio, re, os, sys, time, subprocess
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

import aiohttp
import pyromod.listen
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from pyrogram.types import (
    Message, CallbackQuery, InlineQueryResultArticle,
    InputTextMessageContent, InlineQueryResultPhoto, InlineKeyboardMarkup, InlineKeyboardButton
)

# ---------------- CONFIG ---------------- #
from config import *  # should define: APP_ID, API_HASH, TG_BOT_TOKEN, OWNER_ID, PORT, LOGGER, START_MSG, START_PIC
from database import *  # your database connection file

# ---------------- WEB SERVER ---------------- #
routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Rohit")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# ---------------- BOT ---------------- #
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
        usr_bot_me = await self.get_me()
        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        self.uptime = datetime.now()
        self.LOGGER(__name__).info(f"Bot Running...! @{self.username}")

        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(OWNER_ID, text="<b><blockquote> Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @Codeflix_Bots</blockquote></b>")
        except:
            pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot Stopped.")

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Bot Interrupted.")
        finally:
            loop.run_until_complete(self.stop())

app = Bot()

# ---------------- START ---------------- #
@app.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔎 Search Manga", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("💻 Contact Developer", url="https://t.me/rohit_1888")]
        ]
    )
    await message.reply_photo(
        photo=START_PIC,
        caption=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
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

    # Default to homepage if no search query
    results = await search_nhentai(query or None, page)
    next_offset = str(page + 1) if len(results) == 10 else ""

    await inline_query.answer(results, cache_time=1, is_personal=True, next_offset=next_offset)

# ---------------- SEARCH FUNCTION ---------------- #

async def search_nhentai(query=None, page=1):
    results = []

    if query:
        url = f"https://nhentai.net/search/?q={query.replace(' ', '+')}&page={page}"
    else:
        url = f"https://nhentai.net/?page={page}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return []
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    gallery_items = soup.select(".gallery")

    for item in gallery_items[:10]:
        link = item.select_one("a")["href"]
        code = link.split("/")[2]

        title_tag = item.select_one(".caption")
        title = title_tag.text.strip() if title_tag else f"Code {code}"

        thumb_tag = item.select_one("img")
        thumb = thumb_tag.get("data-src") or thumb_tag.get("src")
        if thumb.startswith("//"):
            thumb = "https:" + thumb

        caption = f"**{title}**\n🔗 [Read Now](https://nhentai.net/g/{code}/)\n\n`Code:` {code}"

        results.append(
            InlineQueryResultPhoto(
                photo_url=thumb,
                thumb_url=thumb,
                caption=caption,
                parse_mode="markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{code}")]
                ])
            )
        )

    return results

# ---------------- PAGE DOWNLOAD HELPER ---------------- #
async def download_page(session, image_url, filename, page_num):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }
    async with session.get(image_url, headers=headers) as img_resp:
        if img_resp.status != 200:
            raise Exception(f"Failed to download page {page_num} (status {img_resp.status})")
        content = await img_resp.read()
        with open(filename, "wb") as f:
            f.write(content)

# ---------------- DOWNLOAD PDF FUNCTION ---------------- #
async def download_manga_as_pdf(code, progress_callback=None):
    api_url = f"https://nhentai.net/api/gallery/{code}"
    folder = f"nhentai_{code}"
    os.makedirs(folder, exist_ok=True)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to get gallery metadata: status {resp.status}")
            data = await resp.json()

        num_pages = len(data["images"]["pages"])
        print(f"Gallery {code} has {num_pages} pages")

        images = []
        ext_map = {"j": "jpg", "p": "png", "g": "gif", "w": "webp"}  # Added webp support

        for i, page in enumerate(data["images"]["pages"]):
            page_num = i + 1
            ext = page.get("t")
            extension = ext_map.get(ext, "jpg")

            image_url = f"https://i.nhentai.net/galleries/{data['media_id']}/{page_num}.{extension}"
            print(f"Downloading page {page_num}: {image_url}")

            filename = os.path.join(folder, f"{page_num:03}.{extension}")
            await download_page(session, image_url, filename, page_num)

            images.append(filename)

            if progress_callback:
                await progress_callback(page_num, num_pages, "Downloading")

    image_objs = [Image.open(img).convert("RGB") for img in images]
    pdf_path = f"{folder}.pdf"
    image_objs[0].save(pdf_path, save_all=True, append_images=image_objs[1:])

    for img in images:
        os.remove(img)
    os.rmdir(folder)

    return pdf_path

# ---------------- CALLBACK HANDLER ---------------- #
@app.on_callback_query(filters.regex(r"^download_(\d+)$"))
async def handle_download_button(client: Client, callback_query):
    code = callback_query.matches[0].group(1)
    pdf_path = None

    try:
        if callback_query.message:
            chat_id = callback_query.message.chat.id
            msg = await callback_query.message.reply(f"📥 Starting download for `{code}`...", quote=True)

            async def progress(current, total, stage):
                percent = int((current / total) * 100)
                await msg.edit(f"{stage}... {percent}%")

        elif callback_query.inline_message_id:
            chat_id = callback_query.from_user.id
            await callback_query.edit_message_text(f"📥 Starting download for `{code}`...")

            async def progress(current, total, stage):
                percent = int((current / total) * 100)
                try:
                    await callback_query.edit_message_text(f"{stage}... {percent}%")
                except Exception:
                    pass

        # Start download
        pdf_path = await download_manga_as_pdf(code, progress)

        if callback_query.message:
            await msg.edit("📤 Uploading PDF...")
            await client.send_document(chat_id, document=pdf_path, caption=f"📖 Manga: {code}")
        else:
            await callback_query.edit_message_text("📤 Uploading PDF...")
            await client.send_document(chat_id, document=pdf_path, caption=f"📖 Manga: {code}")

    except Exception as e:
        error_text = f"❌ Failed: {e}"
        if callback_query.message:
            try:
                await msg.edit(error_text)
            except Exception:
                pass
        else:
            try:
                await callback_query.edit_message_text(error_text)
            except Exception:
                pass
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)


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

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    app.run()