from datetime import datetime
import os
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
    get_ongoing_counseling_requests,
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

    # Check if user needs to verify for active requests access
    # Once verified, they stay verified (no time-based expiration)
    if not user.get("active_requests_verified", False):
        # Prompt for verification
        context.bot.send_message(
            chat_id=chat_id,
            text="🔐 To view active requests, please enter the authorization password:",
        )
        set_user_last_command(chat_id, "verify_active_requests")
        return

    # Get all ongoing counseling requests (no filtering by topic/location)
    ongoing_requests = get_ongoing_counseling_requests()

    reqs = len(ongoing_requests)
    if reqs == 0:
        context.bot.send_message(
            chat_id=chat_id,
            text="There are no ongoing counseling requests at the moment.",
        )
        return

    context.bot.send_message(
        chat_id=chat_id,
        text=f"There are currently {reqs} ongoing counseling requests.\n\nHere are the ongoing sessions (oldest first):",
    )

    # Show all ongoing requests (up to 20)
    for request in ongoing_requests:
        # Get counselor name (first and last name)
        counselor = db.users.find_one({"chat_id": request["counselor_chat_id"]})
        if counselor:
            first_name = counselor.get("first_name", "")
            last_name = counselor.get("last_name", "")
            counselor_name = f"{first_name} {last_name}".strip() or "Unknown"
        else:
            counselor_name = "Unknown"

        # Truncate note to first 20 characters
        note_preview = (
            request["note"][:20] + "..."
            if len(request["note"]) > 20
            else request["note"]
        )

        created_date = request["created"]
        formatted_date = created_date.strftime("%A, %B %d, %Y")

        context.bot.send_message(
            chat_id=chat_id,
            text=f"📋 *Ongoing Session*\n\n"
                 f"👤 *Name:* {request['name']}\n"
                 f"📧 *Email:* {request['email']}\n"
                 f"📞 *Phone:* {request['phone']}\n"
                 f"🏷️ *Category:* {request['topic']}\n"
                 f"👨‍💼 *Counselor:* {counselor_name}\n"
                 f"💬 *Note Preview:* {note_preview}\n"
                 f"📅 *Started:* {formatted_date}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Mark as Completed",
                            callback_data=f"mark_complete={request['request_message_id']}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Follow-Up",
                            callback_data=f"follow_up={request['request_message_id']}",
                        )
                    ]
                ],
                resize_keyboard=True,
            ),
        )


def handle_active_requests_verification(update, context):
    """
    Handles the verification for viewing active requests.
    """
    chat_id = update.effective_chat.id
    password = update.message.text.strip()
    
    if password == os.getenv("COUNSELOR_REQUEST_PASSWORD"):
        # Grant access and mark user as verified for active requests with timestamp
        db.users.update_one(
            {"chat_id": chat_id}, 
            {"$set": {
                "active_requests_verified": True,
                "active_requests_verified_at": datetime.now()
            }}
        )
        
        context.bot.send_message(
            chat_id=chat_id,
            text="✅ Access granted! You now have permanent access to view active requests.",
        )
        
        set_user_last_command(chat_id, None)
        
        # Automatically call show_active_requests after successful verification
        show_active_requests(update, context)
    else:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ Incorrect password. Access denied.\n\nPlease contact an administrator if you need access to view active requests.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)


def reset_active_requests_verification(chat_id):
    """
    Helper function to reset active requests verification for a user.
    This can be called when needed for security purposes or admin actions.
    """
    db.users.update_one(
        {"chat_id": chat_id}, 
        {"$unset": {
            "active_requests_verified": "",
            "active_requests_verified_at": ""
        }}
    )


def grant_active_requests_access(chat_id):
    """
    Helper function to grant active requests access to a counselor without password.
    This can be called by admins for onboarding or administrative purposes.
    """
    db.users.update_one(
        {"chat_id": chat_id}, 
        {"$set": {
            "active_requests_verified": True,
            "active_requests_verified_at": datetime.now()
        }}
    )


def show_new_requests(update, context):
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
        counselor_chat_id = req.get("counselor_chat_id")
        counselor_name = db.users.find_one({"chat_id": counselor_chat_id})["first_name"]
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["conversation_already_started"].format(
                counselor_name
            ),
        )


def send_message_handler(msg, to, from_chat_id=None):
    ## Send message to the other user with "End Conversation" button
    
    # Create the "End Conversation" button
    end_conversation_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 End Conversation", callback_data=f"end_conv_quick={from_chat_id}={to}")]
    ])
    
    if msg.text:
        if msg.text in keyboard_commands:
            return "Error"
        else:
            bot.send_message(
                chat_id=to, 
                text=msg.text,
                reply_markup=end_conversation_keyboard
            )
            return msg.text
    elif msg.photo:
        bot.send_photo(
            chat_id=to,
            photo=msg.photo[-1].file_id,
            caption=msg.caption or " ",
            reply_markup=end_conversation_keyboard
        )
        return "photo=" + msg.photo[-1].file_id
    elif msg.voice:
        bot.send_voice(
            chat_id=to,
            voice=msg.voice.file_id,
            caption=msg.caption or " ",
            reply_markup=end_conversation_keyboard
        )
        return "video=" + msg.voice.file_id
    elif msg.video:
        bot.send_video(
            chat_id=to,
            video=msg.video.file_id,
            caption=msg.caption or " ",
            reply_markup=end_conversation_keyboard
        )
        return msg.video.file_id
    elif msg.animation:
        bot.send_animation(
            chat_id=to,
            animation=msg.animation.file_id,
            caption=msg.caption or " ",
            reply_markup=end_conversation_keyboard
        )
        return "animation=" + msg.animation.file_id


def conversation_handler(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    send_to = user["last_command"].split("=")
    msg = update.message

    message_value = send_message_handler(msg, int(send_to[1]), chat_id)
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


def end_conversation_quick_cb_handler(update, context):
    """Handle the quick 'End Conversation' button attached to messages"""
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")
    
    # Verify this user is actually in a conversation
    user = db.users.find_one({"chat_id": chat_id})
    last_command = user.get("last_command", "") if user else ""
    
    if not last_command or not last_command.startswith("in-conversation-with"):
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ You are not currently in an active conversation."
        )
        return
    
    # Parse the conversation context from last_command
    try:
        _, other_id_str, role_str, msg_id_str = last_command.split("=")
        other_id = int(other_id_str)
        request_message_id = int(msg_id_str)
        role = "counselor" if role_str == "pastor" else "user"
    except (ValueError, IndexError):
        context.bot.send_message(
            chat_id=chat_id, 
            text="⚠️ Could not parse conversation context."
        )
        return
    
    # Send confirmation prompt (same as /cancel command)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["conversation_end_prompt"].format(role),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Yes",
                        callback_data=f"end_conv=yes={chat_id}={other_id}={role}",
                    ),
                    InlineKeyboardButton(
                        "No",
                        callback_data=f"end_conv=no={chat_id}={other_id}={role}",
                    ),
                ]
            ],
            resize_keyboard=True,
        ),
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


def follow_up_request_cb(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id, "role": "counselor"})
    
    if not user:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    q = update.callback_query.data
    q_head = q.split("=")
    request_message_id = int(q_head[1])
    
    # Get the counseling request
    request = db.counseling_requests.find_one({"request_message_id": request_message_id})
    
    if not request:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ Counseling request not found."
        )
        return
    
    # Get the conversation history
    conversation = db.conversations.find_one({"from": request_message_id})
    
    if not conversation:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ No conversation history found for this request."
        )
        return
    
    # Get counselor and user names
    original_counselor = db.users.find_one({"chat_id": conversation["counselor_id"]})
    user_info = db.users.find_one({"chat_id": conversation["user_chat_id"]})
    
    counselor_name = "Unknown"
    if original_counselor:
        first_name = original_counselor.get("first_name", "")
        last_name = original_counselor.get("last_name", "")
        counselor_name = f"{first_name} {last_name}".strip() or "Unknown"
    
    user_name = user_info.get("first_name", "Unknown") if user_info else "Unknown"
    
    # Format conversation history
    messages = conversation.get("messages", [])
    conversation_text = ""
    
    if messages:
        conversation_text = "\n\n📝 *Conversation History:*\n"
        for i, msg in enumerate(messages[-10:], 1):  # Show last 10 messages
            sender = "👨‍💼 Counselor" if msg["from"] == conversation["counselor_id"] else "👤 User"
            message_content = msg["message"]
            
            # Handle different message types
            if message_content.startswith("photo="):
                message_content = "📷 [Photo]"
            elif message_content.startswith("video="):
                message_content = "🎥 [Video]"
            elif message_content.startswith("animation="):
                message_content = "🎬 [Animation]"
            
            # Truncate long messages
            if len(message_content) > 100:
                message_content = message_content[:100] + "..."
                
            conversation_text += f"{i}. {sender}: {message_content}\n"
        
        if len(messages) > 10:
            conversation_text += f"\n... and {len(messages) - 10} more messages"
    else:
        conversation_text = "\n\n📝 *No conversation history available*"
    
    # Send follow-up confirmation message
    context.bot.send_message(
        chat_id=chat_id,
        text=f"🔄 *Follow-Up Request*\n\n"
             f"👤 *User:* {request['name']}\n"
             f"📧 *Email:* {request['email']}\n"
             f"🏷️ *Category:* {request['topic']}\n"
             f"👨‍💼 *Original Counselor:* {counselor_name}\n"
             f"📅 *Started:* {conversation['created'].strftime('%A, %B %d, %Y')}\n"
             f"💬 *Note:* {request['note']}"
             + conversation_text +
             f"\n\n❓ *Do you want to continue this conversation?*\n"
             f"If you continue, you'll take over this session and the user will be notified.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Continue Conversation",
                        callback_data=f"continue_conv={request_message_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data=f"cancel_follow_up={request_message_id}",
                    )
                ]
            ],
            resize_keyboard=True,
        ),
    )


def continue_conversation_cb(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id, "role": "counselor"})
    
    if not user:
        return

    q = update.callback_query.data
    q_head = q.split("=")
    request_message_id = int(q_head[1])
    
    # Get the counseling request and conversation
    request = db.counseling_requests.find_one({"request_message_id": request_message_id})
    conversation = db.conversations.find_one({"from": request_message_id})
    
    if not request or not conversation:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ Request or conversation not found."
        )
        return
    
    user_chat_id = request["user_chat_id"]
    
    # Check if user is already in another conversation
    user_last_command = get_user_last_command(user_chat_id)
    if user_last_command and user_last_command.startswith("in-conversation-with"):
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ This user is currently in another conversation. Please try again later."
        )
        return
    
    # Check if counselor is already in conversation
    counselor_last_command = get_user_last_command(chat_id)
    if counselor_last_command and counselor_last_command.startswith("in-conversation-with"):
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ You are currently in another conversation. Please end that conversation first."
        )
        return
    
    # Update the conversation and request
    db.conversations.update_one(
        {"from": request_message_id},
        {
            "$set": {
                "counselor_id": chat_id,
                "active": True,
                "resumed_at": datetime.now(),
                "resumed_by": chat_id
            }
        }
    )
    
    db.counseling_requests.update_one(
        {"request_message_id": request_message_id},
        {"$set": {"counselor_chat_id": chat_id, "status": "ongoing"}}
    )
    
    # Set conversation states
    set_user_last_command(
        user_chat_id, f"in-conversation-with={chat_id}=pastor={request_message_id}"
    )
    set_user_last_command(
        chat_id, f"in-conversation-with={user_chat_id}=user={request_message_id}"
    )
    
    # Get counselor name for notifications
    counselor_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "a counselor"
    
    # Notify the counselor
    context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ You have successfully continued the conversation with *{request['name']}*.\n\n"
             f"Messages you send from now will be delivered to them. You can end the conversation using /cancel.",
        parse_mode="Markdown"
    )
    
    # Notify the user
    context.bot.send_message(
        chat_id=user_chat_id,
        text=f"🔄 *Your counseling session has been resumed*\n\n"
             f"Counselor *{counselor_name}* has picked up your conversation and is ready to continue helping you.\n\n"
             f"Messages you send from now will be delivered to them. You can end the conversation using /cancel.",
        parse_mode="Markdown"
    )


def cancel_follow_up_cb(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text="❌ Follow-up cancelled. You can view other active requests or perform other actions."
    )


def mark_request_completed_cb(update, context):
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id, "role": "counselor"})
    
    if not user:
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["unknown"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    q = update.callback_query.data
    q_head = q.split("=")
    request_message_id = int(q_head[1])
    
    # Get the counseling request
    request = db.counseling_requests.find_one({"request_message_id": request_message_id})
    
    if not request:
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ Counseling request not found."
        )
        return
    
    if request.get("status") == "completed":
        context.bot.send_message(
            chat_id=chat_id,
            text="✅ This counseling request has already been marked as completed."
        )
        return
    
    # Mark the request as completed
    set_counseling_request_status(request_message_id, "completed")
    
    # Mark any active conversation as inactive
    db.conversations.update_one(
        {"from": request_message_id, "active": True},
        {"$set": {"active": False, "completed_at": datetime.now()}}
    )
    
    # Clear user last commands if they are in conversation
    user_chat_id = request["user_chat_id"]
    counselor_chat_id = request.get("counselor_chat_id")
    
    # Clear states for both users
    set_user_last_command(user_chat_id, None)
    if counselor_chat_id:
        set_user_last_command(counselor_chat_id, None)
    
    context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Counseling request for *{request['name']}* has been marked as completed.\n\n"
             f"Both the user and counselor have been notified that the session has ended.",
        parse_mode="Markdown"
    )
    
    # Notify the user that the session has been completed
    context.bot.send_message(
        chat_id=user_chat_id,
        text="✅ Your counseling session has been marked as completed by a counselor.\n\n"
             "Thank you for using our counseling service. If you need further assistance, "
             "please feel free to request another session.",
        reply_markup=ReplyKeyboardMarkup(normal_keyboard, resize_keyboard=True),
    )
    
    # Notify the assigned counselor if different from the one marking it complete
    if counselor_chat_id and counselor_chat_id != chat_id:
        context.bot.send_message(
            chat_id=counselor_chat_id,
            text=f"ℹ️ The counseling session with *{request['name']}* has been marked as completed by another counselor.",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(pastor_keyboard, resize_keyboard=True),
        )


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
