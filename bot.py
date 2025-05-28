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
import aiohttp
from bs4 import BeautifulSoup
from PIL import Image
from pyrogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# Custom config and database imports
from config import *
from database import *

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
async def inline_search(client: Client, inline_query):
    query = inline_query.query.strip()

    if not query:
        await inline_query.answer([], switch_pm_text="Type something to search", switch_pm_parameter="start")
        return

    # Example logic for nhentai search (replace with actual scraper/API)
    results = await search_nhentai(query)  # <-- You implement this function

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


async def download_manga_as_pdf(code, progress_callback=None):
    base_url = f"https://nhentai.net/g/{code}/"
    folder = f"nhentai_{code}"
    os.makedirs(folder, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    thumbnails = soup.select(".thumb-container img")

    images = []
    for i, img in enumerate(thumbnails):
        src = img.get("data-src") or img.get("src")
        src = src.replace("t.jpg", ".jpg").replace("t.png", ".png")
        if src.startswith("//"):
            src = "https:" + src

        filename = os.path.join(folder, f"{i+1:03}.jpg")
        await download_image(session, src, filename)

        if progress_callback:
            await progress_callback(i + 1, len(thumbnails), "Downloading")

        images.append(filename)

    # Convert to PDF
    image_objs = [Image.open(img).convert("RGB") for img in images]
    pdf_path = f"{folder}.pdf"
    image_objs[0].save(pdf_path, save_all=True, append_images=image_objs[1:])

    # Cleanup
    for img in images:
        os.remove(img)
    os.rmdir(folder)

    return pdf_path


@app.on_callback_query(filters.regex(r"^download_(\d+)$"))
async def handle_download_button(client: Client, callback_query):
    code = callback_query.matches[0].group(1)
    chat_id = callback_query.message.chat.id
    msg = await callback_query.message.reply(f"📥 Starting download for `{code}`...", quote=True)

    async def progress(current, total, stage):
        percent = int((current / total) * 100)
        await msg.edit(f"{stage}... {percent}%")

    try:
        pdf_path = await download_manga_as_pdf(code, progress)
        await msg.edit("📤 Uploading PDF...")
        await client.send_document(chat_id, document=pdf_path, caption=f"📖 Manga: {code}")
    except Exception as e:
        await msg.edit(f"❌ Failed: {e}")
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

#-------------------------------------------#
@app.on_message(filters.command("update") & filters.user(ADMINS))
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