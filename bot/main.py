import os
from . import application, PORT, db, config, bot
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
    feedback,
    feedback_cb_handler,
    set_church_location,
    find_user,
    church_location_callback_handler,
    handle_find_user_callback,
    handle_branch_selection_callback,
    handle_update_user,
    find_user_message_handler,
    handle_broadcast,
    counselor_dashboard,
    handle_counselor_verification,
    handle_counselor_topic_update,
    handle_topic_selection,
    handle_location_not_set_first_time,
    handle_location_not_set_for_counseling,
    handle_birthday_not_set,
)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import filters
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
    show_new_requests,
    conversation_handler,
    counselor_transfer_msg_confirm_cb_handler,
    counselor_transfer_msg_handler,
    notify_pastors,
    handle_initial_conversation_cb,
    end_conversation_cb_handler,
    end_conversation_quick_cb_handler,
    handle_counseling_feedback_cb,
    mark_request_completed_cb,
    counselor_transfer_callback_handler,
    counselor_transfer,
    follow_up_request_cb,
    continue_conversation_cb,
    cancel_follow_up_cb,
    handle_active_requests_verification,
)
from dotenv import dotenv_values, load_dotenv

load_dotenv()


async def handle_message_commands(update, context):
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
        await get_devotional(update, context)
    elif title == "latest sermon":
        await latest_sermon(update, context)
    elif title == "get sermon":
        await get_sermon(update, context)
    elif title == "help":
        await helps(update, context)
    elif title == "find user":
        await find_user(update, context)
    elif title == "statistics":
        await stats(update, context)
    elif title == "broadcast":
        await broadcast_message_handler(update, context)
    elif title == "map":
        map_loc(update, context)
    elif title == "cancel":
        await cancel(update, context)
    elif title == "reboot camp":
        await reboot_about(update, context)
    elif title == "counseling":
        await counseling(update, context)
    elif title == "menu":
        await menu(update, context)
    elif title == "view active requests":
        await show_active_requests(update, context)
    elif title == "view new requests":
        await show_new_requests(update, context)
    elif title == "counselor dashboard":
        await counselor_dashboard(update, context)
    elif title == "location":
        await set_church_location(update, context)
    else:
        await unknown(update, context)


async def handle_message_response(update, context):
    """
    Handles actions for messages
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    last_command = user["last_command"]

    if last_command == None:
        await handle_message_commands(update, context)
    elif last_command == "first_time_location_set":
        await handle_location_not_set_first_time(update, context)
    elif last_command == "first_time_birthday_set":
        await handle_birthday_not_set(update, context)
    elif last_command.startswith("location_counseling"):
        await handle_location_not_set_for_counseling(update, context)
    elif last_command.startswith("in-conversation-with"):
        await conversation_handler(update, context)
    elif last_command == "find_user":
        await find_user_message_handler(update, context)
    elif last_command == "select_topics":
        await handle_topic_selection(update, context)
    elif last_command == "verify_counselor":
        await handle_counselor_verification(update, context)
    elif last_command == "verify_active_requests":
        await handle_active_requests_verification(update, context)
    elif last_command.startswith("update_user"):
        await handle_update_user(update, context)
    elif last_command == "get_sermon":
        title = update.message.text.strip()
        sermons = search_db_title(title)
        if len(sermons) == 0:
            await context.bot.send_message(
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
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=sermon["image"],
                        caption=sermon["title"],
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                else:
                    button = [
                        [InlineKeyboardButton("Download Sermon", url=sermon["link"])]
                    ]
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=sermon["image"],
                        caption=sermon["title"],
                        reply_markup=InlineKeyboardMarkup(button),
                    )
        await menu(update, context)
    elif last_command.startswith("broadcast"):
        await handle_broadcast(update, context)

    elif last_command == "map":
        await context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["map_feedback"],
            parse_mode="Markdown",
        )
        set_user_last_command(chat_id, None)
    elif last_command.startswith("counselor_request"):
        topic = last_command.split("=")[-1]
        await handle_counselor_request_yes(update, context, topic)
    elif last_command.startswith("cr_yes"):
        message_id = int(last_command.split("=")[-1])
        text = update.message.text
        db.counseling_requests.update_one(
            {"request_message_id": message_id}, {"$set": {"active": True, "note": text}}
        )
        req = db.counseling_requests.find_one({"request_message_id": message_id})
        await context.bot.send_message(chat_id=chat_id, text=config["messages"]["cr_done"])
        await done(update, context)
        # Notify pastors in particular category about new request.
        await notify_pastors(req)
    elif last_command.startswith("feedback"):
        type = last_command.split("=")[-1]
        message = update.message.text

        db.feedback.insert_one(
            {"type": type, "message": message, "status": "pending", "user": chat_id}
        )
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["feedback_done"]
        )
        set_user_last_command(chat_id, None)
    elif last_command.startswith("transfer_req"):
        await counselor_transfer_msg_handler(update, context)


async def cb_handle(update, context):
    chat_id = update.effective_chat.id
    callback = update.callback_query
    q = callback.data
    q_head = q.split("=")
    if q_head[0] == "map":
        # TODO: refactor map location handling
        pass
    elif q_head[0] == "update":
        await handle_find_user_callback(update, context)
    elif q_head[0] == "counsel":
        await handle_counseling(update, context)
    elif q_head[0] == "qa_or_c":
        await handle_ask_question_or_request_counselor(update, context)
    elif q_head[0] == "bc":
        if q_head[1] == "all":
            await context.bot.send_message(
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
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=sermon["image"],
            caption=sermon["title"],
            reply_markup=InlineKeyboardMarkup(button),
        )
    elif q_head[0] == "loc":
        await church_location_callback_handler(update, context)
    elif q_head[0] == "br":
        await handle_branch_selection_callback(update, context)
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

            await context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_day"],
                reply_markup=InlineKeyboardMarkup(day_buttons),
            )
        else:
            db.users.update_one(
                {"chat_id": chat_id},
                {"$set": {"birthday": q.split("=")[1] + "-" + q.split("=")[2]}},
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_confirm"].format(
                    q.split("=")[1] + "/" + q.split("=")[2]
                ),
            )
            set_user_last_command(chat_id, None)
    elif q_head[0] == "get-sermon":
        if q_head[1] == "yes":
            await context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["get_sermon_1"]
            )
            set_user_last_command(chat_id, "get_sermon")
        else:
            buttons = []
            await context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["get_sermon_2"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
    elif q_head[0] == "confirm_info":
        await handle_counseling_info_confirm(update, context)
    elif q_head[0] == "confirm_loc":
        await handle_counseling_location_confirm(update, context)
    elif q_head[0] == "cr-yes":
        user_local_church = db.users.find_one({"chat_id": chat_id}).get("location")
        db.counseling_requests.update_one(
            {"request_message_id": int(q_head[1])},
            {"$set": {"location": user_local_church}},
        )
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cr_yes_confirm"]
        )
        set_user_last_command(chat_id, "cr_yes=" + q_head[1])
    elif q_head[0] == "conv":
        await handle_initial_conversation_cb(update, context)
    elif q_head[0] == "mark_complete":
        await mark_request_completed_cb(update, context)
    elif q_head[0] == "follow_up":
        await follow_up_request_cb(update, context)
    elif q_head[0] == "continue_conv":
        await continue_conversation_cb(update, context)
    elif q_head[0] == "cancel_follow_up":
        await cancel_follow_up_cb(update, context)
    elif q_head[0] == "end_conv":
        await end_conversation_cb_handler(update, context)
    elif q_head[0] == "end_conv_quick":
        await end_conversation_quick_cb_handler(update, context)
    elif q_head[0] == "faq":
        await handle_get_faq_callback(update, context)
    elif q_head[0] == "feedback":
        await feedback_cb_handler(update, context)
    elif q_head[0] == "counseling_feedback":
        await handle_counseling_feedback_cb(update, context)
    elif q_head[0] == "transfer":
        await counselor_transfer_callback_handler(update, context)
    elif q_head[0] == "transfer_req_confirm":
        await counselor_transfer_msg_confirm_cb_handler(update, context)
    elif q_head[0] == "update_topics":
        await handle_counselor_topic_update(update, context)


msg_handler = MessageHandler(filters.ALL & (~filters.COMMAND), handle_message_response)
cb_handler = CallbackQueryHandler(cb_handle)


def main(deploy: bool = False) -> None:
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("feedback", feedback))
    application.add_handler(CommandHandler("transfer", counselor_transfer))
    application.add_handler(msg_handler)
    application.add_handler(cb_handler)

    if deploy:
        URL = "https://cci-bot-be313a646eb4.herokuapp.com/"
        application.run_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=os.getenv("BOT_TOKEN"),
            webhook_url=URL + os.getenv("BOT_TOKEN"),
        )
    else:
        application.run_polling()
