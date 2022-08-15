from datetime import date
from datetime import datetime as dt
from chat.counselor_handlers import end_conversation_prompt
from helpers import *
from scrapers import WebScrapers
from keyboards import *
from locations import MAP_LOCATIONS, CHURCH_LOCATIONS
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

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
            "chat_id":chat_id, "date":dt.now(),
            "admin":False,
            "mute":False,
            "first_name":first_name,
            "last_name":last_name,
            "last_command":None,
            "active":True,
            "role":"user"
        })
    else:
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None, "active":True}})
    # checks if user is admin and return the appropriate keyboard
    keyboard = validate_user_keyboard(chat_id)
    # send welcome message
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["start"].format(update["message"]["chat"]["first_name"]),
        parse_mode="Markdown", disable_web_page_preview="True",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    location_prompt(chat_id)
    birthday_prompt(chat_id)

# Broadcast Functions
def bc_animation(update, context):
    """
    This function sends animation as broadcast
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id, 'admin':True})
    if user:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("animation")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":user["last_command"]+"+bc_animation"}})

def bc_help(update, context):
    """
    This function sends instruction on how to use broadcasts
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id, 'admin':True})
    if user:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc_help"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":user["last_command"]+"+bc_help"}})

def bc_photo(update, context):
    """
    This function sends photo as broadcast
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id, 'admin':True})
    if user:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("photo")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":user["last_command"]+"+bc_photo"}})

def bc_text(update, context):
    """
    This function sends text as broadcast
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id, 'admin':True})
    if user:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("message")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":user["last_command"]+"+bc_text"}})

def bc_video(update, context):
    """
    This function sends video as broadcast.
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id, 'admin':True})
    if user:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["bc"].format("video")
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":user["last_command"]+"+bc_video"}})


def blog_posts(update, context):
    chat_id = update.effective_chat.id
    button = [[InlineKeyboardButton("Read blog posts", url="https://ccing.org/blogs/")]]
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["blog_posts"], reply_markup=InlineKeyboardMarkup(button)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def broadcast(update, context):
    """
    This function allows for an admin personnel send broadcast
    to all users
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({'chat_id':chat_id, 'admin':True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["broadcast"],
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("Send to all users", callback_data="bc=all")]
                ,[InlineKeyboardButton("Send to specific users", callback_data="bc=specific")]],
            )
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    else:
        unknown(update, context)

def campuses(update, context):
    """ 
    This gives a list of church campuses.
    """
    chat_id = update.effective_chat.id
    ch = ""
    for church in list(CHURCH_LOCATIONS.keys()):
        ch += config["messages"]["church"].format(
        church.capitalize(), CHURCH_LOCATIONS[church]["name"], CHURCH_LOCATIONS[church]["link"]
        )
        ch += "\n\n"

    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["find_church"].format(ch),
        parse_mode="Markdown", disable_web_page_preview="True"
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def cancel(update, context):
    """
    This function helps you cancel any existing action
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id})

    try:
        if user["last_command"].startswith("in-conversation-with"):
            end_conversation_prompt(update, context)
        else:
            keyboard = validate_user_keyboard(chat_id)
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["cancel"],
                parse_mode="Markdown", disable_web_page_preview="True",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    except:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cancel"],
            parse_mode="Markdown", disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def done(update, context):
    """
    This function helps you finish an existing action.
    """
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["done"],
        parse_mode="Markdown", disable_web_page_preview="True",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def feedback(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["feedback"],
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Technical Issue", callback_data="feedback=technical")],
            [InlineKeyboardButton("Suggestion", callback_data="feedback=suggestion")],
            [InlineKeyboardButton("Other", callback_data="feedback=other")]
        ],resize_keyboard=True
        )
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def feedback_cb_handler(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")

    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["feedback_handler"],
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"feedback="+q_head[1]}})

def get_sermon(update, context):
    """ 
    This gets a particular sermon user wants
    """
    chat_id = update.effective_chat.id
    buttons = [
       [InlineKeyboardButton("Yes, find by title", callback_data="get-sermon=yes")],
       [InlineKeyboardButton("No, looking for a topic/date", callback_data="get-sermon=no")]
    ]
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["get_sermon"], reply_markup=InlineKeyboardMarkup(buttons)
    )

def get_devotional(update, context):
    """
    This get the devotional for the particular day
    """
    chat_id = update.effective_chat.id
    if not db.devotionals.find_one({"date":str(date.today())}):
        d = WebScrapers.t30()
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

def helps(update, context):
    """
    This sends a list of available commands for the bot
    """
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["help"], parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

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


def map_loc(update, context):
    """
    This handles requests for map locations.
    """
    chat_id = update.effective_chat.id
    context.bot.send_photo(
        chat_id=chat_id, photo=open("img/MAP.jpg", "rb"),
        caption=config["messages"]["map"],
    )
    buttons = [[InlineKeyboardButton(i.capitalize(), callback_data="map="+i)] for i in list(MAP_LOCATIONS.keys())]
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["location"],
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"map"}})

def menu(update, context):
    """
    This restores the default keyboard.
    """
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["menu"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def membership_school(update, context):
    chat_id = update.effective_chat.id
    button = [[InlineKeyboardButton("Register", url="https://ccing.org/membership-class/")]]
    context.bot.send_photo(
        chat_id=chat_id, photo=open("img/membership.jpg", "rb"),
        caption=config["messages"]["membership"], reply_markup=InlineKeyboardMarkup(button)
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

def notify_new_sermon(chat_id, sermons):
    try:
        buttons = [[InlineKeyboardButton(i, callback_data="s="+i.split("-")[2])] for i in sermons]
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
   
def unknown(update, context):
    """
    This handles unrecognized commands.
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["unknown"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def reboot_about(update, context):
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["reboot_camp"]["about"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def stats(update, context):
    """
    This function gives you statistics about the bot
    """
    chat_id = update.effective_chat.id

    if db.users.find_one({'chat_id':chat_id, 'admin':True}):

        total_users = db.users.count_documents({})
        active_users = db.users.count_documents({"active":True})
        mute_users = db.users.count_documents({"mute":True})
        total_sermons = db.sermons.count_documents({})
        location_based_stats = ""
        birthdays = db.users.count_documents({"birthday":{"$exists":True}})
        today = dt.today()
        x = str(today.month)+'-'+str(today.day)
        todays_birthdays = db.users.count_documents({"birthday":x})

        for loc in db.users.distinct("location"):
            loc_count = db.users.count_documents({"location":loc})
            location_based_stats += loc + " users: " + str(loc_count)
            location_based_stats += "\n"
        
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["stats"].format(total_users, active_users, 
                mute_users, total_sermons,
                location_based_stats, birthdays,
                todays_birthdays), parse_mode="Markdown"
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    else:
        unknown(update, context)
