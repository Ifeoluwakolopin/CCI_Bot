from datetime import datetime
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from bot import db, bot, config
from bot.keyboards import (
    validate_user_keyboard,
    get_counseling_feedback_keyboard,
    keyboard_commands,
    normal_keyboard,
    pastor_keyboard,
)
from bot.database import (
    set_user_last_command,
    get_user_last_command,
    get_active_counseling_requests,
    set_counseling_request_status,
)


# function to displays all active requests to pastors : button
def show_active_requests(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id, "role": "pastor"})
    if user:
        active_requests = get_active_counseling_requests(
            user["topics"], user["locations"]
        )

        reqs = len(active_requests)
        if reqs == 0:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["active_requests_none"]
            )
        else:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["active_requests"].format(reqs)
            )
            if reqs > 5:
                top_reqs = active_requests[0:5]
            else:
                top_reqs = active_requests

            for request in top_reqs:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=config["messages"]["active_request"].format(
                        request["name"],
                        request["email"],
                        request["phone"],
                        request["topic"],
                        request["note"],
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "Start Conversation",
                                    callback_data="conv="
                                    + str(request["request_message_id"]),
                                )
                            ]
                        ],
                        resize_keyboard=True,
                    ),
                )
    else:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)


def notify_pastors(counseling_request):
    pastors = db.users.find(
        {
            "role": "pastor",
            "topics": counseling_request["topic"],
            "locations": counseling_request["location"],
            "chat_id": {"$ne": counseling_request["user_chat_id"]},
        }
    )

    for pastor in pastors:
        bot.send_message(
            chat_id=pastor["chat_id"], text=config["messages"]["active_request_notify"]
        )

        bot.send_message(
            chat_id=pastor["chat_id"],
            text=config["messages"]["active_request"].format(
                counseling_request["name"],
                counseling_request["email"],
                counseling_request["phone"],
                counseling_request["topic"],
                counseling_request["note"],
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Start Conversation",
                            callback_data="conv="
                            + str(counseling_request["request_message_id"]),
                        )
                    ]
                ],
                resize_keyboard=True,
            ),
        )


def handle_initial_conversation_cb(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    req = db.counseling_requests.find_one({"request_message_id": int(q_head[1])})
    if req["user_chat_id"] == chat_id:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["conversation_start_self_not_allowed"],
        )
    elif req["status"] == "pending":
        pastor = db.users.find_one({"chat_id": chat_id})
        user_chat_id = req["user_chat_id"]

        if get_user_last_command(user_chat_id).startswith("in-conversation-with"):
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["user_in_separate_conversation"],
            )
            return
        ## notify pastor that conversation has started
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["conversation_start"].format(req["name"]),
        )
        ## notify user that conversation has started
        context.bot.send_message(
            chat_id=req["user_chat_id"],
            text=config["messages"]["conversation_start_user"].format(
                pastor["first_name"]
            ),
            parse_mode="Markdown",
        )
        ## set pastor_id as counselor_id for request
        db.counseling_requests.update_one(
            {"request_message_id": req["request_message_id"]},
            {"$set": {"counselor_chat_id": chat_id}},
        )
        ## set user status as in-conversation with pastor
        msg_id = req["request_message_id"]

        set_user_last_command(
            user_chat_id, f"in-conversation-with={chat_id}=pastor={msg_id}"
        )

        ## set pastor status as in-conversation with user
        set_user_last_command(
            chat_id, f"in-conversation-with={user_chat_id}=user={msg_id}"
        )

        ## start conversation
        start_conversation(chat_id, req)
        set_counseling_request_status(req["request_message_id"], "ongoing")
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_already_started"]
        )
        set_user_last_command(chat_id, None)


def send_message_handler(msg, to):
    ## Send message to the other user.
    if msg.text:
        if msg.text in keyboard_commands:
            return "Error"
        else:
            bot.send_message(chat_id=to, text=msg.text)
            return msg.text
    elif msg.photo:
        bot.send_photo(
            chat_id=to,
            photo=msg.photo[-1].file_id,
            caption=msg.caption or " ",
        )
        return "photo=" + msg.photo[-1].file_id
    elif msg.voice:
        bot.send_voice(
            chat_id=to,
            voice=msg.voice.file_id,
            caption=msg.caption or " ",
        )
        return "video=" + msg.voice.file_id
    elif msg.video:
        bot.send_video(
            chat_id=to,
            video=msg.video.file_id,
            caption=msg.caption or " ",
        )
        return msg.video.file_id
    elif msg.animation:
        bot.send_animation(
            chat_id=to,
            animation=msg.animation.file_id,
            caption=msg.caption or " ",
        )
        return "animation=" + msg.animation.file_id


def conversation_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    send_to = user["last_command"].split("=")
    msg = update.message

    message_value = send_message_handler(msg, int(send_to[1]))
    if message_value == "Error":
        keyboard = validate_user_keyboard(chat_id)
        bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["in_conversation"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
    else:
        message = {
            "message": message_value,
            "created": datetime.now(),
            "from": chat_id,
            "to": int(send_to[1]),
        }

        ## Update conversation object in database.
        if send_to[2] == "pastor":
            update_conversation(message, int(send_to[1]), chat_id)
        else:
            update_conversation(message, chat_id, int(send_to[1]))


def end_conversation_prompt(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    send_to = user["last_command"].split("=")

    role = send_to[2]

    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["conversation_end_prompt"].format(role),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Yes",
                        callback_data="end_conv=yes="
                        + str(chat_id)
                        + "="
                        + send_to[1]
                        + "="
                        + role,
                    ),
                    InlineKeyboardButton(
                        "No",
                        callback_data="end_conv=no="
                        + str(chat_id)
                        + "="
                        + send_to[1]
                        + "="
                        + role,
                    ),
                ]
            ],
            resize_keyboard=True,
        ),
    )


def set_conversation_status(counselor_id, user_id, active):
    db.conversations.update_one(
        {"counselor_id": counselor_id, "user_id": user_id}, {"$set": {"active": active}}
    )


def end_conversation_cb_handler(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    user = db.users.find_one({"chat_id": chat_id})

    if user["role"] == "pastor":
        keyboard1, keyboard2 = pastor_keyboard, normal_keyboard
        pastor_id = chat_id
        user_id = int(q_head[3])
        other = "pastor"
    else:
        keyboard1, keyboard2 = normal_keyboard, pastor_keyboard
        user_id = chat_id
        pastor_id = int(q_head[3])
        other = "user"

    if q_head[1] == "yes":
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["conversation_end_confirm"],
            reply_markup=ReplyKeyboardMarkup(keyboard1, resize_keyboard=True),
        )
        context.bot.send_message(
            chat_id=pastor_id,
            text=config["messages"]["conversation_end_notify"].format(other),
            reply_markup=ReplyKeyboardMarkup(keyboard2, resize_keyboard=True),
        )
        # update counseling_request status to completed
        set_counseling_request_status(
            int(user["last_command"].split("=")[-1]), "completed"
        )
        # update conversation status to completed
        set_conversation_status(user_id, pastor_id, False)

        # update user last_command to None
        set_user_last_command(chat_id, None)
        set_user_last_command(pastor_id, None)
        # Ask user to provide feedback on their conversation.
        request_counseling_feedback_from_user(user_id, pastor_id)
    else:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["conversation_end_cancel"]
        )


def start_conversation(chat_id, counseling_request):
    if not db.conversations.find_one(
        {"from": counseling_request["request_message_id"], "active": True}
    ):
        db.conversations.insert_one(
            {
                "counselor_id": chat_id,
                "user_chat_id": counseling_request["user_chat_id"],
                "messages": [],
                "created": datetime.now(),
                "from": counseling_request["request_message_id"],
                "last_updated": datetime.now(),
                "active": True,
            }
        )


def update_conversation(msg, counselor_id, user_id):
    db.conversations.update_one(
        {"counselor_id": counselor_id, "user_chat_id": user_id, "active": True},
        {"$push": {"messages": msg}, "$set": {"last_updated": datetime.now()}},
    )


def request_counseling_feedback_from_user(user_chat_id, pastor_chat_id):
    pastor_name = db.users.find_one({"chat_id": pastor_chat_id})["first_name"]
    bot.send_message(
        chat_id=user_chat_id,
        text=config["messages"]["counseling_feedback_prompt"].format(pastor_name),
        reply_markup=get_counseling_feedback_keyboard(user_chat_id, pastor_chat_id),
    )


def handle_counseling_feedback_cb(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")

    # Check if a rating for the counselor already exists
    existing_rating = db.conversations.find_one(
        {
            "counselor_id": int(q_head[3]),
            "user_chat_id": int(q_head[2]),
            "ratings": {"$elemMatch": {"counselor": int(q_head[3])}},
        },
        {"_id": 1},
    )

    if existing_rating:
        # Rating for this counselor already exists
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_feedback_already"],
        )
    else:
        # Add new rating since it doesn't exist
        db.conversations.update_one(
            {
                "counselor_id": int(q_head[3]),
                "user_chat_id": int(q_head[2]),
            },
            {
                "$push": {
                    "ratings": {"rating": int(q_head[1]), "counselor": int(q_head[3])}
                }
            },
        )

        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counseling_feedback_thanks"]
        )

    set_user_last_command(chat_id, None)


# TODO: create a function to get calendly link and send
def create_calendly_link():
    pass


def counselor_transfer(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    if user["role"] == "pastor":
        if user["last_command"].startswith("in-conversation-with"):
            location = db.counseling_requests.find_one(
                {"request_message_id": int(user["last_command"].split("=")[-1])}
            )["location"]
            pastors = db.users.find({"role": "pastor", "location": location})
            last_command = user["last_command"]
            set_user_last_command(chat_id, f"transfer_req={last_command}")
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counselor_transfer_prompt"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Pastor {}".format(pastor["first_name"]),
                                callback_data="transfer=" + str(pastor["chat_id"]),
                            )
                        ]
                        for pastor in pastors
                        if pastor is not user
                    ],
                    resize_keyboard=True,
                ),
            )
        else:
            context.bot.send_message(
                chat_id=chat_id, text=config["messages"]["counselor_transfer_invalid"]
            )
    else:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)


def counselor_transfer_callback_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    q = update.callback_query.data
    q_head = q.split("=")
    pastor = db.users.find_one({"chat_id": int(q_head[1])})
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counselor_transfer_details"].format(
            pastor["first_name"]
        ),
    )
    last_command = "=".join(user["last_command"].split("=")[-4:])
    set_user_last_command(chat_id, f"transfer_req={q_head[1]}={last_command}")


def counselor_transfer_msg_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    msg = update.message.text.strip()
    try:
        id = int(user["last_command"].split("=")[1])
        user_id = int(user["last_command"].split("=")[-3])

        db.conversations.update_one(
            {"counselor_id": chat_id, "user_id": user_id, "active": True},
            {"$set": {"counselor_transfer_msg": msg}},
        )
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_transfer_msg_confirm"],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Complete Transfer",
                            callback_data="transfer_req_confirm=true=" + str(id),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Edit",
                            callback_data="transfer_req_confirm=false=" + str(id),
                        )
                    ],
                ],
                resize_keyboard=True,
            ),
        )
    except:
        last_command = user["last_command"].split("=")[2:]
        set_user_last_command(chat_id, f"transfer_req={'='.join(last_command)}")
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_transfer_msg_prompt"],
        )


def counselor_transfer_msg_confirm_cb_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    q = update.callback_query.data
    q_head = q.split("=")
    new_pastor = db.users.find_one({"chat_id": int(q_head[2])})
    if user["last_command"] is not None:
        last_commands = user["last_command"].split("=")
        if q_head[1] == "true":
            # send confirmation
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counselor_transfer_confirm"].format(
                    new_pastor["first_name"]
                ),
            )
            # update counseling request to set the new pastor as the counselor for this request
            db.counseling_requests.update_one(
                {"request_message_id": int(last_commands[-1])},
                {
                    "$set": {
                        "counselor_chat_id": new_pastor["chat_id"],
                        "transfer_from": chat_id,
                        "status": "pending",
                    }
                },
            )

            counseling_request = db.counseling_requests.find_one(
                {"request_message_id": int(last_commands[-1])}
            )

            # update the conversation to set the new pastor as the counselor for this conversation
            db.conversations.update_one(
                {
                    "counselor_id": chat_id,
                    "user_id": int(last_commands[-3]),
                    "active": True,
                },
                {
                    "$set": {
                        "counselor_id": new_pastor["chat_id"],
                        "transfer_from": chat_id,
                    }
                },
            )
            conv = db.conversations.find_one(
                {
                    "counselor_id": new_pastor["chat_id"],
                    "transfer_from": chat_id,
                    "active": True,
                }
            )

            # notify new pastor of transfer
            context.bot.send_message(
                chat_id=new_pastor["chat_id"],
                text=config["messages"]["counselor_transfer_notify"].format(
                    user["first_name"],
                    counseling_request["name"],
                    counseling_request["email"],
                    counseling_request["phone"],
                    counseling_request["topic"],
                    counseling_request["note"],
                    user["first_name"],
                    conv["counselor_transfer_msg"],
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Continue Conversation",
                                callback_data="conv="
                                + str(counseling_request["request_message_id"]),
                            )
                        ]
                    ],
                    resize_keyboard=True,
                ),
            )
            user_chat_id = int(user["last_command"].split("=")[-3])
            # notify user of transfer

            feedback_keyboard = get_counseling_feedback_keyboard(user_chat_id, chat_id)
            context.bot.send_message(
                chat_id=user_chat_id,
                text=config["messages"]["counselor_transfer_notify_user"].format(
                    new_pastor["first_name"], user["first_name"]
                ),
                reply_markup=feedback_keyboard,
            )
            set_user_last_command(user_chat_id, None)
            set_user_last_command(chat_id, None)
        else:
            location = db.counseling_requests.find_one(
                {"request_message_id": int(user["last_command"].split("=")[-1])}
            )["location"]
            pastors = db.users.find({"role": "pastor", "location": location})
            last_command = "=".join(user["last_command"].split("=")[-4:])
            set_user_last_command(chat_id, f"transfer_req={last_command}")
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counselor_transfer_edit"],
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "Pastor {}".format(pastor["first_name"]),
                                callback_data="transfer=" + str(pastor["chat_id"]),
                            )
                        ]
                        for pastor in pastors
                    ],
                    resize_keyboard=True,
                ),
            )
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_request_transferred"],
            reply_markup=ReplyKeyboardMarkup(
                validate_user_keyboard(chat_id), resize_keyboard=True
            ),
        )
