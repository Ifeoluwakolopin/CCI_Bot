import jobs
from datetime import date
from datetime import datetime as dt
from helpers import *
from locations import MAP_LOCATIONS, CHURCHES
from sermons import t30
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from keyboards import normal_keyboard, admin_keyboard
from reboot_camp import *

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
    location_prompt(chat_id)
    birthday_prompt(chat_id)

# Broadcast Functions
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

def campuses(update, context):
    """ 
    This gives a list of church campuses.
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

def done(update, context):
    """
    This function helps you finish an existing action.
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

def mem_school(update, context):
    chat_id = update.effective_chat.id
    button = [[InlineKeyboardButton("Register", url="http://bit.ly/ccimemschool")]]
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


def newsletter(update, context):
    chat_id = update.effective_chat.id
    button = [[InlineKeyboardButton("Subscribe", url="https://ccing.us8.list-manage.com/subscribe?u=03f72aceeaf186b2d6c32d37e&id=52c44cb044")]]
    context.bot.send_photo(
        chat_id=chat_id, photo=open("img/newsletter.jpg", "rb"),
        caption=config["messages"]["newsletter"], reply_markup=InlineKeyboardMarkup(button)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})


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
    location_based_stats = ""
    bdays = db.users.count_documents({"birthday":{"$exists":True}})
    today = dt.today()
    x = str(today.month)+'-'+str(today.day)
    today_bday = db.users.count_documents({"birthday":x})

    for loc in db.users.distinct("location"):
        loc_count = db.users.count_documents({"location":loc})
        location_based_stats += loc + " users: " + str(loc_count)
        location_based_stats += "\n"
        
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["stats"].format(total_users, active_users, 
        mute_users, total_sermons,
        location_based_stats, bdays,
        today_bday), parse_mode="Markdown"
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

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
    elif title == "reboot camp":
        reboot_about(update, context)
    else:
        random(update, context)

def message_handle(update, context):
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
        [InlineKeyboardButton("Lagos - Ikeja", callback_data="loc=Ikeja"),
        InlineKeyboardButton("Lagos - Lekki", callback_data="loc=Lekki")],
        [InlineKeyboardButton("Ibadan", callback_data="loc=Ibadan"),
        InlineKeyboardButton("PortHarcourt", callback_data="loc=PH")],
        [InlineKeyboardButton("Canada", callback_data="loc=Canada"),
        InlineKeyboardButton("Abuja", callback_data="loc=Abuja")],
        [InlineKeyboardButton("United Kingdom(UK)", callback_data="loc=UK")],
        [InlineKeyboardButton("Online Member", callback_data="loc=Online"),
        InlineKeyboardButton("None", callback_data="loc=None")]]
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
    user = db.users.find_one({"chat_id":chat_id})
    try:
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["birthday_prompt"].format(user["first_name"]),
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
            btns = [[InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(1,8)],
                [InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(8,15)],
                [InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(15,22)],
                [InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(22,29)]]
            
            if q.split("=")[1] in ["9", "4", "6", "11"]:
                btns.append([InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(29,31)])
            elif q.split("=")[1] == "2":
                btns.append([InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(29,30)])
            else:
                btns.append([InlineKeyboardButton(str(i), callback_data=q+"="+str(i)) for i in range(29,32)])
                
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["birthday_day"],
                reply_markup=InlineKeyboardMarkup(btns)
            )
        else:
            db.users.update_one({"chat_id":chat_id}, {"$set":{"birthday":q.split("=")[1]+"-"+q.split("=")[2]}})
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["birthday_confirm"].format(q.split("=")[1]+"/"+q.split("=")[2])
            )
        
msg_handler = MessageHandler(Filters.all & (~Filters.command), message_handle)
cb_handler = CallbackQueryHandler(cb_handle)

def main():
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("newsletter", newsletter))
    dp.add_handler(CommandHandler("campuses", campuses))
    dp.add_handler(CommandHandler("membership", mem_school))
    dp.add_handler(msg_handler)
    dp.add_handler(cb_handler)

    updater.start_webhook(
        listen="0.0.0.0", port=int(PORT), url_path=config["bot_token"]
    )
    updater.bot.setWebhook('https://cci-bot.herokuapp.com/'+config["bot_token"])
    updater.idle()


if __name__ == '__main__':
    main()
    jobs.sched.start()
    