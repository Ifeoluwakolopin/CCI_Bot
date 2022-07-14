from datetime import datetime
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
    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["active_requests"]
    )
    top_five_requests = get_top_five_requests()
    for request in top_five_requests:
        if request["note"]:
            msg = request["note"]
        else:
            msg = " "
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["active_request"].format(
                request["name"], request["email"], request["phone"], msg
            ), reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Start Conversation", 
                callback_data="conv="+str(request["request_message_id"]))]], resize_keyboard=True
                )
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    
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
        db.users.update_one({"chat_id":req["chat_id"]}, {"$set":{"status":"in-conversation-with="+str(chat_id)+"=pastor"}})
        ## set pastor status as in-conversation with user
        db.users.update_one({"chat_id":chat_id}, {"$set":{"status":"in-conversation-with="+str(req["chat_id"])+"=user"}})
        ## start conversation
        start_conversation(req)
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_already_started"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})

def conversation_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id":chat_id})
    send_to = user["status"].split("=")
    msg = update.message

    ## Send message to the other user.

    message = {
        "message":msg.text,
        "created":datetime.now(),
        "from":chat_id,
        "to":send_to,
    }
    ## Update conversation object in database.
    if send_to[2] == "pastor":
        update_conversation(message, send_to[1], chat_id)
    else:
        update_conversation(message, chat_id, send_to[1])

    


def start_conversation(counseling_request):
    db.conversations.insert_one({
        "counselor_id":counseling_request["counselor_chat_id"],
        "user_id":counseling_request["chat_id"],
        "messages":[],
        "created":datetime.now(),
        "from":counseling_request,
        "last_updated":datetime.now()
    })

def update_conversation(msg, counselor_id, user_id):
    db.conversations.update_one({
        "counselor_id":counselor_id,
        "user_id":user_id
    }, {
        "$push":{
            "messages":msg
        }, 
        "$set":{
            "last_updated":datetime.now()
        }
    })