from datetime import datetime

from telegram import ReplyKeyboardMarkup
from chat.models import Message
from keyboards import *
from helpers import *

## HELPER FUNCTIONS
# (1) 
def get_active_requests():
    requests = db.counseling_requests.find({"active":True, "status":"pending"}).sort("created", 1)
    return requests

def set_request_inactive(request_id:str):
    db.counseling_requests.update_one({"request_message_id":request_id}, {"$set":{"active":False}})

def set_request_status(request_id:str, status:str):
    db.counseling_requests.update_one({"request_message_id":request_id}, {"$set":{"status":status}})

def get_top_five_requests():
    all_requests = get_active_requests()
    top_five = all_requests[0:5]
    return top_five

# function to displays all active requests to pastors : button
def show_active_requests(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({'chat_id':chat_id, 'role':'pastor'})
    if user:
        top_five_requests = get_top_five_requests()
        if top_five_requests.count() == 0:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["active_requests_none"]
            )
        else:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["active_requests"]
            )
            for request in top_five_requests:
                if request["note"]:
                    msg = request["note"]
                else:
                    msg = " "
                context.bot.send_message(
                    chat_id=chat_id, 
                    text=config["messages"]["active_request"].format(
                        request["name"], 
                        request["email"], 
                        request["phone"],
                        request["topic"],
                        msg
                    ), reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("Start Conversation", callback_data="conv="+str(request["request_message_id"]))]
                        ], 
                        resize_keyboard=True
                    )
                )
    else:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})


# FIXME: fix this function
def notify_pastors(update, context):
    pastors = db.users.find({"role":"pastor"})
    for pastor in pastors:
        context.bot.send_message(
            chat_id=pastor["chat_id"], text=config["messages"]["active_request_notify"]
        )
        top_five_requests = get_top_five_requests()
        for request in top_five_requests:
            if request["note"]:
                msg = request["note"]
            else:
                msg = " "
            context.bot.send_message(
                chat_id=pastor["chat_id"], text=config["messages"]["active_request"].format(
                    request["name"], request["email"], request["phone"], msg
                ), reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Start Conversation", 
                    callback_data="conv="+str(request["request_message_id"]))]], resize_keyboard=True
                    )
                )

def handle_initial_conversation_cb(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    req = db.counseling_requests.find_one({"request_message_id":int(q_head[1])})
    if req["status"] == "pending":
        set_request_status(req["request_message_id"], "ongoing")
        pastor = db.users.find_one({"chat_id":chat_id})
        ## notify pastor that conversation has started
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_start"].format(req["name"])
        )
        ## notify user that conversation has started
        context.bot.send_message(
            chat_id=req["chat_id"], text=config["messages"]["conversation_start_user"].format(pastor["first_name"])
        )
        ## set pastor_id as counselor_id for request
        db.counseling_requests.update_one({"request_message_id":req["request_message_id"]}, {"$set":{"counselor_chat_id":chat_id}})
        ## set user status as in-conversation with pastor
        db.users.update_one({"chat_id":req["chat_id"]}, {"$set":{"last_command":"in-conversation-with="+str(chat_id)+"=pastor="+str(req["request_message_id"])}})
        ## set pastor status as in-conversation with user
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"in-conversation-with="+str(req["chat_id"])+"=user="+str(req["request_message_id"])}})
        ## start conversation
        start_conversation(chat_id, req)
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_already_started"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})


def send_message_handler(msg, to):
    ## Send message to the other user.
    if msg.text:
        bot.send_message(
            chat_id=to, 
            text=msg.text
        )
        return msg.text
    elif msg.photo:
        bot.send_photo(
            chat_id=to, photo=msg.photo[-1].file_id, 
            caption=msg.caption or " ",
        )
        return "photo="+msg.photo[-1].file_id
    elif msg.voice:
        bot.send_voice(
            chat_id=to, voice=msg.voice.file_id, 
            caption=msg.caption or " ",
        )
        return "video="+msg.voice.file_id
    elif msg.video:
        bot.send_video(
            chat_id=to, video=msg.video.file_id, 
            caption=msg.caption or " ",
        )
        return msg.video.file_id
    elif msg.animation:
        bot.send_animation(
            chat_id=to, animation=msg.animation.file_id, 
            caption=msg.caption or " ",
        )
        return "animation="+msg.animation.file_id


def conversation_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    send_to = user["last_command"].split("=")
    msg = update.message

    message_value = send_message_handler(msg, int(send_to[1]))

    message = {
        "message":message_value,
        "created":datetime.now(),
        "from":chat_id,
        "to":int(send_to[1]),
    }

    ## Update conversation object in database.
    if send_to[2] == "pastor":
        update_conversation(message, int(send_to[1]), chat_id)
    else:
        update_conversation(message, chat_id, int(send_to[1]))


def end_conversation_prompt(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    send_to = user["last_command"].split("=")

    role = send_to[2]
    
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["conversation_end_prompt"].format(role),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Yes", callback_data="end_conv=yes="+str(chat_id)+"="+send_to[1]+"="+role),
            InlineKeyboardButton("No", callback_data="end_conv=no="+str(chat_id)+"="+send_to[1]+"="+role)
        ]], resize_keyboard=True)
    )
def set_conversation_status(counselor_id, user_id, active):
    db.conversations.update_one({"counselor_id":counselor_id, "user_id":user_id}, {"$set":{"active":active}})


def end_conversation_cb_handler(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    user = db.users.find_one({"chat_id":chat_id})
    
    # TODO: Checking for the role might cause error [confirm]
    if user["role"]=="pastor":
        keyboard1, keyboard2 = pastor_keyboard, normal_keyboard
        pastor_id = chat_id
        user_id = int(q_head[3])
    else:
        keyboard1, keyboard2 = normal_keyboard, pastor_keyboard
        user_id = chat_id
        pastor_id = int(q_head[3])


    if q_head[1] == "yes":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_end_confirm"],
            reply_markup=ReplyKeyboardMarkup(keyboard1, resize_keyboard=True)
        )
        context.bot.send_message(
            chat_id=int(q_head[3]), text=config["messages"]["conversation_end_notify"].format(
                q_head[4]
            ), reply_markup=ReplyKeyboardMarkup(keyboard2, resize_keyboard=True)
        )
        # update counseling_request status to completed
        set_request_status(int(user["last_command"].split("=")[-1]), "completed")
        # update conversation status to completed
        set_conversation_status(user_id, pastor_id, False)

        # update user last_command to None
        db.users.update_many({"chat_id": {"$in": [chat_id, int(q_head[3])]}},
            {"$set":{"last_command":None}},
        )
        # Ask user to provide feedback on their conversation.
        request_counseling_feedback_from_user(user_id, pastor_id)
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_end_cancel"]
        )


def start_conversation(chat_id, counseling_request):
    db.conversations.insert_one({
        "counselor_id":chat_id,
        "user_id":counseling_request["chat_id"],
        "messages":[],
        "created":datetime.now(),
        "from":counseling_request["request_message_id"],
        "last_updated":datetime.now(),
        "active":True,
    })

## TODO: Check how this works without upsert.
def update_conversation(msg, counselor_id, user_id):
    db.conversations.update_one({
        "counselor_id":counselor_id,
        "user_id":user_id,
        "active":True
    }, {
        "$push":{
            "messages":msg
        }, 
        "$set":{
            "last_updated":datetime.now()
        }
    })

def request_counseling_feedback_from_user(user_chat_id, pastor_chat_id):
    pastor_name = db.users.find_one({"chat_id":pastor_chat_id})["first_name"]
    bot.send_message(
        chat_id=user_chat_id, text=config["messages"]["counseling_feedback_prompt"].format(pastor_name),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("1", callback_data="counseling_feedback=1="+str(user_chat_id)+"="+str(pastor_chat_id)),
            InlineKeyboardButton("2", callback_data="counseling_feedback=2="+str(user_chat_id)+"="+str(pastor_chat_id)),
            InlineKeyboardButton("3", callback_data="counseling_feedback=3="+str(user_chat_id)+"="+str(pastor_chat_id)),
            InlineKeyboardButton("4", callback_data="counseling_feedback=4="+str(user_chat_id)+"="+str(pastor_chat_id)),
            InlineKeyboardButton("5", callback_data="counseling_feedback=5="+str(user_chat_id)+"="+str(pastor_chat_id)),
        ]], resize_keyboard=True)
    )

def handle_counseling_feedback_cb(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    db.conversations.update_one({
        "counselor_id":int(q_head[3]),
        "user_id":int(q_head[2]),
    }, {
        "$set":{
            "rating":int(q_head[1])
        }
    })

    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["counseling_feedback_thanks"]
    )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})


# TODO: create a function to get calendly link and send
def create_calendly_link():
    pass