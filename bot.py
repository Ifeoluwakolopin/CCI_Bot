import os
import json
import logging
import telegram
import pymongo
from datetime import datetime as dt
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater
from telegram.ext import Filters
from telegram.ext import MessageHandler, CommandHandler
from sermons import cci_sermons, t30


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

config = json.load(open("config.json"))

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

def send_bc(chat_id, message):
    try:
        bot.send_message(
            chat_id=chat_id, text=message, disable_web_page_preview="True"
        )
        return True
    except:
        return None

def start(update, context):
    """
    This is the response of the bot on startup
    """
    chat_id = update.effective_chat.id
    first_name = str(update["message"]["chat"]["first_name"])
    last_name = str(update["message"]["chat"]["last_name"])
    # add user to database
    if not db.users.find_one({"chat_id":chat_id}):
        db.users.insert_one({
            "chat_id":chat_id, "date":dt.now(), "admin":False, "mute":False, "full_name":first_name, "last_name":last_name})
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None, "active":True}})
    # send message
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["start"].format(update["message"]["chat"]["first_name"]),
        parse_mode="Markdown", disable_web_page_preview="True"
    )

def latest_sermon(update, context):
    """ 
    This gets the most recent sermon
    """
    chat_id = update.effective_chat.id
    sermon = cci_sermons()[0]
    buttons = [[InlineKeyboardButton("Download Sermon", url=sermon["download"])],
        [InlineKeyboardButton("Watch Video", url=sermon["video"])]]
    context.bot.send_photo(
        chat_id=chat_id, photo=sermon["image"], caption=sermon["title"], reply_markup=InlineKeyboardMarkup(buttons)
    )
    try:
        db.sermons.find({"title":sermon["title"]})[0]
    except IndexError:
        db.sermons.insert_one(sermon)
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    

def helps(update, context):
    """
    This sends a list of available commands for the bot
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["help"])
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def menu(update, context):
    """
    This sends a list of available commands for the bot
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["menu"])
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["admin_menu"]
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})


def get_sermon(update, context):
    """ 
    This gets a particular sermon user wants
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["get_sermon"]
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"get_sermon"}})

def get_devotional(update, context):
    """
    This get the devotional for the particular day
    """
    chat_id = update.effective_chat.id
    d = t30()
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    context.bot.send_photo(
        chat_id=chat_id, photo=d["image"], caption=d["title"], reply_markup=InlineKeyboardMarkup(button)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def stats(update, context):
    """
    This function gives you statistics about the bot
    """
    chat_id = update.effective_chat.id
    total_users = db.users.count_documents({})
    total_sermons = db.sermons.count_documents({})
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["stats"].format(total_users, total_sermons), parse_mode="Markdown"
    )

def broadcast(update, context):
    """
    This function allows for an admin personnel send broadcast
    to all users
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["broadcast"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"broadcast"}})

def mute(update, context):
    """
    This set the user's mute status
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["mute"]
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"mute":True}})

def unmute(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["unmute"]
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"mute":False}})


def echo(update, context):
    """
    Handles actions for messages
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    last_command = user["last_command"]

    if last_command == "get_sermon":
        title = update.message.text.strip()
        sermons = search_db(title)
        if len(sermons) == 0:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["empty"].format(title)
            )
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["menu"]
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
        else:
            for sermon in sermons:
                if sermon["video"] is not None:
                    buttons = [[InlineKeyboardButton("Download Sermon", url=sermon["download"])],
                        [InlineKeyboardButton("Watch Video", url=sermon["video"])]]
                    context.bot.send_photo(
                        chat_id=chat_id, photo=sermon["image"], caption=sermon["title"], reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    button = [[InlineKeyboardButton("Download Sermon", url=sermon["link"])]]
                    context.bot.send_photo(
                        chat_id=chat_id, photo=sermon["image"], caption=sermon["title"], reply_markup=InlineKeyboardMarkup(button)
                    )
                    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    elif last_command == "broadcast":
        message = update.message.text
        for user in db.users.find({}):
            x = send_bc(user["chat_id"], message)
            if x is None:
                db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"active":False}})
        users = db.users.count_documents({})
        total_delivered = db.users.count_documents({"active": True})
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(total_delivered, users)
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})




echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)

def main():
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("latest_sermon", latest_sermon))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("help", helps))
    dp.add_handler(CommandHandler("get_devotional", get_devotional))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("get_sermon", get_sermon))
    dp.add_handler(echo_handler)

    updater.start_webhook(
        listen="0.0.0.0", port=int(PORT), url_path=config["bot_token"]
    )
    updater.bot.setWebhook('https://secret-sands-37903.herokuapp.com/'+config["bot_token"])
    updater.idle()


if __name__ == '__main__':
    main()