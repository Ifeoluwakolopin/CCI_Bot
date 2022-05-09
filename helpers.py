import os
import json
import logging
import pymongo
import telegram
from telegram.ext import Updater

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

config = json.load(open("config.json", encoding="utf-8"))

bot = telegram.Bot(config["bot_token"])

PORT = int(os.environ.get('PORT', 5000))

updater = Updater(config["bot_token"], use_context=True)
dp = updater.dispatcher

# Database
client = pymongo.MongoClient(config["db"]["client"])
db = client[config["db"]["name"]]

def search_db(title):
    """
    This function queries the db for a particular sermon
    """
    sermons = db.sermons.find({})
    result = []
    for sermon in sermons:
        if title.lower() in sermon["title"].lower():
            result.append(sermon)

    return result

def text_send(chat_id, message):
    """
    This function sends a message to a user
    """
    try:
        bot.send_message(
            chat_id=chat_id, text=message, disable_web_page_preview="True"
        )
        return True
    except:
        return None

def photo_send(chat_id, photo, caption=""):
    """
    This function sends a photo to user with caption
    """
    try:
        bot.send_photo(
            chat_id=chat_id, photo=photo, caption=caption
        )
        return True
    except:
        return None

def animation_send(chat_id, animation, caption=""):
    """
    This function sends an animation to a user with a caption
    """
    try:
        bot.send_animation(
            chat_id=chat_id, animation=animation, caption=caption
        )
        return True
    except:
        return None

def video_send(chat_id, video, caption=""):
    """
    This function sends a video to a user with a caption
    """
    try:
        bot.send_video(
            chat_id=chat_id, video=video, caption=caption
        )
        return True
    except:
        return None