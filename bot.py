import os
from chat.counselor_handlers import *
from commands import *
from helpers import *
from chat.handlers import *
from locations import MAP_LOCATIONS
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from dotenv import dotenv_values,load_dotenv
load_dotenv()


def handle_message_commands(update, context):
    """
    This matches incoming commands form users to their respective functions

    Keyword arguments:
    update -- metadata containing information on incoming request.
        passed as argument for command handles
    context -- passed as argument for command handles

    Return: None
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
    elif title == "map":
        map_loc(update, context)
    elif title == "cancel":
        cancel(update, context)
    elif title == "reboot camp":
        reboot_about(update, context)
    elif title == "counseling":
        get_counsel(update, context)
    else:
        unknown(update, context)

def handle_message_response(update, context):
    """
    Handles actions for messages
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    last_command = user["last_command"]

    if last_command == None:
        handle_message_commands(update, context)
    elif last_command == "get_sermon":
        title = update.message.text.strip()
        sermons = search_db_title(title)
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
    elif last_command.startswith("bc_to"):

        msg = update.message.text

        if msg is not None and msg.lower() in ["how to broadcast", "text", "video", "photo", "animation"]:
            title = msg.lower()
            if title == "how to broadcast":
                bc_help(update, context)
            elif title == "text":
                bc_text(update, context)
            elif title == "video":
                bc_video(update, context)
            elif title == "photo":
                bc_photo(update, context)
            elif title == "animation":
                bc_animation(update, context)
        else:
            q = last_command.split("+")

            if q[0] == "bc_to_all":
                users = db.users.find({})
            else:
                locations = q[1:-1]
                users = db.users.find({"location": {"$in": locations}})

            bc_type = q[-1]

            if bc_type == "bc_text":
                message = update.message.text
                BroadcastHandlers.text(users, message)
            elif bc_type == "bc_photo":
                photo = update.message.photo[-1].file_id
                caption = update.message.caption or ""
                BroadcastHandlers.photo(users, photo, caption)
            elif bc_type == "bc_video":
                video = update.message.video.file_id
                caption = update.message.caption or ""
                BroadcastHandlers.video(users, video, caption)
            elif bc_type == "bc_animation":
                animation = update.message.animation.file_id
                caption = update.message.caption or ""
                BroadcastHandlers.animation(users, animation, caption)

            if q[0] == "bc_to_all":
                sent_to = db.users.count_documents({"active": True})
            else:
                locations = q[1:-1]
                sent_to = db.users.count_documents({"location": {"$in": locations}, "active":True})
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(sent_to)
            )
            done(update, context)
        
    elif last_command == "map":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["map_feedback"],
            parse_mode="Markdown"
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    elif last_command == "get_counsel":
        handle_get_counsel(update, context)
    elif last_command == "counselor_request":
        handle_counselor_request(update, context)
    elif last_command == "counselor_request_yes":
        handle_counselor_request_yes(update, context)
    elif last_command.startswith("cr_yes"):
        message_id = int(last_command.split("=")[-1])
        text = update.message.text
        db.counseling_requests.update_one(
            {"request_message_id": message_id}, {"$set":{"active":True, "note": text}}
        )
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cr_done"]
        )
        done(update, context)
        notify_pastors(update, context)
    elif last_command.startswith("in-conversation-with"):
        conversation_handler(update, context)


def cb_handle(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    if q_head[0] == "map":
        if q[4:] in list(MAP_LOCATIONS.keys()):
            buttons = [[InlineKeyboardButton(i.capitalize(), callback_data=q+"="+i)] for i in list(MAP_LOCATIONS[q[4:]].keys())]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["location2"].format(q[4:].capitalize()),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif len(q_head) == 3:
            towns = set([i["location"] for i in MAP_LOCATIONS[q_head[1]][q_head[2]]])
            buttons = [[InlineKeyboardButton(i.capitalize(), callback_data=q+"="+i)] for i in list(towns)]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["location2"].format(q_head[2].capitalize()),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        elif len(q.split("=")) == 4:
            locations = ""
            for loc in MAP_LOCATIONS[q_head[1]][q_head[2]]:
                if loc["location"] == q_head[3]:
                    locations += config["messages"]["location4"].format(
                        loc["name"], loc["contact"]
                    )
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["location3"].format(q_head[3].capitalize(), locations)
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    elif q_head[0] == "bc":
        if q_head[1] == "all":
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["broadcast_type"],
                reply_markup=ReplyKeyboardMarkup(bc_buttons, resize_keyboard=True)
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"bc_to_all"}})
        else:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["broadcast_location"],
                reply_markup=InlineKeyboardMarkup(bc_location_buttons, resize_keyboard=True)
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":None}})
    elif q_head[0] == "bc-to":
        admin_user = db.users.find_one({"chat_id":chat_id})
        if q_head[1] == "done":
            locs = admin_user["last_command"].split("+")[1:]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["broadcast_location_done"].format(
                    ", ".join(locs)),
                reply_markup=ReplyKeyboardMarkup(bc_buttons, resize_keyboard=True)
                )
        else:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["broadcast_location_added"].format(q_head[1])
            )
            if admin_user["last_command"] is not None:
                db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":admin_user["last_command"]+"+"+q_head[1]}})
            else:
                db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"bc_to+"+q_head[1]}})
    elif q_head[0] == "s":
        sermon = search_db_title(q[2:])[0]
        if sermon["video"] is not None:
            button = [
                [InlineKeyboardButton("Download Sermon", url=sermon["download"])],
                [InlineKeyboardButton("Watch Video", url=sermon["video"])]
            ]
        else:
            button = [
                [InlineKeyboardButton("Download Sermon", url=sermon["link"])]
            ]
        context.bot.send_photo(
            chat_id=chat_id, photo=sermon["image"], caption=sermon["title"], reply_markup=InlineKeyboardMarkup(button)
           )
    elif q_head[0] == "loc":
        db.users.update_one({"chat_id":chat_id}, {"$set":{"location":q[4:]}})
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["lc_confirm"].format(q[4:])
        )
    elif q_head[0] == "bd":
        if len(q_head) == 2:
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
    elif q_head[0] == "get-sermon":
        if  q_head[1]=="yes":
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["get_sermon_1"]
            )
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"get_sermon"}})
        else:
            btns = [
                
            ]
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["get_sermon_2"],
                reply_markup=InlineKeyboardMarkup(btns)
            )
    elif q_head[0] == "cr":
        if q_head[1] == "yes":
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["cr_yes"],
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("Yes", callback_data="cr-yes="+q_head[2]),
                        InlineKeyboardButton("No", callback_data="cr-no="+q_head[2])
                    ]]
                )
            )
        else:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["counselor_request_invalid_info"]
            )
            db.counseling_requests.delete_one({"request_message_id":int(q_head[2])})
            db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"counselor_request_yes"}})
    elif q_head[0] == "cr-yes":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cr_yes_confirm"]
        )
        db.users.update_one({"chat_id":chat_id}, {"$set":{"last_command":"cr_yes="+q_head[1]}})
    elif q_head[0] == "cr-no":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cr_done"]
        )
        db.counseling_requests.update_one({"request_message_id":int(q_head[1])}, {"$set":{"active":True}})
        done(update, context)
        notify_pastors(update, context)
    elif q_head[0] == "conv":
        handle_initial_conversation_cb(update, context)
    elif q_head[0] == "end_conv":
        end_conversation_cb_handler(update, context)


        
msg_handler = MessageHandler(Filters.all & (~Filters.command), handle_message_response)
cb_handler = CallbackQueryHandler(cb_handle)

def main():
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("blog", blog_posts))
    dp.add_handler(CommandHandler("campuses", campuses))
    dp.add_handler(CommandHandler("membership", membership_school))
    dp.add_handler(msg_handler)
    dp.add_handler(cb_handler)

    updater.start_webhook(
        listen="0.0.0.0", port=int(PORT), url_path=os.getenv("BOT_TOKEN")
    )
    updater.bot.setWebhook('https://cci-bot.herokuapp.com/'+os.getenv("BOT_TOKEN"))
    updater.idle()


if __name__ == '__main__':
    main()
    #jobs.sched.start()