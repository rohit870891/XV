#rohit_1888


from aiohttp import web
import asyncio
import pyromod.listen
from pyrogram import Client
from pyrogram.types import InputMediaPhoto
from pyrogram.handlers import MessageHandler
from pyrogram import filters
from collections import defaultdict
import asyncio
from pyrogram.enums import ParseMode
import sys
import pytz
from datetime import datetime
#rohit_1888 on Tg
from config import *
from database import *

import logging


routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("Rohit")

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app


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
        self.LOGGER(__name__).info(f"Bot Running..!\n\nCreated by \nhttps://t.me/weebs_support")

        self.set_parse_mode(ParseMode.HTML)
        self.username = usr_bot_me.username
        self.LOGGER(__name__).info(f"Bot Running..! Made by @Rohit_1888")   

        # Start Web Server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()


        try: await self.send_message(OWNER_ID, text = f"<b><blockquote> Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @Codeflix_Bots</blockquote></b>")
        except: pass

    async def stop(self, *args):
        await super().stop()
        self.LOGGER(__name__).info("Bot stopped.")

    def run(self):
        """Run the bot."""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        self.LOGGER(__name__).info("Bot is now running. Thanks to @rohit_1888")
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.LOGGER(__name__).info("Shutting down...")
        finally:
            loop.run_until_complete(self.stop())


if __name__ == "__main__":
    Bot().run()


@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    id = message.from_user.id

    await message.reply_photo(
        photo=START_PIC,
        caption=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup
        # message_effect_id=5104841245755180586  
    )

    return



media_groups = defaultdict(list)

@Bot.on_message(filters.private & filters.media_group)
async def handle_album(client, message):
    media_groups[message.media_group_id].append(message)

    # Delay briefly to wait for all messages in the group
    await asyncio.sleep(1.5)

    messages = media_groups.pop(message.media_group_id, [])
    media = []

    for msg in sorted(messages, key=lambda m: m.message_id):
        caption = msg.caption or ""
        new_caption = f"@Javpostr\n\n{caption}" if caption else "@Javpostr"
        if len(media) == 0:
            # Only first media in group can have caption
            media.append(InputMediaPhoto(media=msg.photo.file_id, caption=new_caption))
        else:
            media.append(InputMediaPhoto(media=msg.photo.file_id))

    if media:
        await message.reply_media_group(media=media)