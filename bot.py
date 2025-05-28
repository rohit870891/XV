from aiohttp import web
import asyncio, re
import pyromod.listen
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, Message
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from collections import defaultdict
from datetime import datetime
import logging
import sys
import pytz
import os
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import tempfile
import asyncio
import aiohttp
import libtorrent as lt
import time
import cloudscraper
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from pyrogram.types import CallbackQuery

# Custom config and database imports
from config import *
from database import *
import subprocess 
import cloudscraper
from bs4 import BeautifulSoup

def get_gallery_title(gallery_id: str) -> str:
    url = f"https://nhentai.xxx/g/{gallery_id}/"
    scraper = cloudscraper.create_scraper()
    res = scraper.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    return soup.select_one('h1.title').text.strip()


def get_gallery_title(gallery_id: str) -> str:
    url = f"https://nhentai.xxx/g/{gallery_id}/"
    scraper = cloudscraper.create_scraper()
    res = scraper.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    return soup.select_one('h1.title').text.strip()

async def download_and_convert(gallery_id: str) -> io.BytesIO:
    url = f"https://i.nhentai.xxx/galleries/{gallery_id}.zip"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            zip_data = await resp.read()
    
    zip_bytes = io.BytesIO(zip_data)
    pdf_bytes = io.BytesIO()
    
    with zipfile.ZipFile(zip_bytes, 'r') as z:
        images = [Image.open(z.open(f)) for f in sorted(z.namelist()) if f.endswith(('.jpg', '.png'))]
        rgb_images = [img.convert("RGB") for img in images]
        rgb_images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=rgb_images[1:])
    
    pdf_bytes.seek(0)
    return pdf_bytes

# Convert all downloaded images to PDF
def convert_images_to_pdf(image_folder, output_pdf_path):
    files = sorted(
        [os.path.join(image_folder, f) for f in os.listdir(image_folder)
         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    )
    images = []
    for f in files:
        img = Image.open(f).convert("RGB")
        images.append(img)
    if not images:
        raise Exception("No images found to convert")
    images[0].save(output_pdf_path, save_all=True, append_images=images[1:])
    return output_pdf_path

# Async Telegram sending helpers
async def send_progress_edit(message, text):
    try:
        await message.edit(text)
    except:
        pass



# Web route setup
routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Rohit")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# Bot Client
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Bot",
            api_hash=API_HASH,
            api_id=APP_ID,
            workers=TG_BOT_WORKERS,
            bot_token=TG_BOT_TOKEN
        )
        self.LOGGER = LOGGER

    async def start(self):
        await super().start()
        usr_bot_me = await self.get_me()
        self.uptime = datetime.now()

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        self.LOGGER(__name__).info(f"Bot Running..! Made by @Rohit_1888")

        # Start web server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(OWNER_ID, text="<b><blockquote> Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @Codeflix_Bots</blockquote></b>")
        except:
            pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @rohit_1888")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())

# Create bot instance
app = Bot()


# Start command
@app.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔎 Sᴇᴀʀᴄʜ Mᴀɴɢᴀ", switch_inline_query_current_chat="")],
            [InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ 💻", url="https://telegram.dog/rohit_1888")]
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

#---------------------


@Client.on_inline_query()
async def handle_inline(client, inline_query):
    query = inline_query.query.strip()
    gallery_id = extract_gallery_id(query)
    if not gallery_id:
        return await inline_query.answer([], switch_pm_text="Invalid Gallery ID", cache_time=1)

    title = get_gallery_title(gallery_id)
    pdf_data = await download_and_convert(gallery_id)

    await inline_query.answer([
        InlineQueryResultDocument(
            title=title,
            document=pdf_data,
            mime_type="application/pdf",
            caption=f"Gallery: {title}\nID: {gallery_id}",
            file_name=f"{title}.pdf",
            input_message_content=InputTextMessageContent(f"📕 {title} — Downloading..."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Next", switch_inline_query_current_chat="next")],
                [InlineKeyboardButton("⬇️ Download", url=f"https://nhentai.xxx/g/{gallery_id}/")]
            ])
        )
    ], cache_time=0)


#-------------------------------
async def search_nhentai(query):
    url = f"https://nhentai.xxx/search/?q={query.replace(' ', '+')}"
    results = []

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return []

            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    gallery_items = soup.select(".gallery")

    for i, item in enumerate(gallery_items[:10]):  # Max 10 results
        link_tag = item.select_one("a")
        if not link_tag or "href" not in link_tag.attrs:
            continue

        href = link_tag["href"]  # e.g., /g/123456/
        code = href.split("/")[2]

        title_tag = item.select_one(".caption")
        title = title_tag.text.strip() if title_tag else f"Code {code}"

        img_tag = item.select_one("img")
        thumb = img_tag.get("data-src") or img_tag.get("src") if img_tag else None
        if thumb and thumb.startswith("//"):
            thumb = "https:" + thumb

        page_url = f"https://nhentai.xxx/g/{code}/"

        button = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{code}")]
        ])

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Code: {code}",
                thumb_url=thumb,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n🔗 [Read Now]({page_url})\n`Code:` {code}",
                    disable_web_page_preview=False
                ),
                reply_markup=button
            )
        )

    return results


async def download_nhentai_as_pdf(code, status_msg, client):
    base_url = f"https://nhentai.xxx/g/{code}/"
    headers = {"Referer": "https://nhentai.xxx"}

    async with aiohttp.ClientSession(headers=headers) as session:
        # Fetch gallery page
        async with session.get(base_url) as resp:
            if resp.status != 200:
                raise Exception(f"Gallery not found. HTTP {resp.status}")
            html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        img_tags = soup.select("#thumbnail-container img")

        if not img_tags:
            raise Exception("No images found.")

        image_urls = []
        for img in img_tags:
            src = img.get("data-src") or img.get("src")
            if src.startswith("//"):
                src = "https:" + src
            image_urls.append(src.replace("t.jpg", ".jpg").replace("t.png", ".png").replace("t.", "."))  # full-size

        total = len(image_urls)
        images = []

        await status_msg.edit(f"📥 Found {total} pages. Downloading images...")

        for i, img_url in enumerate(image_urls, start=1):
            async with session.get(img_url) as img_resp:
                if img_resp.status != 200:
                    raise Exception(f"Image {i} failed")
                img_bytes = await img_resp.read()

            image = Image.open(BytesIO(img_bytes)).convert("RGB")
            images.append(image)

            if i % 5 == 0 or i == total:
                await status_msg.edit(f"📥 Downloading... {i}/{total} pages")

    # Save PDF
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, f"{code}.pdf")
    images[0].save(pdf_path, save_all=True, append_images=images[1:])

    return pdf_path

#-----------------------
@app.on_callback_query()
async def handle_download_button(client, callback_query: CallbackQuery):
    data = callback_query.data
    if not data.startswith("download:"):
        await callback_query.answer()
        return

    _, code, page_str = data.split(":")
    page = int(page_str)

    # Acknowledge callback query without alert popup
    await callback_query.answer(f"Downloading manga code {code} ...", show_alert=False)

    # Edit inline message to show starting status
    try:
        await callback_query.edit_message_text(f"⏳ Preparing to download `{code}`...")
    except Exception:
        # If message can't be edited (e.g. no message), just ignore
        pass

    # Determine user chat id safely
    user_chat_id = None
    if callback_query.message:
        user_chat_id = callback_query.message.chat.id
    else:
        # fallback to sending DM using callback_query.from_user.id
        user_chat_id = callback_query.from_user.id

    try:
        scraper = get_authenticated_session()
        torrent_url = get_torrent_url(scraper, code)
        torrent_bytes = download_torrent(scraper, torrent_url)

        # Save torrent file to temp directory
        temp_dir = tempfile.mkdtemp()
        torrent_path = os.path.join(temp_dir, f"{code}.torrent")
        with open(torrent_path, "wb") as f:
            f.write(torrent_bytes)

        # Load torrent info and setup session
        info = lt.torrent_info(torrent_path)
        ses = lt.session()
        ses.listen_on(6881, 6891)

        async def progress_callback(progress):
            # Progress callback can update inline message text
            try:
                await callback_query.edit_message_text(f"📥 Download progress: {progress:.2f}%")
            except Exception:
                pass  # ignore if can't edit (e.g. no inline message)

        # Download all images via torrent (you implement this)
        await download_images_from_torrent(info, ses, temp_dir, progress_callback)

        # Convert downloaded images to PDF (you implement this)
        pdf_path = os.path.join(temp_dir, f"{code}.pdf")
        convert_images_to_pdf(temp_dir, pdf_path)

        # Edit message to indicate upload
        try:
            await callback_query.edit_message_text("📤 Uploading PDF...")
        except Exception:
            pass

        # Send the PDF file to user private chat
        await client.send_document(user_chat_id, pdf_path, caption=f"Manga `{code}` downloaded as PDF.")

        # Delete the inline message if possible
        if callback_query.message:
            try:
                await callback_query.message.delete()
            except Exception:
                pass

    except Exception as e:
        # Show error message in inline message if possible
        try:
            await callback_query.edit_message_text(f"❌ Failed to download `{code}`:\n`{e}`")
        except Exception:
            # If cannot edit message, send a private message with error instead
            await client.send_message(user_chat_id, f"❌ Failed to download `{code}`:\n`{e}`")

#-------------------------------------------#
@app.on_message(filters.command("update") & filters.user(OWNER_ID))
async def update_bot(client, message):
    #if message.from_user.id not OWNER_ID:
        #return await message.reply_text("You are not authorized to update the bot.")

    try:
        msg = await message.reply_text("<b><blockquote>Pulling the latest updates and restarting the bot...</blockquote></b>")

        # Run git pull
        git_pull = subprocess.run(["git", "pull"], capture_output=True, text=True)

        if git_pull.returncode == 0:
            await msg.edit_text(f"<b><blockquote>Updates pulled successfully:\n\n{git_pull.stdout}</blockquote></b>")
        else:
            await msg.edit_text(f"<b><blockquote>Failed to pull updates:\n\n{git_pull.stderr}</blockquote></b>")
            return

        await asyncio.sleep(3)

        await msg.edit_text("<b><blockquote>✅ Bot is restarting now...</blockquote></b>")

    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
        return

    finally:
        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)

# Start bot
if __name__ == "__main__":
    app.run()