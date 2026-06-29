import logging
import os

import certifi
import telegram
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram.ext import Updater

from .logging_config import configure_logging
from .settings import load_config

load_dotenv()

configure_logging()
logger = logging.getLogger(__name__)

config = load_config()

bot = telegram.Bot(os.getenv("BOT_TOKEN"))

PORT = int(os.environ.get("PORT", 5000))

updater = Updater(os.getenv("BOT_TOKEN"), use_context=True)
dp = updater.dispatcher

# Database
client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
db = client[os.getenv("DB_NAME")]
