import time
from datetime import datetime
from commands import unknown
from telegram import KeyboardButton, ReplyKeyboardMarkup
from keyboards import *
from helpers import *

config = json.load(open("config.json", encoding="utf-8"))

# (1) Provides reply for initial 'get counsel' command.
def get_counsel(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["counseling_start"],
        reply_markup=ReplyKeyboardMarkup(categories_keyboard, resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"get_counsel"}})

# (2) Handles getting the user the right topics for their request
# Also provides suggestion to speak to a pastor or add a new question.
def handle_get_counsel(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    topic = update.message.text.strip().lower()
    topic_from_db = db.counseling_topics.find_one({"topic":topic})

    if topic_from_db:
        ## TODO: limit this to 5 questions and add a button to see more.
        ## TODO: Populate the database
        ## TODO: Integrate the calendar as the final step. (Google calender).
        faqs = topic_from_db["faqs"]
        buttons = [[InlineKeyboardButton(faq["id"], callback_data="faq="+topic+"="+str(faq["id"]))] for faq in faqs]
        questions = "\n\n".join(["{0}. {1}".format(faq["id"], faq["q"]) for faq in faqs])

        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counseling_topic_reply"].format(
                topic.capitalize(),
                questions
                ),
            reply_markup=InlineKeyboardMarkup(buttons, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counseling_topic_not_found"],
            reply_markup=ReplyKeyboardMarkup(categories_keyboard, resize_keyboard=True)
        )
    # adds topic to database
    add_topic_to_db(topic)
    # Prompts user to speak to a Pastor.
    time.sleep(5)
    ask_question_or_request_counselor(update, context)

def handle_get_faq_callback(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    response = db.counseling_topics.find_one({"topic":q_head[1]})
    answer = response["faqs"][int(q_head[2])-1]["a"].strip()

    context.bot.send_message(
        chat_id=chat_id, text=answer, reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("Ask a new question")], 
            [KeyboardButton("Speak to a Pastor")]
            ], resize_keyboard=True
        )
    )

    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"question_or_counselor_request"}})

def add_topic_to_db(topic:str):
    if not db.counseling_topics.find_one({"topic":topic}):
        db.counseling_topics.insert_one({"topic":topic, "faqs":[], "count":1})
    else:
        db.counseling_topics.update_one({"topic":topic}, {"$inc":{"count":1}})
    
def get_topics_from_db():
    topics = db.counseling_topics.find()
    return [topic["topic"] for topic in topics]

# (3) Provides prompt for user to request to speak to a pastor.
def ask_question_or_request_counselor(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["add_question_or_request_counselor"],
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("Ask a question")], 
            [KeyboardButton("Speak to a Pastor")]
            ], resize_keyboard=True)
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"question_or_counselor_request"}})

# (4) Handles user reply to prompt to speak to a pastor.
def handle_ask_question_or_request_counselor(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    user_request = update.message.text.strip().lower()

    if user["admin"]:
        btn = admin_keyboard
    else:
        btn = normal_keyboard

    if user_request == "speak to a pastor":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_request_yes"],
            reply_markup=ReplyKeyboardMarkup(btn, resize_keyboard=True)
            )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"counselor_request_yes"}})
    elif user_request == "ask a new question":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["ask_question"],
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"ask_counseling_question"}})
    else:
        unknown(update, context)

# (5) Handles user request to speak to a pastor.
def handle_counselor_request_yes(update, context):
    chat_id = update.effective_chat.id
    message = update.message
    try:

        contact_info = message.text.split("\n")
        name = contact_info[0].strip()
        email = contact_info[1].strip() # regex email validation
        phone = contact_info[2].strip() # regex validate phone number
        message_id = message.message_id
        
        # temporarily add request to db queue
        add_request_to_queue({
            "created":datetime.now(),
            "chat_id":chat_id,
            "name":name,
            "email":email,
            "phone":phone,
            "request_message_id":message_id,
            "note":None,  
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

def handle_ask_question(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text.strip().lower()

    
    db.new_questions.insert_one({"chat_id":chat_id, "question":message})
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["ask_question_success"]
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"ask_counseling_question"}})


def add_request_to_queue(counseling_request:dict):
    db.counseling_requests.insert_one({
        "created":counseling_request["created"],
        "name":counseling_request["name"],
        "email": counseling_request["email"],
        "phone":counseling_request["phone"],
        "chat_id":counseling_request["chat_id"],
        "request_message_id":counseling_request["request_message_id"],
        "active":False,
        "note":counseling_request["note"],
        "status":"pending",
        "counselor_chat_id": None
    })