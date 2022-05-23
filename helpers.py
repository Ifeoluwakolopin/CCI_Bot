import os
import json
import logging
import pymongo
import telegram
from telegram.ext import Updater

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO, filename="status.log")
logger = logging.getLogger(__name__)

config = json.load(open("config.json", encoding="utf-8"))

bot = telegram.Bot(config["bot_token"])

PORT = int(os.environ.get('PORT', 5000))

updater = Updater(config["bot_token"], use_context=True)
dp = updater.dispatcher

# Database
client = pymongo.MongoClient(config["db"]["client"])
db = client[config["db"]["name"]]

def search_db_title(title)-> list:
    """
    This takes in a string and searches a mongodb collection
    if the title is in the database.
    
    Keyword arguments:
    title -- string containing words to be searched.
    Return: list of words containing title
    """
    sermons = db.sermons.find({})
    result = []
    for sermon in sermons:
        if title.lower() in sermon["title"].lower():
            result.append(sermon)

    return result

def text_send(chat_id, message):
    """
    This takes in a user's id and a message string. It sends the
    associated user the message via the Telegram Bot API
    
    Keyword arguments:
    chat_id -- identifies a specific user
    message -- str: input message to be sent

    Return: None or True
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
    This takes in an ID, photo and caption. It sends the associated
    user the photo with the given caption via the Telegram Bot API
    
    Keyword arguments:
    chat_id -- identifies a specific user
    photo -- str: link or path to a picture
    caption -- str: text to associate with the picture

    Return: None or True
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
    This takes in an ID, animation and caption. It sends the associated
    user the animation with the given caption via the Telegram Bot API
    
    Keyword arguments:
    chat_id -- identifies a specific user
    animation -- str: link or path to the animation
    caption -- str: text to associate with the animation

    Return: None or True
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
    This takes in an ID, video and caption. It sends the associated
    user the photo with the given caption via the Telegram Bot API
    
    Keyword arguments:
    chat_id -- identifies a specific user
    video -- str: link or path to the video
    caption -- str: text to associate with the video

    Return: None or True
    """
    try:
        bot.send_video(
            chat_id=chat_id, video=video, caption=caption
        )
        return True
    except:
        return None