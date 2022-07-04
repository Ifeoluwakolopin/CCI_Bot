from keyboards import *
from helpers import *

# (1) 
def get_active_requests():
    requests = db.counseling_requests.find({"active":True, "status":"pending"}).sort("created", 1)
    return requests

def set_request_active(request_id:str):
    db.counseling_requests.update_one({"request_id":request_id}, {"$set":{"active":False}})

def set_request_status(request_id:str, status:str):
    db.counseling_requests.update_one({"request_id":request_id}, {"$set":{"status":status}})

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
            ), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Start Conversation", callback_data="conv="+str(request["request_message_id"]))]], resize_keyboard=True)
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    

def handle_initial_conversation_cb(update, context):
    pass