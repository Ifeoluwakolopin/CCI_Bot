
import os
import json
import logging
import pymongo
import telegram
from keyboards import *
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater
from dotenv import dotenv_values, load_dotenv
load_dotenv()


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

config = json.load(open("config.json", encoding="utf-8"))

bot = telegram.Bot(os.getenv("BOT_TOKEN"))

PORT = int(os.environ.get('PORT', 5000))

updater = Updater(os.getenv('BOT_TOKEN'), use_context=True)
dp = updater.dispatcher

# Database
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]