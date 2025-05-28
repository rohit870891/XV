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
import io
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





#-------------------------------



#-----------------------

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

        await msg.edit_text("<b><blockquote>✅ Bᴏᴛ ɪs ʀᴇsᴛᴀʀᴛɪɴɢ ɴᴏᴡ...</blockquote></b>")

    except Exception as e:
        await message.reply_text(f"An error occurred: {e}")
        return

    finally:
        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)

# Start bot
if __name__ == "__main__":
    app.run()