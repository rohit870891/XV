import os
from os import environ,getenv
import logging
from logging.handlers import RotatingFileHandler

#rohit_1888 on Tg
#--------------------------------------------
#Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "8154426339:AAG5XssGYWsJFnzA_p4YOXmyugt1EH_8ySc")
APP_ID = int(os.environ.get("APP_ID", "22469064")) #Your API ID from my.telegram.org
API_HASH = os.environ.get("API_HASH", "c05481978a217fdb11fa6774b15cba32") #Your API Hash from my.telegram.org
#--------------------------------------------

OWNER = os.environ.get("OWNER", "sewxiy") # Owner username without @
OWNER_ID = int(os.environ.get("OWNER_ID", "7328629001")) # Owner id
#--------------------------------------------
PORT = os.environ.get("PORT", "8001")
#--------------------------------------------
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://YatoPro:ProYato@cluster0.zeaqrcy.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DATABASE_NAME", "Cluooo")

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))
#--------------------------------------------
START_PIC = os.environ.get("START_PIC", "https://telegra.ph/file/ec17880d61180d3312d6a.jpg")

#--------------------------------------------
#--------------------------------------------
START_MSG = os.environ.get("START_MESSAGE", "<b>ʜᴇʟʟᴏ {first}\n\n<blockquote> ɪ ᴀᴍ ᴘᴏsᴛ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ʙᴏᴛ.</blockquote></b>")