from datetime import datetime
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from bot import db, bot, config
from bson.int64 import Int64
from bot.keyboards import (
    validate_user_keyboard,
    get_counseling_feedback_keyboard,
    keyboard_commands,
    normal_keyboard,
    pastor_keyboard,
)
from bson import Int64
from bot.database import (
    set_user_last_command,
    get_user_last_command,
    get_active_counseling_requests,
    set_counseling_request_status,
)


def show_active_requests(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id, "role": "counselor"})

    if not user:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)
        return

    # Step 1: Get topics this counselor is associated with
    if user.get("global") == True:
        topics = []  # Global access — allow all topics
    else:
        associated_topics = db.counseling_topics.find(
            {"counselors": chat_id}, {"topic": 1}
        )
        topics = [doc["topic"] for doc in associated_topics]

    # Step 2: Get active counseling requests for these topics
    active_requests = get_active_counseling_requests(topics=topics)

    reqs = len(active_requests)
    if reqs == 0:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["active_requests_none"]
        )
        return

    context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["active_requests"].format(reqs)
    )

    # Show top 5 or fewer requests
    top_reqs = active_requests[:5]

    for request in top_reqs:
        created_date = request["created"]
        formatted_date = created_date.strftime("%A, %B %d, %Y")

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["active_request"].format(
                request["name"],
                request["email"],
                request["phone"],
                request["topic"],
                request["note"],
            )
            + f"\nRequested on: {formatted_date}",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Start Conversation",
                            callback_data="conv=" + str(request["request_message_id"]),
                        )
                    ]
                ],
                resize_keyboard=True,
            ),
        )


def notify_pastors(counseling_request):
    # Step 1: Get topic document
    topic_doc = db.counseling_topics.find_one({"topic": counseling_request["topic"]})

    if not topic_doc or "counselors" not in topic_doc:
        print("No counselors found for this topic.")
        return

    # Step 2: Filter out requesting user's chat_id

    counselor_ids = [cid for cid in topic_doc["counselors"]]

    if not counselor_ids:
        print("No eligible counselors to notify.")
        return

    # Step 3: Get counselors by chat_id
    pastors = db.users.find(
        {
            "$or": [
                {"chat_id": {"$in": counselor_ids}},
                {"role": "counselor", "global": True},
            ],
            "chat_id": {"$ne": counseling_request["user_chat_id"]},
        }
    )

    # Step 4: Send notifications
    for pastor in pastors:
        if str(pastor.get("last_command", "")).startswith("in-conversation-with"):
            continue
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

        user_last_command = get_user_last_command(user_chat_id)
        if user_last_command is not None and user_last_command.startswith(
            "in-conversation-with"
        ):
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
    chat_id = Int64(update.effective_chat.id)
    q = update.callback_query.data
    q_head = q.split("=")

    user = db.users.find_one({"chat_id": chat_id})
    last_command = user.get("last_command", "")

    # Parse from "in-conversation-with={other_id}=user|pastor={request_message_id}"
    try:
        _, other_id_str, role_str, msg_id_str = last_command.split("=")
        other_id = Int64(other_id_str)
        request_message_id = int(msg_id_str)
        role = "counselor" if role_str == "pastor" else "user"
    except (ValueError, IndexError):
        context.bot.send_message(
            chat_id=chat_id, text="⚠️ Could not parse conversation context."
        )
        return

    # Set roles accordingly
    if role == "counselor":
        actor_role = "user"
        actor_keyboard = normal_keyboard
        other_keyboard = pastor_keyboard
        user_id, counselor_id = chat_id, other_id
    else:
        actor_role = "counselor"
        actor_keyboard = pastor_keyboard
        other_keyboard = normal_keyboard
        user_id, counselor_id = other_id, chat_id

    if q_head[1] == "yes":
        # Confirm to actor
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["conversation_end_confirm"],
            reply_markup=ReplyKeyboardMarkup(actor_keyboard, resize_keyboard=True),
        )
        # Notify the other participant
        context.bot.send_message(
            chat_id=other_id,
            text=config["messages"]["conversation_end_notify"].format(actor_role),
            reply_markup=ReplyKeyboardMarkup(other_keyboard, resize_keyboard=True),
        )

        set_counseling_request_status(request_message_id, "completed")
        set_conversation_status(user_id, counselor_id, False)
        set_user_last_command(chat_id, None)
        set_user_last_command(other_id, None)

        # Trigger feedback from the user about the counselor
        request_counseling_feedback_from_user(user_id, counselor_id)
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


from bson.int64 import Int64
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup


def counselor_transfer(update, context):
    chat_id = Int64(update.effective_chat.id)
    user = db.users.find_one({"chat_id": chat_id})

    if user.get("role") != "counselor":
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)
        return

    last_command = user.get("last_command")
    if not last_command or not last_command.startswith("in-conversation-with"):
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_transfer_invalid"]
        )
        return

    try:
        request_msg_id = int(last_command.split("=")[-1])
    except (IndexError, ValueError):
        context.bot.send_message(
            chat_id=chat_id,
            text="Could not extract request ID from your current session.",
        )
        return

    req = db.counseling_requests.find_one({"request_message_id": request_msg_id})
    if not req:
        context.bot.send_message(chat_id=chat_id, text="Counseling request not found.")
        return

    topic = req["topic"]
    user_chat_id = Int64(req["user_chat_id"])

    # Step 1: Get counselors from the topic
    topic_doc = db.counseling_topics.find_one({"topic": topic})
    topic_counselors = topic_doc.get("counselors", []) if topic_doc else []

    # Step 2: Get global counselors
    global_counselors_cursor = db.users.find(
        {"role": "counselor", "global": True}, {"chat_id": 1}
    )
    global_counselors = [Int64(p["chat_id"]) for p in global_counselors_cursor]

    # Step 3: Combine and deduplicate
    eligible_ids = list(set(topic_counselors + global_counselors))

    # Step 4: Filter out current counselor and the user
    eligible_ids = [
        cid for cid in eligible_ids if cid != chat_id and cid != user_chat_id
    ]

    # Step 5: Query user info
    pastors = db.users.find({"chat_id": {"$in": eligible_ids}})

    # Save transfer state
    set_user_last_command(chat_id, f"transfer_req={last_command}")

    # Create buttons
    buttons = [
        [
            InlineKeyboardButton(
                f"Counselor {pastor.get('first_name', '')}",
                callback_data=f"transfer={pastor['chat_id']}",
            )
        ]
        for pastor in pastors
    ]

    if not buttons:
        context.bot.send_message(
            chat_id=chat_id, text="No eligible counselors found for transfer."
        )
        return

    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counselor_transfer_prompt"],
        reply_markup=InlineKeyboardMarkup(buttons, resize_keyboard=True),
    )


def counselor_transfer_callback_handler(update, context):
    chat_id = Int64(update.effective_chat.id)
    q = update.callback_query.data
    q_head = q.split("=")
    new_counselor_id = Int64(q_head[1])

    user = db.users.find_one({"chat_id": chat_id})
    new_pastor = db.users.find_one({"chat_id": new_counselor_id})

    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["counselor_transfer_details"].format(
            new_pastor["first_name"]
        ),
    )

    last_command = "=".join(user["last_command"].split("=")[-4:])
    set_user_last_command(chat_id, f"transfer_req={new_counselor_id}={last_command}")


def counselor_transfer_msg_handler(update, context):
    chat_id = Int64(update.effective_chat.id)
    user = db.users.find_one({"chat_id": chat_id})
    msg = update.message.text.strip()

    try:
        parts = user["last_command"].split("=")
        new_counselor_id = Int64(parts[1])
        user_id = Int64(parts[-3])

        db.conversations.update_one(
            {"counselor_id": chat_id, "user_chat_id": user_id, "active": True},
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
                            callback_data=f"transfer_req_confirm=true={new_counselor_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Edit",
                            callback_data=f"transfer_req_confirm=false={new_counselor_id}",
                        )
                    ],
                ]
            ),
        )

    except Exception:
        # Retry by re-setting the last_command
        last_command = "=".join(user["last_command"].split("=")[2:])
        set_user_last_command(chat_id, f"transfer_req={last_command}")
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["counselor_transfer_msg_prompt"]
        )


def counselor_transfer_msg_confirm_cb_handler(update, context):
    chat_id = Int64(update.effective_chat.id)
    user = db.users.find_one({"chat_id": chat_id})
    callback_data = update.callback_query.data
    q_head = callback_data.split("=")
    new_counselor_id = Int64(q_head[2])
    new_pastor = db.users.find_one({"chat_id": new_counselor_id})

    if not user or not user.get("last_command"):
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counseling_request_transferred"],
            reply_markup=ReplyKeyboardMarkup(
                validate_user_keyboard(chat_id), resize_keyboard=True
            ),
        )
        return

    parts = user["last_command"].split("=")
    transfer_confirmed = q_head[1] == "true"
    original_request_msg_id = int(parts[-1])
    original_user_chat_id = Int64(parts[-3])

    if transfer_confirmed:
        # ✅ Step 1: Confirm transfer to user
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_transfer_confirm"].format(
                new_pastor["first_name"]
            ),
        )

        # ✅ Step 2: Update the counseling request
        db.counseling_requests.update_one(
            {"request_message_id": original_request_msg_id},
            {
                "$set": {
                    "counselor_chat_id": new_counselor_id,
                    "transfer_from": chat_id,
                    "status": "pending",
                }
            },
        )
        counseling_request = db.counseling_requests.find_one(
            {"request_message_id": original_request_msg_id}
        )

        # ✅ Step 3: Update the conversation
        db.conversations.update_one(
            {
                "counselor_id": chat_id,
                "user_chat_id": original_user_chat_id,
                "active": True,
            },
            {"$set": {"counselor_id": new_counselor_id, "transfer_from": chat_id}},
        )
        conv = db.conversations.find_one(
            {"counselor_id": new_counselor_id, "transfer_from": chat_id, "active": True}
        )

        # ✅ Step 4: Notify the new counselor
        context.bot.send_message(
            chat_id=new_counselor_id,
            text=config["messages"]["counselor_transfer_notify"].format(
                user["first_name"],
                counseling_request["name"],
                counseling_request["email"],
                counseling_request["phone"],
                counseling_request["topic"],
                counseling_request["note"],
                user["first_name"],
                conv.get("counselor_transfer_msg", "No message provided."),
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Continue Conversation",
                            callback_data=f"conv={original_request_msg_id}",
                        )
                    ]
                ],
                resize_keyboard=True,
            ),
        )

        # ✅ Step 5: Notify the user (who made the request)
        feedback_keyboard = get_counseling_feedback_keyboard(
            original_user_chat_id, chat_id
        )
        context.bot.send_message(
            chat_id=original_user_chat_id,
            text=config["messages"]["counselor_transfer_notify_user"].format(
                new_pastor["first_name"], user["first_name"]
            ),
            reply_markup=feedback_keyboard,
        )

        # ✅ Step 6: Reset states
        set_user_last_command(original_user_chat_id, None)
        set_user_last_command(chat_id, None)

    else:
        # ❌ Transfer was not confirmed – show alternative counselors again

        request_doc = db.counseling_requests.find_one(
            {"request_message_id": original_request_msg_id}
        )
        topic = request_doc["topic"]
        user_chat_id = request_doc["user_chat_id"]

        topic_doc = db.counseling_topics.find_one({"topic": topic})
        topic_ids = topic_doc.get("counselors", []) if topic_doc else []

        global_cursor = db.users.find(
            {"role": "counselor", "global": True}, {"chat_id": 1}
        )
        global_ids = [Int64(p["chat_id"]) for p in global_cursor]

        eligible_ids = list(set(topic_ids + global_ids))
        eligible_ids = [
            cid for cid in eligible_ids if cid != chat_id and cid != user_chat_id
        ]

        pastors = db.users.find({"chat_id": {"$in": eligible_ids}})

        last_command = "=".join(user["last_command"].split("=")[-4:])
        set_user_last_command(chat_id, f"transfer_req={last_command}")

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_transfer_edit"],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"Counselor {pastor.get('first_name', '')}",
                            callback_data=f"transfer={pastor['chat_id']}",
                        )
                    ]
                    for pastor in pastors
                ],
                resize_keyboard=True,
            ),
        )
