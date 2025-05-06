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
        [[InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ 💻", url="https://telegram.dog/rohit_1888")]]
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


media_groups = defaultdict(list)

@Bot.on_message(filters.private & filters.media_group)
async def handle_album(client, message):
    media_groups[message.media_group_id].append(message)
    await asyncio.sleep(1.5)

    messages = [msg for msg in media_groups.pop(message.media_group_id, []) if hasattr(msg, "message_id") and msg.photo]
    if not messages:
        return

    user_id = message.from_user.id
    header = await db.get_header(user_id) or ""
    footer = await db.get_footer(user_id) or ""
    bot_username = await db.get_bot(user_id) or f"@{client.me.username}"

    media = []
    for idx, msg in enumerate(sorted(messages, key=lambda m: m.message_id)):
        if idx == 0:
            if msg.caption:
                # Replace all bot usernames with your bot's username
                updated_caption = re.sub(r"@\w+_bot\b", bot_username, msg.caption, flags=re.IGNORECASE)
                updated_caption = f"{header}\n\n{updated_caption}\n\n{footer}"
            else:
                updated_caption = f"{header}\n\n<b>Your content has been processed successfully:</b>\n{bot_username}\n\n{footer}"

            media.append(InputMediaPhoto(media=msg.photo.file_id, caption=updated_caption, parse_mode=ParseMode.HTML))
        else:
            media.append(InputMediaPhoto(media=msg.photo.file_id))

    await message.reply_media_group(media=media, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Share Link", url=f"https://telegram.me/share/url?url={bot_username}")]
    ]))


@Bot.on_message(filters.private & filters.photo & ~filters.media_group)
async def handle_single_photo(client, message):
    user_id = message.from_user.id
    header = await db.get_header(user_id) or ""
    footer = await db.get_footer(user_id) or ""
    bot_username = await db.get_bot(user_id) or f"@{client.me.username}"

    if message.caption:
        updated_caption = re.sub(r"@\w+_bot\b", bot_username, message.caption, flags=re.IGNORECASE)
        updated_caption = f"{header}\n\n{updated_caption}\n\n{footer}"
    else:
        updated_caption = f"{header}\n\n<b>Your content has been processed successfully:</b>\n{bot_username}\n\n{footer}"

    await message.reply_photo(
        photo=message.photo.file_id,
        caption=updated_caption,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Share Link", url=f"https://telegram.me/share/url?url={bot_username}")]
        ])
    )




# Start bot
if __name__ == "__main__":
    app.run()