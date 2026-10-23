import os
import certifi
import json
import logging
from pymongo import MongoClient
from telegram.ext import Application
from dotenv import dotenv_values, load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

config = json.load(open("config.json", encoding="utf-8"))

application = (
    Application.builder()
    .token(os.getenv("BOT_TOKEN"))
    .concurrent_updates(False)
    .job_queue(None)
    .build()
)
bot = application.bot

PORT = int(os.environ.get("PORT", 5000))

# Database
client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
db = client[os.getenv("DB_NAME")]
