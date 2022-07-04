from keyboards import *
from helpers import *

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
        db.counseling_requests.update_one({"request_id":req["request_id"]}, {"$set":{"counselor_chat_id":chat_id}})

        ## set user status as in-conversation with pastor

        ## set pastor status as in-conversation with user

    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_already_started"]
        )
