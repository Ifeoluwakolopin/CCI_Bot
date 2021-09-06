from helpers import config, db
from telegram import ReplyKeyboardMarkup
from .keyboards import normal_keyboard, admin_keyboard


def reboot(update, context):
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id":chat_id, "admin":True}):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["reboot_camp"]["about"],
            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)
        )
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["reboot_camp"]["about"],
            reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True)
        )
    db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})