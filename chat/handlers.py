from datetime import datetime
from commands import unknown
from telegram import KeyboardButton, ReplyKeyboardMarkup
from keyboards import *
from helpers import *

config = json.load(open("config.json", encoding="utf-8"))

# (1) Provides reply for initial 'get counsel' command.
def get_counsel(update, context):
    chat_id = update.effective_chat.id
    ## to be implemented
    ## Change ReplyKeyboardMarkup to InlineKeyboardMarkup with categories
    ## This should also be implemented in callback handler.
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["counseling_start"],
        reply_markup=ReplyKeyboardMarkup(categories_keyboard),
        resize_keyboard=True
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"get_counsel"}})

# (2) Handles getting the user the right topics for their request
# Also provides suggestion to speak to a pastor.
def handle_get_counsel(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    topic = update.message.text.strip().lower()
    ## to be implemented
    ## add InlineKeyboard buttons with suggested topics.
    if topic in config["counseling_topics"]:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counseling_topic_reply"].format(
                config["counseling_topics"][topic])
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counseling_topic_reply"].format(
                config["counseling_topics"]["default"].format(topic)),
            reply_markup=ReplyKeyboardMarkup(categories_keyboard, resize_keyboard=True)
        )
    # adds topic to database
    add_topic_to_db(topic)
    # Prompts user to speak to a Pastor.
    counselor_request(update, context)

def add_topic_to_db(topic:str):
    if not db.counseling_topics.find_one({"topic":topic}):
        db.counseling_topics.insert_one({"topic":topic, "count":1})
    else:
        db.counseling_topics.update_one({"topic":topic}, {"$inc":{"count":1}})
    
def get_topics_from_db():
    topics = db.counseling_topics.find()
    return [topic["topic"] for topic in topics]

# (3) Provides prompt for user to request to speak to a pastor.
def counselor_request(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["counselor_request"],
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("Yes"), KeyboardButton("No")]],
            resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"counselor_request"}})

# (4) Handles user reply to prompt to speak to a pastor.
def handle_counselor_request(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    counselor_request = update.message.text.strip().lower()

    if user["admin"]:
        btn = admin_keyboard
    else:
        btn = normal_keyboard

    if counselor_request == "yes":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_yes"],
            reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True)
            )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"counselor_request_yes"}})
    elif counselor_request == "no":
        # to be implemented
        # add buttons containing new set of topics
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_no"],
            reply_markup=ReplyKeyboardMarkup(categories_keyboard,
                resize_keyboard=True)
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"get_counsel"}})
    else:
        unknown(update, context)

# (5) Handles user positive reply to prompt to speak to a pastor.
def handle_counselor_request_yes(update, context):
    chat_id = update.effective_chat.id
    message = update.message
    try:

        contact_info = message.text.split("\n")
        name = contact_info[0].strip()
        email = contact_info[1].strip()
        phone = contact_info[2].strip()
        message_id = message.message_id
        
        # temporarily add request to db queue
        add_request_to_queue({
            "created":datetime.now(),
            "chat_id":chat_id,
            "name":name,
            "email":email,
            "phone":phone,
            "request_message_id":message_id,
            "note":None
        })

        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_contact_info_confirm"].format(name, email, phone),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Yes, this is correct", callback_data="cr=yes="+str(message_id))],
                [InlineKeyboardButton("No, I want to make a change", callback_data="cr=no="+str(message_id))]
                ], resize_keyboard=True)
            )
    except:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_invalid_info"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"counselor_request_yes"}})


def add_request_to_queue(counseling_request:dict):
    db.counseling_requests.insert_one({
        "created":counseling_request["created"],
        "name":counseling_request["name"],
        "email": counseling_request["email"],
        "phone":counseling_request["phone"],
        "chat_id":counseling_request["chat_id"],
        "request_message_id":counseling_request["request_message_id"],
        "active":False,
        "note":counseling_request["note"]
    })

def get_active_requests():
    requests = db.counseling_requests.find({"active":True}).sort({"created":1})
    return requests

def set_request_inactive(request_id:str):
    db.counseling_requests.update_one({"request_id":request_id}, {"$set":{"active":False}})