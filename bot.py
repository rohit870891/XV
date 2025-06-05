from aiohttp import web
import asyncio, os, re
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import subprocess, sys
import cloudscraper
import aiohttp
import pyromod.listen
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery
)
from pyrogram.enums import ParseMode
from playwright.async_api import async_playwright


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


async def fetch_page_content(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        # Wait for gallery thumbnails to load (adjust selector if needed)
        await page.wait_for_selector(".gallery_preview, .gallery-thumb", timeout=10000)
        content = await page.content()
        await browser.close()
    return content


# ---------------- START COMMAND ---------------- #
@app.on_message(filters.command('start') & filters.private)
async def start_command(_, message: Message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 NHentai", switch_inline_query_current_chat=""),
            InlineKeyboardButton("🦊 HentaiFox", switch_inline_query_current_chat="fox:")
        ],
        [
            InlineKeyboardButton("📚 SimplyHentai", switch_inline_query_current_chat="simply:")
        ],
        [
            InlineKeyboardButton("💻 Contact Developer", url="https://t.me/rohit_1888")
        ]
    ])

    await message.reply_photo(
        photo=START_PIC,
        caption=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name or "",
            username=('@' + message.from_user.username) if message.from_user.username else "",
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=keyboard
    )

# ---------------- INLINE SEARCH ---------------- #
@app.on_inline_query()
async def inline_search(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    page = int(inline_query.offset) if inline_query.offset else 1

    if query.startswith("fox:"):
        results = await search_hentaifox(query[4:], page)
    elif query.startswith("simply:"):
        results = await search_simplyhentai(query[7:], page)
    else:
        results = await search_nhentai(query or None, page)

    next_offset = str(page + 1) if len(results) == 10 else ""
    await inline_query.answer(results, cache_time=1, is_personal=True, next_offset=next_offset)

# ---------------- SEARCH FUNCTIONS ---------------- #
async def search_nhentai(query=None, page=1):
    results = []
    url = f"https://nhentai.net/search/?q={query.replace(' ', '+')}&page={page}" if query else f"https://nhentai.net/?page={page}"

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
        title = item.select_one(".caption").text.strip() if item.select_one(".caption") else f"Code {code}"
        thumb = item.select_one("img").get("data-src") or item.select_one("img").get("src")
        if thumb.startswith("//"):
            thumb = "https:" + thumb

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Code: {code}",
                thumb_url=thumb,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n🔗 [Read Now](https://nhentai.net/g/{code}/)\n\n`Code:` {code}",
                    disable_web_page_preview=False
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download PDF", callback_data=f"nhentai_{code}")]
                ])
            )
        )
    return results

async def search_hentaifox(query, page=1):
    results = []
    search_url = f"https://hentaifox.com/search/?q={query}&page={page}"
    html = await fetch_page_content(search_url)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".gallery_preview")

    for item in items[:10]:
        a_tag = item.find("a")
        if not a_tag:
            continue
        link = a_tag["href"]
        code = link.strip("/").split("/")[-1]
        title = item.select_one(".caption").text.strip() if item.select_one(".caption") else f"Gallery {code}"
        thumb = item.select_one("img")["data-src"] or item.select_one("img")["src"]
        if thumb.startswith("//"):
            thumb = "https:" + thumb

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Code: {code}",
                thumb_url=thumb,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n🔗 [Read Now](https://hentaifox.com/gallery/{code}/)\n\n`Code:` {code}",
                    disable_web_page_preview=True
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download PDF", callback_data=f"fox_{code}")]
                ])
            )
        )
    return results

async def search_simplyhentai(query, page=1):
    results = []
    search_url = f"https://www.simply-hentai.com/search?query={query}&page={page}"
    html = await fetch_page_content(search_url)
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".gallery-thumb")

    for item in items[:10]:
        a_tag = item.find("a")
        if not a_tag:
            continue
        link = a_tag["href"]
        code = link.strip("/").split("/")[-1]
        title = a_tag.get("title", f"Gallery {code}")
        thumb = item.select_one("img")["src"]
        if thumb.startswith("//"):
            thumb = "https:" + thumb

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Code: {code}",
                thumb_url=thumb,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n🔗 [Read Now](https://www.simply-hentai.com{link})\n\n`Code:` {code}",
                    disable_web_page_preview=True
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📥 Download PDF", callback_data=f"simply_{code}")]
                ])
            )
        )
    return results

# ---------------- DOWNLOAD FUNCTIONS ---------------- #
async def download_page(session, url, filename):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            raise Exception(f"Failed to download: {url}")
        with open(filename, "wb") as f:
            f.write(await resp.read())

async def download_manga_as_pdf(code, source, progress_callback=None):
    folder = f"{source}_{code}"
    os.makedirs(folder, exist_ok=True)
    image_paths = []

    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession() as session:
        if source == "nhentai":
            api_url = f"https://nhentai.net/api/gallery/{code}"
            async with session.get(api_url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception("Gallery not found.")
                data = await resp.json()

            num_pages = len(data["images"]["pages"])
            ext_map = {"j": "jpg", "p": "png", "g": "gif", "w": "webp"}
            media_id = data["media_id"]

            for i, page in enumerate(data["images"]["pages"], start=1):
                ext = ext_map.get(page["t"], "jpg")
                url = f"https://i.nhentai.net/galleries/{media_id}/{i}.{ext}"
                path = os.path.join(folder, f"{i:03}.{ext}")
                await download_page(session, url, path)
                image_paths.append(path)
                if progress_callback:
                    await progress_callback(i, num_pages, "Downloading")

        elif source == "fox":
            gallery_url = f"https://hentaifox.com/gallery/{code}/"
            async with session.get(gallery_url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception("Gallery not found.")
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            thumbs = soup.select(".gallery_thumb img")
            num_pages = len(thumbs)

            for i, img in enumerate(thumbs, start=1):
                thumb_url = img["data-src"]
                if thumb_url.startswith("//"):
                    thumb_url = "https:" + thumb_url
                path = os.path.join(folder, f"{i:03}.jpg")
                await download_page(session, thumb_url, path)
                image_paths.append(path)
                if progress_callback:
                    await progress_callback(i, num_pages, "Downloading")

        elif source == "simply":
            gallery_url = f"https://www.simply-hentai.com/gallery/{code}/"
            async with session.get(gallery_url, headers=headers) as resp:
                if resp.status != 200:
                    raise Exception("Gallery not found.")
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            thumbs = soup.select(".gallery-thumb img")
            num_pages = len(thumbs)

            for i, img in enumerate(thumbs, start=1):
                thumb_url = img["src"]
                if thumb_url.startswith("//"):
                    thumb_url = "https:" + thumb_url
                path = os.path.join(folder, f"{i:03}.jpg")
                await download_page(session, thumb_url, path)
                image_paths.append(path)
                if progress_callback:
                    await progress_callback(i, num_pages, "Downloading")

        else:
            raise Exception("Unsupported source.")

    # Generate0



# ---------------- CALLBACK HANDLER ---------------- #

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
import os
from reportlab.pdfgen import canvas
from PIL import Image
import aiofiles
import shutil

@app.on_callback_query(filters.regex(r"^(nhentai|fox|simply)_(\d+)$"))
async def handle_callback(client: Client, callback: CallbackQuery):
    source, code = callback.data.split("_", 1)
    chat_id = callback.from_user.id

    # Inline result fallback
    reply_message = callback.message or callback.inline_message_id
    progress_msg = None
    folder = f"{source}_{code}"
    pdf_path = f"{folder}.pdf"

    try:
        # Start message (fallback for inline result)
        if callback.message:
            progress_msg = await callback.message.reply("📥 Download started...")
        else:
            await callback.answer("📥 Download started...")

        # Progress function
        async def progress(current, total, stage):
            pct = int((current / total) * 100)
            txt = f"{stage}... {pct}% ({current}/{total})"
            if progress_msg:
                try:
                    await progress_msg.edit_text(txt)
                except:
                    pass

        # Download images using your function
        await download_manga_as_pdf(code, source, progress)

        # Convert to PDF
        files = sorted(os.listdir(folder))
        image_paths = [os.path.join(folder, f) for f in files if f.endswith(('.jpg', '.png', '.jpeg', '.webp'))]
        if not image_paths:
            raise Exception("❌ No images downloaded.")

        # Create PDF using PIL
        image_list = [Image.open(img).convert("RGB") for img in image_paths]
        first_img = image_list[0]
        if len(image_list) > 1:
            first_img.save(pdf_path, save_all=True, append_images=image_list[1:])
        else:
            first_img.save(pdf_path)

        if not os.path.exists(pdf_path):
            raise Exception("❌ PDF conversion failed.")

        if progress_msg:
            await progress_msg.edit_text("📤 Uploading PDF...")

        await client.send_document(chat_id, pdf_path, caption=f"📖 Manga: `{code}`", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        if progress_msg:
            await progress_msg.edit_text(f"❌ Error: {str(e)}")
        else:
            await callback.answer("❌ Error occurred.")

    finally:
        # Cleanup
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(folder):
                shutil.rmtree(folder)
        except:
            pass

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
