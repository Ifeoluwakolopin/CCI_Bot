import os
from . import dp, updater, PORT, db, config, bot
from .database import search_db_title
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
    campuses,
    feedback,
    membership_school,
    feedback_cb_handler,
)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler, CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from chat.handlers import (
    get_counsel,
    handle_get_counsel,
    handle_ask_question_or_request_counselor,
    handle_counselor_request_yes,
    handle_get_faq_callback,
)
from chat.counselor_handlers import (
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
        broadcast_message_handler(update, context)
    elif title == "map":
        map_loc(update, context)
    elif title == "cancel":
        cancel(update, context)
    elif title == "reboot camp":
        reboot_about(update, context)
    elif title == "counseling":
        get_counsel(update, context)
    elif title == "show active counseling requests":
        show_active_requests(update, context)
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
    elif last_command.startswith("bc_to"):
        # TODO: fix broadcast handling

        pass

    elif last_command == "map":
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["map_feedback"],
            parse_mode="Markdown",
        )
        db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})
    elif last_command.startswith("get_counsel"):
        handle_get_counsel(update, context)
    elif last_command == "question_or_counselor_request":
        handle_ask_question_or_request_counselor(update, context)
    elif last_command == "counselor_request_yes":
        handle_counselor_request_yes(update, context)
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
        db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})
    elif last_command.startswith("transfer_req"):
        counselor_transfer_msg_handler(update, context)


def cb_handle(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    if q_head[0] == "map":
        # TODO: refactor map location handling
        pass
    elif q_head[0] == "bc-to":
        # TODO: refactor broadcast handling
        pass
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
        db.users.update_one({"chat_id": chat_id}, {"$set": {"location": q[4:]}})
        bot.send_message(
            chat_id=chat_id, text=config["messages"]["lc_confirm"].format(q[4:])
        )
    elif q_head[0] == "bd":
        if len(q_head) == 2:
            buttons = [
                [
                    InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                    for i in range(1, 8)
                ],
                [
                    InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                    for i in range(8, 15)
                ],
                [
                    InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                    for i in range(15, 22)
                ],
                [
                    InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                    for i in range(22, 29)
                ],
            ]

            if q.split("=")[1] in ["9", "4", "6", "11"]:
                buttons.append(
                    [
                        InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                        for i in range(29, 31)
                    ]
                )
            elif q.split("=")[1] == "2":
                buttons.append(
                    [
                        InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                        for i in range(29, 30)
                    ]
                )
            else:
                buttons.append(
                    [
                        InlineKeyboardButton(str(i), callback_data=q + "=" + str(i))
                        for i in range(29, 32)
                    ]
                )

            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_day"],
                reply_markup=InlineKeyboardMarkup(buttons),
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
    elif q_head[0] == "get-sermon":
        if q_head[1] == "yes":
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["get_sermon_1"]
            )
            db.users.update_one(
                {"chat_id": chat_id}, {"$set": {"last_command": "get_sermon"}}
            )
        else:
            buttons = []
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["get_sermon_2"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
    elif q_head[0] == "cr":
        if q_head[1] == "yes":
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["cr_choose_category"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Spiritual Growth",
                                callback_data="cr-cat=spiritual growth=" + q_head[2],
                            ),
                            InlineKeyboardButton(
                                "Relationships",
                                callback_data="cr-cat=relationships=" + q_head[2],
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "Career", callback_data="cr-cat=career=" + q_head[2]
                            ),
                            InlineKeyboardButton(
                                "Mental Wellbeing",
                                callback_data="cr-cat=mental wellbeing=" + q_head[2],
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "Habits and Addictions",
                                callback_data="cr-cat=habits and addictions="
                                + q_head[2],
                            ),
                            InlineKeyboardButton(
                                "Marriage and Family",
                                callback_data="cr-cat=marriage and family=" + q_head[2],
                            ),
                        ],
                        [
                            InlineKeyboardButton(
                                "Other", callback_data="cr-cat=other=" + q_head[2]
                            )
                        ],
                    ]
                ),
            )
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counselor_request_invalid_info"],
            )
            db.counseling_requests.delete_one({"request_message_id": int(q_head[2])})
            db.users.update_one(
                {"chat_id": chat_id},
                {"$set": {"last_command": "counselor_request_yes"}},
            )
    elif q_head[0] == "cr-cat":
        db.counseling_requests.update_one(
            {"request_message_id": int(q_head[-1])}, {"$set": {"topic": q_head[-2]}}
        )
        user_location = db.users.find_one({"chat_id": chat_id})["location"]
        counseling_location_buttons = [
            [
                InlineKeyboardButton(
                    "Lagos - Ikeja", callback_data="cr-loc=Ikeja=" + q_head[-1]
                ),
                InlineKeyboardButton(
                    "Lagos - Lekki", callback_data="cr-loc=Lekki=" + q_head[-1]
                ),
            ],
            [
                InlineKeyboardButton(
                    "Lagos - Yaba", callback_data="cr-loc=Yaba=" + q_head[-1]
                ),
                InlineKeyboardButton(
                    "Ile-Ife", callback_data="cr-loc=Ile-ife=" + q_head[-1]
                ),
            ],
            [
                InlineKeyboardButton(
                    "Ibadan", callback_data="cr-loc=Ibadan=" + q_head[-1]
                ),
                InlineKeyboardButton(
                    "Port-Harcourt", callback_data="cr-loc=PH=" + q_head[-1]
                ),
            ],
            [
                InlineKeyboardButton(
                    "Canada", callback_data="cr-loc=Canada=" + q_head[-1]
                ),
                InlineKeyboardButton(
                    "Abuja", callback_data="cr-loc=Abuja=" + q_head[-1]
                ),
            ],
            [
                InlineKeyboardButton(
                    "United Kingdom(UK)", callback_data="cr-loc=UK=" + q_head[-1]
                )
            ],
        ]
        if user_location not in ["None", "Online"]:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["cr_confirm_location"].format(user_location),
                reply_markup=InlineKeyboardMarkup(counseling_location_buttons),
            )
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["cr_choose_location"],
                reply_markup=InlineKeyboardMarkup(counseling_location_buttons),
            )
    elif q_head[0] == "cr-loc":
        db.counseling_requests.update_one(
            {"request_message_id": int(q_head[-1])}, {"$set": {"location": q_head[-2]}}
        )
        db.users.update_one({"chat_id": chat_id}, {"$set": {"location": q_head[-2]}})
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["cr_yes"],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Add Note", callback_data="cr-yes=" + q_head[2]
                        )
                    ]
                ],
                resize_keyboard=True,
            ),
        )
    elif q_head[0] == "cr-yes":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["cr_yes_confirm"]
        )
        db.users.update_one(
            {"chat_id": chat_id}, {"$set": {"last_command": "cr_yes=" + q_head[1]}}
        )
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
    dp.add_handler(CommandHandler("campuses", campuses))
    dp.add_handler(CommandHandler("feedback", feedback))
    dp.add_handler(CommandHandler("membership", membership_school))
    dp.add_handler(CommandHandler("transfer", counselor_transfer))
    dp.add_handler(msg_handler)
    dp.add_handler(cb_handler)

    if deploy:
        updater.start_webhook(
            listen="0.0.0.0", port=int(PORT), url_path=os.getenv("BOT_TOKEN")
        )
        updater.bot.setWebhook(
            "https://cci-bot.herokuapp.com/" + os.getenv("BOT_TOKEN")
        )
    else:
        updater.start_polling()

    updater.idle()
