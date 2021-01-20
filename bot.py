import os
import json
import logging
import telegram
import pymongo
from datetime import date
from datetime import datetime as dt
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater
from telegram.ext import Filters
from telegram.ext import CallbackQueryHandler
from telegram.ext import MessageHandler, CommandHandler
from sermons import cci_sermons, t30
from locations import MAP_LOCATIONS, CHURCHES


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

buttons = [
    KeyboardButton("latest sermon"),
    KeyboardButton("get sermon"),
]

buttons1 = [
    KeyboardButton("location"),
    KeyboardButton("membership"),
]

buttons2 = [ 
    KeyboardButton("devotional"),
    KeyboardButton("help"),
    KeyboardButton("map")
]

buttons3 = [
    KeyboardButton("statistics"),
    KeyboardButton("broadcast"),
]

normal_keyboard = [buttons,buttons1, buttons2]
admin_keyboard = [buttons, buttons1, buttons2, buttons3]

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
            "chat_id":chat_id, "date":dt.now(), "admin":False, "mute":False, "first_name":first_name, "last_name":last_name})
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None, "active":True}})
    # send message
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["start"].format(update["message"]["chat"]["first_name"]),
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["start"].format(update["message"]["chat"]["first_name"]),
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
        )


def latest_sermon(update, context):
    """ 
    This gets the most recent sermon
    """
    chat_id = update.effective_chat.id
    sermon = db.temporary.find_one({"latest_sermon":True})
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
    

def helps(update, context):
    """
    This sends a list of available commands for the bot
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["help"], parse_mode="Markdown",
            disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["help"], parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
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
    if not db.devotionals.find_one({"date":str(date.today())}):
        d = t30()
        db.devotionals.insert_one(d)
    else:
        d = db.devotionals.find_one({"date":str(date.today())})
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    context.bot.send_photo(
        chat_id=chat_id, photo=d["image"],
        caption=config["messages"]["t30_caption"].format(d["title"], d["excerpt"].split("\n")[0]),
        reply_markup=InlineKeyboardMarkup(button)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def random(update, context):
    """
    This handles unrecognized commands.
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def stats(update, context):
    """
    This function gives you statistics about the bot
    """
    chat_id = update.effective_chat.id
    total_users = db.users.count_documents({})
    active_users = db.users.count_documents({"active":True})
    mute_users = db.users.count_documents({"mute":True})
    total_sermons = db.sermons.count_documents({})
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["stats"].format(total_users, active_users, mute_users, total_sermons), parse_mode="Markdown"
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def location(update, context):
    """ 
    This gives a list of church locations.
    """
    chat_id = update.effective_chat.id
    ch = ""
    for church in list(CHURCHES.keys()):
        ch += config["messages"]["church"].format(
        church.capitalize(), CHURCHES[church]["name"], CHURCHES[church]["link"]
        )
        ch += "\n\n"

    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["find_church"].format(ch),
        parse_mode="Markdown", disable_web_page_preview="True"
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def mem_school(update, context):
    chat_id = update.effective_chat.id
    button = [[InlineKeyboardButton("Register", url="http://bit.ly/ccimemschool")]]
    context.bot.send_photo(
        chat_id=chat_id, photo=open("membership.jpg", "rb"),
        caption=config["messages"]["membership"], reply_markup=InlineKeyboardMarkup(button)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})


bc_btns = [[
    KeyboardButton("text"),
    KeyboardButton("video"),
    KeyboardButton("photo")],
    [
        KeyboardButton("animation"),
        KeyboardButton("usage")
    ]
]

def broadcast(update, context):
    """
    This function allows for an admin personnel send broadcast
    to all users
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["broadcast"],
            reply_markup = ReplyKeyboardMarkup(bc_btns, resize_keyboard=True)
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def bc_help(update, context):
    """
    This function sends instruction on how to use broadcasts
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc_help"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def bc_text(update, context):
    """
    This function sends text as broadcast
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("message")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"bc_text"}})

def bc_photo(update, context):
    """
    This function sends photo as broadcast
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("photo")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"bc_photo"}})

def bc_video(update, context):
    """
    This function sends video as broadcast.
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("video")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"bc_video"}})

def bc_animation(update, context):
    """
    This function sends animation as broadcast
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("animation")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"bc_animation"}})

def done(update, context):
    """
    This function helps you cancel any existing action
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["done"],
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["done"],
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def menu(update, context):
    """
    This restores the default keyboard.
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["menu"],
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["menu"],
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def cancel(update, context):
    """
    This function helps you cancel any existing action
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cancel"],
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cancel"],
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

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
    """
    This sets the user's mute status to false
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["unmute"]
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"mute":False}})

def map_loc(update, context):
    """
    This handles requests for map locations.
    """
    chat_id = update.effective_chat.id
    context.bot.send_photo(
        chat_id=chat_id, photo=open("MAP.jpg", "rb"),
        caption=config["messages"]["map"],
    )
    buttons = [[InlineKeyboardButton(i.capitalize(), callback_data="map="+i)] for i in list(MAP_LOCATIONS.keys())]
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["location"],
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"map"}})
    
def notify_new_sermon(chat_id, sermons):
    try:
        buttons = [[InlineKeyboardButton(i, callback_data="s="+i.split("–")[2])] for i in sermons]
    except:
        buttons = [[InlineKeyboardButton(i, callback_data="s="+i)] for i in sermons]
    user = db.users.find_one({"chat_id":chat_id})
    try:
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["new_sermon"].format(user["first_name"]),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except:
        db.users.update_one({"chat_id":chat_id}, {"$set":{"active":False}})

def handle_commands(update, context):
    """
    Handles logic for commands
    """
    title = update.message.text.lower()

    if title == "devotional":
        get_devotional(update, context)
    elif title == "latest sermon":
        latest_sermon(update, context)
    elif title == "get sermon":
        get_sermon(update, context)
    elif title == "help":
        helps(update, context)
    elif title == "statistics":
        stats(update, context)
    elif title == "broadcast":
        broadcast(update, context)
    elif title == "location":
        location(update, context)
    elif title == "membership":
        mem_school(update, context)
    elif title == "usage":
        bc_help(update, context)
    elif title == "text":
        bc_text(update, context)
    elif title == "video":
        bc_video(update, context)
    elif title == "photo":
        bc_photo(update, context)
    elif title == "animation":
        bc_animation(update, context)
    elif title == "map":
        map_loc(update, context)
    elif title == "cancel":
        cancel(update, context)
    else:
        random(update, context)

def echo(update, context):
    """
    Handles actions for messages
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    last_command = user["last_command"]

    if last_command == None:
        handle_commands(update, context)
    elif last_command == "get_sermon":
        title = update.message.text.strip()
        sermons = search_db(title)
        if len(sermons) == 0:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["empty"].format(title)
            )
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
        menu(update, context)
    elif last_command == "bc_text":
        message = update.message.text
        for user in db.users.find({}):
            x = text_send(user["chat_id"], message.format(user["first_name"]))
            if x is None:
                db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"active":False}})
        users = db.users.count_documents({})
        total_delivered = db.users.count_documents({"active": True})
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(total_delivered, users)
        )
        done(update, context)
    elif last_command == "bc_photo":
        photo = update.message.photo[-1].file_id
        caption = update.message.caption
        for user in db.users.find({}):
            x = photo_send(user["chat_id"], photo=photo, caption=caption.format(user["first_name"]))
            if x is None:
                db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"active":False}})
        users = db.users.count_documents({})
        total_delivered = db.users.count_documents({"active": True})
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(total_delivered, users)
        )
        done(update, context)
    elif last_command == "bc_video":
        video = update.message.video.file_id
        caption = update.message.caption
        for user in db.users.find({}):
            x = video_send(user["chat_id"], video=video, caption=caption.format(user["first_name"]))
            if x is None:
                db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"active":False}})
        users = db.users.count_documents({})
        total_delivered = db.users.count_documents({"active": True})
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(total_delivered, users)
        )
        done(update, context)
    elif last_command == "bc_animation":
        animation = update.message.animation.file_id
        caption = update.message.caption
        for user in db.users.find({}):
            x = animation_send(user["chat_id"], animation=animation, caption=caption)
            if x is None:
                db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"active":False}})
        users = db.users.count_documents({})
        total_delivered = db.users.count_documents({"active": True})
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(total_delivered, users)
        )
        done(update, context)
    elif last_command == "map":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["map_feedback"],
            parse_mode="Markdown"
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def location_prompt(chat_id):
    buttons = [
        [InlineKeyboardButton("Lagos - Ikeja", callback_data="loc=Ikeja")],
        [InlineKeyboardButton("Lagos - Lekki", callback_data="loc=Lekki")],
        [InlineKeyboardButton("PortHarcourt", callback_data="loc=PH")],
        [InlineKeyboardButton("Canada", callback_data="loc=Canada")],
        [InlineKeyboardButton("Abuja", callback_data="loc=Abuja")],
        [InlineKeyboardButton("Online Member", callback_data="loc=Online")],
        [InlineKeyboardButton("None", callback_data="loc=None")]]
    user = db.users.find_one({"chat_id":chat_id})
    try:
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["lc"].format(user["first_name"]),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except:
        db.users.update_one({"chat_id":chat_id}, {"$set":{"active":False}})

def birthday_prompt(chat_id):
    buttons = [
        [InlineKeyboardButton("January", callback_data="bd=1"),
        InlineKeyboardButton("February", callback_data="bd=2"),
        InlineKeyboardButton("March", callback_data="bd=3")],
        [InlineKeyboardButton("April", callback_data="bd=4"),
        InlineKeyboardButton("May", callback_data="bd=5"),
        InlineKeyboardButton("June", callback_data="bd=6")],
        [InlineKeyboardButton("July", callback_data="bd=7"),
        InlineKeyboardButton("August", callback_data="bd=8"),
        InlineKeyboardButton("September", callback_data="bd=9")],
        [InlineKeyboardButton("October", callback_data="bd=10"),
        InlineKeyboardButton("November", callback_data="bd=11"),
        InlineKeyboardButton("December", callback_data="bd=12")]]
    #user = db.users.find_one({"chat_id":chat_id})
    try:
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["birthday_prompt"],
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except:
        db.users.update_one({"chat_id":chat_id}, {"$set":{"active":False}})

def cb_handle(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    if q.split("=")[0] == "map":
        if q[4:] in list(MAP_LOCATIONS.keys()):
            buttons = [[InlineKeyboardButton(i.capitalize(), callback_data=q+"="+i)] for i in list(MAP_LOCATIONS[q[4:]].keys())]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["location2"].format(q[4:].capitalize()),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif len(q.split("=")) == 3:
            x = q.split("=")
            towns = set([i["location"] for i in MAP_LOCATIONS[x[1]][x[2]]])
            buttons = [[InlineKeyboardButton(i.capitalize(), callback_data=q+"="+i)] for i in list(towns)]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["location2"].format(x[2].capitalize()),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif len(q.split("=")) == 4:
            x = q.split("=")
            locations = ""
            for loc in MAP_LOCATIONS[x[1]][x[2]]:
                if loc["location"] == x[3]:
                    locations += config["messages"]["location4"].format(
                        loc["name"], loc["contact"]
                    )
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["location3"].format(x[3].capitalize(), locations)
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    elif q.split("=")[0] == "s":
        sermon = search_db(q[2:])[0]
        if sermon["video"] is not None:
            buttons = [[InlineKeyboardButton("Download Sermon", url=sermon["download"])],
                    [InlineKeyboardButton("Watch Video", url=sermon["video"])]]
            context.bot.send_photo(
                chat_id=chat_id, photo=sermon["image"], caption=sermon["title"], reply_markup=InlineKeyboardMarkup(buttons)                )
        else:
            button = [[InlineKeyboardButton("Download Sermon", url=sermon["link"])]]
            context.bot.send_photo(
                chat_id=chat_id, photo=sermon["image"], caption=sermon["title"], reply_markup=InlineKeyboardMarkup(button)
           )
    elif q.split("=")[0] == "loc":
        db.users.update_one({"chat_id":chat_id}, {"$set":{"location":q[4:]}})
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["lc_confirm"].format(q[4:])
        )
    elif q.split("=")[0] == "bd":
        if len(q.split("=")) == 2:
            btns = [[InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(1,11)],
                [InlineKeyboardButton(str(i), callback_data=q+"="+i) for i in range(11,21)],
            [InlineKeyboardButton(str(i), callback_data=q+"="+i) for i in range(21,31)]]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["birthday_prompt"],
                reply_markup=InlineKeyboardMarkup(btns)
            )
        else:
            db.users.update_one({"chat_id":chat_id}, {"$set":{"birthday":q.split("=")[1]+"/"+q.split("=")[2]}})
        

echo_handler = MessageHandler(Filters.all & (~Filters.command), echo)
cb_handler = CallbackQueryHandler(cb_handle)

def main():
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(echo_handler)
    dp.add_handler(cb_handler)

    updater.start_webhook(
        listen="0.0.0.0", port=int(PORT), url_path=config["bot_token"]
    )
    updater.bot.setWebhook('https://secret-sands-37903.herokuapp.com/'+config["bot_token"])
    updater.idle()


if __name__ == '__main__':
    main()