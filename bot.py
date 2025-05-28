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

USERNAME = "shukla89"
PASSWORD = "shukla89"

# Login and create a scraper session
def get_authenticated_session():
    scraper = cloudscraper.create_scraper()
    login_url = "https://nhentai.xxx/login/"
    # Step 1: Get login page and CSRF token
    r = scraper.get(login_url)
    if r.status_code != 200:
        raise Exception("Cannot reach login page")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    token = soup.find("input", {"name":"csrfmiddlewaretoken"})["value"]
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
        "csrfmiddlewaretoken": token,
        "next": "/",
    }
    headers = {
        "Referer": login_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
    }
    # Step 2: Post login form
    resp = scraper.post(login_url, data=login_data, headers=headers)
    if resp.status_code != 200 or "Logout" not in resp.text:
        raise Exception("Login failed")
    return scraper

# Extract .torrent URL from gallery page
def get_torrent_url(scraper, code):
    gallery_url = f"https://nhentai.xxx/g/{code}/"
    r = scraper.get(gallery_url)
    if r.status_code != 200:
        raise Exception("Gallery not found")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    download_btn = soup.find("a", {"class": "btn btn-primary btn-block btn-torrent"})
    if not download_btn:
        raise Exception("Download torrent button not found")
    torrent_url = download_btn["href"]
    if torrent_url.startswith("/"):
        torrent_url = "https://nhentai.xxx" + torrent_url
    return torrent_url

# Download torrent file bytes
def download_torrent(scraper, torrent_url):
    r = scraper.get(torrent_url)
    if r.status_code != 200:
        raise Exception("Failed to download torrent file")
    return r.content

# Use libtorrent to get list of files from torrent bytes
def get_files_from_torrent(torrent_bytes):
    info = lt.torrent_info(lt.bdecode(torrent_bytes))
    files = info.files()
    file_list = []
    for i in range(files.num_files()):
        f = files.file_path(i)
        file_list.append(f)
    return file_list, info

# Download files from torrent using libtorrent session (only metadata to get files URLs)
async def download_images_from_torrent(info, session, temp_dir, status_callback=None):
    params = {
        "save_path": temp_dir,
        "storage_mode": lt.storage_mode_t.storage_mode_allocate,
        "ti": info,
        "paused": False,
        "auto_managed": True,
        "duplicate_is_error": True
    }
    handle = session.add_torrent(params)
    print("Downloading torrent metadata and files...")

    while not handle.has_metadata():
        await asyncio.sleep(1)
    print("Metadata received, starting torrent download")

    # Wait for torrent to finish or timeout (5 minutes)
    start_time = time.time()
    timeout = 300
    while handle.status().state != lt.torrent_status.seeding:
        s = handle.status()
        progress = s.progress * 100
        if status_callback:
            await status_callback(progress)
        if time.time() - start_time > timeout:
            print("Timeout downloading torrent")
            break
        await asyncio.sleep(1)

    print("Torrent download finished or timeout reached")

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


@app.on_inline_query()
async def inline_search(client, inline_query):
    query = inline_query.query.strip()
    if not query:
        await inline_query.answer([], switch_pm_text="Type something to search", switch_pm_parameter="start")
        return

    scraper = cloudscraper.create_scraper()
    search_url = f"https://nhentai.net/search/?q={query.replace(' ', '+')}"
    resp = scraper.get(search_url)
    if resp.status_code != 200:
        await inline_query.answer([], switch_pm_text="Error contacting nhentai", switch_pm_parameter="start")
        return

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    gallery_items = soup.select(".gallery a.cover")
    for i, item in enumerate(gallery_items[:10]):
        title = item.get("title") or "No Title"
        href = item.get("href")
        code = href.strip("/").split("/")[-1]
        img_tag = item.select_one("img")
        thumb = img_tag.get("data-src") or img_tag.get("src")
        if thumb.startswith("//"):
            thumb = "https:" + thumb
        page_url = f"https://nhentai.net/g/{code}/"

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Read Online", url=page_url),
                InlineKeyboardButton("Download PDF", callback_data=f"download:{code}:1")
            ],
            [
                InlineKeyboardButton("◀️ Back", switch_inline_query_current_chat=""),  # Implement actual paging logic if needed
                InlineKeyboardButton("Next ▶️", switch_inline_query_current_chat=query)
            ]
        ])

        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Code: {code}",
                thumb_url=thumb,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n🔗 [Read Online]({page_url})\n`Code:` {code}",
                    # Use link_preview_options instead of disable_web_page_preview as warning suggests
                    link_preview_options={}
                ),
                reply_markup=buttons
            )
        )

    await inline_query.answer(results, cache_time=1)


#-------------------------------
async def search_nhentai(query):
    url = f"https://nhentai.net/search/?q={query.replace(' ', '+')}"
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

        page_url = f"https://nhentai.net/g/{code}/"

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
    base_url = f"https://nhentai.net/g/{code}/"
    headers = {"Referer": "https://nhentai.net"}

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