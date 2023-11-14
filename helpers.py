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


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

config = json.load(open("config.json", encoding="utf-8"))

bot = telegram.Bot(os.getenv("BOT_TOKEN"))

PORT = int(os.environ.get("PORT", 5000))

updater = Updater(os.getenv("BOT_TOKEN"), use_context=True)
dp = updater.dispatcher

# Database
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]


def search_db_title(title) -> list:
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


def location_prompt(chat_id) -> None:
    """
    This functions takes in a chat id, and sends a message
    to request for the user's physical church location.

    Keyword arguments:
    chat_id -- identifies a specific user
    Return: None
    """

    user = db.users.find_one({"chat_id": chat_id})
    try:
        bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc"].format(user["first_name"]),
            reply_markup=InlineKeyboardMarkup(location_buttons),
            resize_keyboard=True,
        )
    except:
        db.users.update_one({"chat_id": chat_id}, {"$set": {"active": False}})


def birthday_prompt(chat_id):
    """
    This functions takes in a chat id, and gets the birthdate
    of a particular user

    Keyword arguments:
    chat_id -- identifies a specific user
    Return: None
    """
    user = db.users.find_one({"chat_id": chat_id})
    try:
        bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["birthday_prompt"].format(user["first_name"]),
            reply_markup=InlineKeyboardMarkup(month_buttons),
        )
    except:
        db.users.update_one({"chat_id": chat_id}, {"$set": {"active": False}})


def validate_user_keyboard(chat_id) -> list:
    """
    This takes in a user id and returns the right keyboard for the user.

    Keyword arguments:
    chat_id -- user's telegram chat_id
    Return: returns correct keyboard for user
    """
    user = db.users.find_one({"chat_id": chat_id})
    if user["admin"] == True:
        return admin_keyboard
    elif user["role"] == "pastor":
        return pastor_keyboard
    else:
        return normal_keyboard


class MessageHelper:
    @staticmethod
    def send_text(chat_id, message):
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

    @staticmethod
    def send_photo(chat_id, photo, caption=""):
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
            bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            return True
        except:
            return None

    @staticmethod
    def send_animation(chat_id, animation, caption=""):
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
            bot.send_animation(chat_id=chat_id, animation=animation, caption=caption)
            return True
        except:
            return None

    @staticmethod
    def send_video(chat_id, video, caption=""):
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
            bot.send_video(chat_id=chat_id, video=video, caption=caption)
            return True
        except:
            return None


class BroadcastHandlers:
    @staticmethod
    def text(users, message):
        for user in users:
            x = MessageHelper.send_text(
                user["chat_id"], message.format(user["first_name"])
            )
            if x is None:
                db.users.update_one(
                    {"chat_id": user["chat_id"]}, {"$set": {"active": False}}
                )

    @staticmethod
    def photo(users, photo, caption=""):
        for user in users:
            x = MessageHelper.send_photo(
                user["chat_id"], photo, caption.format(user["first_name"])
            )
            if x is None:
                db.users.update_one(
                    {"chat_id": user["chat_id"]}, {"$set": {"active": False}}
                )

    @staticmethod
    def animation(users, animation, caption=""):
        for user in users:
            x = MessageHelper.send_animation(
                user["chat_id"], animation, caption.format(user["first_name"])
            )
            if x is None:
                db.users.update_one(
                    {"chat_id": user["chat_id"]}, {"$set": {"active": False}}
                )

    @staticmethod
    def video(users, video, caption=""):
        for user in users:
            x = MessageHelper.send_video(
                user["chat_id"], video, caption.format(user["first_name"])
            )
            if x is None:
                db.users.update_one(
                    {"chat_id": user["chat_id"]}, {"$set": {"active": False}}
                )
