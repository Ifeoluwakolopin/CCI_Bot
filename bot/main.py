import os
from . import dp, updater, PORT, db, config, bot
from .database import search_db_title, set_user_last_command
from .commands import (
    get_devotional,
    latest_sermon,
    get_sermon,
    helps,
    stats,
    broadcast_message_handler,
    map_loc,
    cancel,
    reboot_about,
    unknown,
    start,
    mute,
    unmute,
    menu,
    done,
    blog_posts,
    feedback,
    membership_school,
    feedback_cb_handler,
    set_church_location,
    find_user,
    church_location_callback_handler,
    handle_find_user_callback,
    handle_branch_selection_callback,
    handle_update_user,
    find_user_message_handler,
    handle_broadcast,
)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from chat.chat_message_handlers import (
    counseling,
    handle_counseling,
    handle_ask_question_or_request_counselor,
    handle_counselor_request_yes,
    handle_counseling_info_confirm,
    handle_counseling_location_confirm,
    handle_get_faq_callback,
)
from chat.chat_callback_handlers import (
    show_active_requests,
    conversation_handler,
    counselor_transfer_msg_confirm_cb_handler,
    counselor_transfer_msg_handler,
    notify_pastors,
    handle_initial_conversation_cb,
    end_conversation_cb_handler,
    handle_counseling_feedback_cb,
    counselor_transfer_callback_handler,
    counselor_transfer,
)
from dotenv import dotenv_values, load_dotenv
from bot.helpers import create_day_buttons

load_dotenv()


def handle_message_commands(update, context):
    """
    This matches incoming commands from users to their respective functions

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
    elif title == "find user":
        find_user(update, context)
    elif title == "statistics":
        stats(update, context)
    elif title == "broadcast":
        broadcast_message_handler(update, context)
    elif title == "map":
        map_loc(update, context)
    elif title == "cancel":
        cancel(update, context)
    elif title == "reboot camp":
        reboot_about(update, context)
    elif title == "counseling":
        counseling(update, context)
    elif title == "show active counseling requests":
        show_active_requests(update, context)
    elif title == "location":
        set_church_location(update, context)
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
    elif last_command.startswith("in-conversation-with"):
        conversation_handler(update, context)
    elif last_command == "find_user":
        find_user_message_handler(update, context)
    elif last_command.startswith("update_user"):
        handle_update_user(update, context)
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
                    buttons = [
                        [
                            InlineKeyboardButton(
                                "Download Sermon", url=sermon["download"]
                            )
                        ],
                        [InlineKeyboardButton("Watch Video", url=sermon["video"])],
                    ]
                    context.bot.send_photo(
                        chat_id=chat_id,
                        photo=sermon["image"],
                        caption=sermon["title"],
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                else:
                    button = [
                        [InlineKeyboardButton("Download Sermon", url=sermon["link"])]
                    ]
                    context.bot.send_photo(
                        chat_id=chat_id,
                        photo=sermon["image"],
                        caption=sermon["title"],
                        reply_markup=InlineKeyboardMarkup(button),
                    )
        menu(update, context)
    elif last_command.startswith("broadcast"):
        handle_broadcast(update, context)

    elif last_command == "map":
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["map_feedback"],
            parse_mode="Markdown",
        )
        set_user_last_command(chat_id, None)
    elif last_command.startswith("counselor_request"):
        topic = last_command.split("=")[-1]
        handle_counselor_request_yes(update, context, topic)
    elif last_command.startswith("cr_yes"):
        message_id = int(last_command.split("=")[-1])
        text = update.message.text
        db.counseling_requests.update_one(
            {"request_message_id": message_id}, {"$set": {"active": True, "note": text}}
        )
        req = db.counseling_requests.find_one({"request_message_id": message_id})
        context.bot.send_message(chat_id=chat_id, text=config["messages"]["cr_done"])
        done(update, context)
        # Notify pastors in particular category about new request.
        notify_pastors(req)
    elif last_command.startswith("feedback"):
        type = last_command.split("=")[-1]
        message = update.message.text

        db.feedback.insert_one(
            {"type": type, "message": message, "status": "pending", "user": chat_id}
        )
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["feedback_done"]
        )
        set_user_last_command(chat_id, None)
    elif last_command.startswith("transfer_req"):
        counselor_transfer_msg_handler(update, context)


def cb_handle(update, context):
    chat_id = update.effective_chat.id
    callback = update.callback_query
    q = callback.data
    q_head = q.split("=")
    if q_head[0] == "map":
        # TODO: refactor map location handling
        pass
    elif q_head[0] == "update":
        handle_find_user_callback(update, context)
    elif q_head[0] == "counsel":
        handle_counseling(update, context)
    elif q_head[0] == "qa_or_c":
        handle_ask_question_or_request_counselor(update, context)
    elif q_head[0] == "bc":
        if q_head[1] == "all":
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["bc_prompt"],
            )
            set_user_last_command(chat_id, "broadcast")
    # Search db for sermons
    elif q_head[0] == "s":
        sermon = search_db_title(q[2:])[0]
        if sermon["video"] is not None:
            button = [
                [InlineKeyboardButton("Download Sermon", url=sermon["download"])],
                [InlineKeyboardButton("Watch Video", url=sermon["video"])],
            ]
        else:
            button = [[InlineKeyboardButton("Download Sermon", url=sermon["link"])]]
        context.bot.send_photo(
            chat_id=chat_id,
            photo=sermon["image"],
            caption=sermon["title"],
            reply_markup=InlineKeyboardMarkup(button),
        )
    elif q_head[0] == "loc":
        church_location_callback_handler(update, context)
    elif q_head[0] == "br":
        handle_branch_selection_callback(update, context)
    elif q_head[0] == "bd":
        if len(q_head) == 2:
            month = q_head[1]
            if month in ["9", "4", "6", "11"]:
                last_day = 30
            elif month == "2":
                last_day = 29  # Assuming leap year to be safe
            else:
                last_day = 31

            # Create a proper grid of day buttons (7 days per row)
            day_buttons = []
            cols = 7  # 7 columns for days (like a calendar)

            # Generate buttons for each day
            current_row = []
            for day in range(1, last_day + 1):
                current_row.append(
                    InlineKeyboardButton(str(day), callback_data=f"bd={month}={day}")
                )

                # Start a new row after reaching the column limit
                if len(current_row) == cols:
                    day_buttons.append(current_row)
                    current_row = []

            # Add any remaining buttons in the last row
            if current_row:
                day_buttons.append(current_row)

            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_day"],
                reply_markup=InlineKeyboardMarkup(day_buttons),
            )
        else:
            db.users.update_one(
                {"chat_id": chat_id},
                {"$set": {"birthday": q.split("=")[1] + "-" + q.split("=")[2]}},
            )
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_confirm"].format(
                    q.split("=")[1] + "/" + q.split("=")[2]
                ),
            )
            set_user_last_command(chat_id, None)
    elif q_head[0] == "get-sermon":
        if q_head[1] == "yes":
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["get_sermon_1"]
            )
            set_user_last_command(chat_id, "get_sermon")
        else:
            buttons = []
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["get_sermon_2"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
    elif q_head[0] == "confirm_info":
        handle_counseling_info_confirm(update, context)
    elif q_head[0] == "confirm_loc":
        handle_counseling_location_confirm(update, context)
    elif q_head[0] == "cr-yes":
        user_local_church = db.users.find_one({"chat_id": chat_id}).get("location")
        db.counseling_requests.update_one(
            {"request_message_id": int(q_head[1])},
            {"$set": {"location": user_local_church}},
        )
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cr_yes_confirm"]
        )
        set_user_last_command(chat_id, "cr_yes=" + q_head[1])
    elif q_head[0] == "conv":
        handle_initial_conversation_cb(update, context)
    elif q_head[0] == "end_conv":
        end_conversation_cb_handler(update, context)
    elif q_head[0] == "faq":
        handle_get_faq_callback(update, context)
    elif q_head[0] == "feedback":
        feedback_cb_handler(update, context)
    elif q_head[0] == "counseling_feedback":
        handle_counseling_feedback_cb(update, context)
    elif q_head[0] == "transfer":
        counselor_transfer_callback_handler(update, context)
    elif q_head[0] == "transfer_req_confirm":
        counselor_transfer_msg_confirm_cb_handler(update, context)


msg_handler = MessageHandler(Filters.all & (~Filters.command), handle_message_response)
cb_handler = CallbackQueryHandler(cb_handle)


def main(deploy: bool = False) -> None:
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("blog", blog_posts))
    dp.add_handler(CommandHandler("campuses", set_church_location))
    dp.add_handler(CommandHandler("feedback", feedback))
    dp.add_handler(CommandHandler("membership", membership_school))
    dp.add_handler(CommandHandler("transfer", counselor_transfer))
    dp.add_handler(msg_handler)
    dp.add_handler(cb_handler)

    if deploy:
        URL = "https://cci-bot.herokuapp.com/"
        updater.start_webhook(
            listen="0.0.0.0", port=int(PORT), url_path=os.getenv("BOT_TOKEN")
        )
        updater.bot.setWebhook(URL + os.getenv("BOT_TOKEN"))
    else:
        updater.start_polling()

    updater.idle()
