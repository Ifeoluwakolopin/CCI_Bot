import os
import json
from . import bot, db, config
from .models import BotUser
from .helpers import (
    BroadcastHandlers,
    MessageHelper,
    PromptHelper,
    create_buttons_from_data,
    handle_view_more,
    find_text_for_callback,
    add_note,
)
from .database import (
    add_user_to_db,
    set_user_active,
    set_user_last_command,
    get_user_last_command,
    get_countries,
    get_church_locations,
)
from datetime import date, datetime
from bson.int64 import Int64
from chat.chat_callback_handlers import end_conversation_prompt
from .scrapers import WebScrapers
from .keyboards import validate_user_keyboard
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup


def start(update, context):
    """
    This is the response of the bot on startup.

    Args:
        update (Update): An object representing an incoming update.
        context (CallbackContext): An object that provides access to additional data and capabilities.
    """
    chat_id = update.effective_chat.id
    first_name = update.message.chat.first_name
    last_name = update.message.chat.last_name
    username = update.message.chat.username

    # Create and add user to database
    user = BotUser(chat_id, first_name, last_name, username)
    add_user_to_db(user)

    # Set user as active
    set_user_active(chat_id, True)

    # Send welcome message
    send_welcome_message(chat_id, first_name, context.bot)

    db.users.update_one(
        {"chat_id": chat_id}, {"$set": {"last_command": "first_time_location_set"}}
    )


def send_welcome_message(chat_id, first_name, bot):
    """
    Sends a welcome message to the user.

    Args:
        chat_id (int): The chat ID of the user.
        first_name (str): The first name of the user.
        bot (Bot): The bot instance.
    """
    welcome_message = config["messages"]["start"].format(first_name)

    countries = get_countries()

    rows, cols = 4, 1
    buttons = create_buttons_from_data(countries, "loc", rows, cols)

    bot.send_message(
        chat_id=chat_id,
        text=welcome_message,
        parse_mode="Markdown",
        disable_web_page_preview="True",
        reply_markup=buttons,
    )


def handle_location_not_set_first_time(update, context):
    """
    Handles the case where a user has not set their location for the first time.
    Prompts the user to set their church location.
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["location_not_set_first_time"],
    )


def handle_location_not_set_for_counseling(update, context):
    """
    Handles the case where a user has not set their location for counseling.
    Prompts the user to set their church location.
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["location_not_set_for_counseling"],
    )


def handle_birthday_not_set(update, context):
    """
    Handles the case where a user has not set their birthday.
    Prompts the user to set their birthday.
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["birthday_not_set"],
    )


def bc_setup(update, context):
    """
    Unified function to set up broadcast for different types of messages.
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id, "admin": True})
    if not user:
        return

    # Send a message to the admin to select the type of broadcast
    context.bot.send_message(chat_id=chat_id, text=config["messages"]["bc_prompt"])

    set_user_last_command(chat_id, "broadcast")


def find_user(update, context):
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id": chat_id, "admin": True}):
        context.bot.send_message(chat_id=chat_id, text=config["messages"]["find_user"])
        set_user_last_command(chat_id, "find_user")
    else:
        unknown(update, context)


def find_user_message_handler(update, context):
    chat_id = update.effective_chat.id
    msg = update.message.text.split("\n")
    db_query = {k: v.strip() for k, v in [i.split(":") for i in msg]}
    if "admin" in db_query:
        db_query["admin"] = True if db_query["admin"].lower() == "true" else False
    users = db.users.find(db_query, {"_id": 0, "date": 0})
    if users.count() == 0:
        update.message.reply_text("No users found")
    else:
        for user in users:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Update Location",
                        callback_data="update=loc=" + str(user["chat_id"]),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Update Birthday",
                        callback_data="update=bd=" + str(user["chat_id"]),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Update Role",
                        callback_data="update=role=" + str(user["chat_id"]),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Update Admin Status",
                        callback_data="update=admin=" + str(user["chat_id"]),
                    )
                ],
            ]

            if user["role"]:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            "Remove from Locations",
                            callback_data="update=rm_loc=" + str(user["chat_id"]),
                        )
                    ]
                )

            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["user_found"].format(
                    json.dumps(user, indent=2)
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )


def handle_find_user_callback(update, context):
    chat_id = update.effective_chat.id
    query_data = update.callback_query.data.split("=")
    user_id = query_data[-1]
    user = db.users.find_one({"chat_id": int(user_id)})
    if query_data[1] == "loc":
        action = "location"
        church_locations = list(db.church_locations.find({}, {"_id": 0}))
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["update_user_location"].format(
                user["first_name"],
                user["last_name"],
                json.dumps(church_locations, indent=2),
            ),
        )
    elif query_data[1] == "rm_loc":
        action = "remove location"
        locations = list(user["locations"])
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["update_remove_pastor_location"].format(
                user["first_name"], user["last_name"], locations
            ),
        )
    elif query_data[1] == "bd":
        action = "birthday"
    elif query_data[1] == "role":
        action = "role"
    else:
        action = "admin"

    if action != "location" and action != "remove location":
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["update_user"].format(
                user["first_name"], user["last_name"], action
            ),
        )
    set_user_last_command(chat_id, f"update_user={action}={user_id}")


def handle_update_user(update, context):
    chat_id = update.effective_chat.id
    last_command = get_user_last_command(chat_id).split("=")
    user_id = last_command[-1]
    msg = update.message.text
    if last_command[1] == "admin":
        if msg.lower() == "true":
            update = {"$set": {"admin": True}}
        else:
            update = {"$set": {"admin": False}}
    elif last_command[1] == "remove location":
        update = {"$pull": {"locations": msg}}
    elif last_command[1] == "location" and db.users.find_one(
        {"chat_id": int(user_id), "role": "counselor"}
    ):
        update = {"$addToSet": {"locations": msg}, "$set": {"location": msg}}
    else:
        update = {"$set": {last_command[1]: msg}}

    db.users.update_one({"chat_id": int(user_id)}, update)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["update_user_done"].format(last_command[1], update),
    )
    set_user_last_command(chat_id, None)


def handle_broadcast(update, context):
    """
    Handles the broadcast action based on the admin's response.
    """
    chat_id = update.effective_chat.id
    message = update.message
    user = db.users.find_one({"chat_id": chat_id, "admin": True})
    if not user or user.get("last_command") != "broadcast":
        return

    # Reset last_command after broadcast
    set_user_last_command(chat_id, None)

    # Fetch all users to broadcast to
    users = db.users.distinct("chat_id", {"active": True})

    print(f"FOund {len(users)} users to broadcast to")
    print("Sample user id", users[0])

    print("Message:", message)

    if message.text:
        BroadcastHandlers.broadcast_message(
            users, message.text, MessageHelper.send_text
        )
    elif message.photo:
        photo = message.photo[-1].file_id
        caption = message.caption or ""
        BroadcastHandlers.broadcast_message(
            users, photo, MessageHelper.send_photo, caption
        )
    elif message.video:
        video = message.video.file_id
        caption = message.caption or ""
        BroadcastHandlers.broadcast_message(
            users, video, MessageHelper.send_video, caption
        )
    elif message.animation:
        animation = message.animation.file_id
        caption = message.caption or ""
        BroadcastHandlers.broadcast_message(
            users, animation, MessageHelper.send_animation, caption
        )


def blog_posts(update, context):
    chat_id = update.effective_chat.id

    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
        button = [
            [InlineKeyboardButton("Read blog posts", url="https://ccing.org/blogs/")]
        ]
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["blog_posts"],
            reply_markup=InlineKeyboardMarkup(button),
        )
        set_user_last_command(chat_id)


def broadcast_message_handler(update, context):
    """
    This function allows for an admin personnel send broadcast
    to all users
    """
    chat_id = update.effective_chat.id
    if db.users.find_one({"chat_id": chat_id, "admin": True}):
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["broadcast"],
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Send to all users", callback_data="bc=all")],
                ],
            ),
        )
        set_user_last_command(chat_id)
    else:
        unknown(update, context)


def cancel(update, context):
    """
    This function helps you cancel any existing action
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    keyboard = validate_user_keyboard(chat_id)

    if user["last_command"] is not None:
        if user["last_command"].startswith("in-conversation-with"):
            end_conversation_prompt(update, context)
        elif user["last_command"].startswith("counselor_request") or user[
            "last_command"
        ].startswith("location_counseling"):
            latest_request = db.counseling_requests.find_one(
                {"user_chat_id": chat_id}, sort=[("created", -1)]
            )
            if latest_request:
                db.counseling_requests.delete_one({"_id": latest_request["_id"]})
                context.bot.send_message(
                    chat_id=chat_id,
                    text=config["messages"]["counselor_request_cancel"],
                )

            set_user_last_command(chat_id, None)
        elif user["last_command"].split("=")[0] == "transfer_req":
            # cancel a counseling transfer request
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["counselor_transfer_cancel"],
            )
            db.users.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "last_command": user["last_command"].replace(
                            "transfer_req=", ""
                        )
                    }
                },
            )
        elif user["last_command"] == "verify_counselor":
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"].get("cancel", "Action cancelled."),
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            set_user_last_command(chat_id, None)
        else:
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["cancel"],
                parse_mode="Markdown",
                disable_web_page_preview="True",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            set_user_last_command(chat_id, None)

    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["cancel"],
            parse_mode="Markdown",
            disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)


def done(update, context):
    """
    This function helps you finish an existing action.
    """
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["done"],
        parse_mode="Markdown",
        disable_web_page_preview="True",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    set_user_last_command(chat_id, None)


def feedback(update, context):
    chat_id = update.effective_chat.id
    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["feedback"],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Technical Issue", callback_data="feedback=technical"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Suggestion", callback_data="feedback=suggestion"
                        )
                    ],
                    [InlineKeyboardButton("Other", callback_data="feedback=other")],
                ],
                resize_keyboard=True,
            ),
        )
        db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


def feedback_cb_handler(update, context):
    chat_id = update.effective_chat.id
    q = update.callback_query.data
    q_head = q.split("=")

    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["feedback_handler"],
    )
    db.users.update_one(
        {"chat_id": chat_id}, {"$set": {"last_command": "feedback=" + q_head[1]}}
    )


def get_sermon(update, context):
    """
    This gets a particular sermon user wants
    """
    chat_id = update.effective_chat.id
    buttons = [
        [InlineKeyboardButton("Yes, find by title", callback_data="get-sermon=yes")],
        [
            InlineKeyboardButton(
                "No, looking for a topic/date", callback_data="get-sermon=no"
            )
        ],
    ]
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["get_sermon"],
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def get_devotional(update, context):
    """
    This get the devotional for the particular day
    """
    chat_id = update.effective_chat.id
    if not db.devotionals.find_one({"date": str(date.today())}):
        d = WebScrapers.t30()
        db.devotionals.insert_one(d)
    else:
        d = db.devotionals.find_one({"date": str(date.today())})
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    context.bot.send_photo(
        chat_id=chat_id,
        photo=d["image"],
        caption=config["messages"]["t30_caption"].format(
            d["title"], d["excerpt"].split("\n")[0]
        ),
        reply_markup=InlineKeyboardMarkup(button),
    )
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


def helps(update, context):
    """
    This sends a list of available commands for the bot
    """
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["help"],
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


def latest_sermon(update, context):
    """
    This gets the most recent sermon
    """
    chat_id = update.effective_chat.id
    sermon = db.temporary.find_one({"latest_sermon": True})
    if sermon["video"] is not None:
        buttons = [
            [InlineKeyboardButton("Download Sermon", url=sermon["download"])],
            [InlineKeyboardButton("Watch Video", url=sermon["video"])],
        ]
        context.bot.send_photo(
            chat_id=chat_id,
            photo=sermon["image"],
            caption=sermon["title"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        button = [[InlineKeyboardButton("Download Sermon", url=sermon["link"])]]
        context.bot.send_photo(
            chat_id=chat_id,
            photo=sermon["image"],
            caption=sermon["title"],
            reply_markup=InlineKeyboardMarkup(button),
        )
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


def map_loc(update, context):
    """
    This handles requests for map locations.
    """
    # TODO: redo map location prompt
    pass


def menu(update, context):
    """
    This restores the default keyboard.
    """
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["menu"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
        set_user_last_command(chat_id, None)


def membership_school(update, context):
    chat_id = update.effective_chat.id

    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
        button = [
            [
                InlineKeyboardButton(
                    "Register", url="https://ccing.org/membership-class/"
                )
            ]
        ]
        context.bot.send_photo(
            chat_id=chat_id,
            photo=open("img/membership.jpg", "rb"),
            caption=config["messages"]["membership"],
            reply_markup=InlineKeyboardMarkup(button),
        )
        set_user_last_command(chat_id, None)


def mute(update, context):
    """
    This set the user's mute status
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text=config["messages"]["mute"])
    db.users.update_one({"chat_id": chat_id}, {"$set": {"mute": True}})


def unmute(update, context):
    """
    This sets the user's mute status to false
    """
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text=config["messages"]["unmute"])
    db.users.update_one({"chat_id": chat_id}, {"$set": {"mute": False}})


def notify_new_sermon(chat_id, sermons):
    try:
        buttons = [
            [InlineKeyboardButton(i, callback_data="s=" + i.split("-")[2])]
            for i in sermons
        ]
    except:
        buttons = [[InlineKeyboardButton(i, callback_data="s=" + i)] for i in sermons]
    user = db.users.find_one({"chat_id": chat_id})
    try:
        bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["new_sermon"].format(user["first_name"]),
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    except:
        set_user_active(chat_id, False)


def unknown(update, context):
    """
    This handles unrecognized commands.
    """
    chat_id = update.effective_chat.id
    user = db.users.find_one({"chat_id": chat_id})
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["unknown"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    set_user_last_command(chat_id, None)


def reboot_about(update, context):
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["reboot_camp"]["about"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    set_user_last_command(chat_id, None)


def set_church_location(update, context):
    """
    This function sets the church location for a user
    """
    chat_id = update.effective_chat.id
    countries = get_countries()

    user = db.users.find_one({"chat_id": chat_id})
    rows, cols = 4, 1
    buttons = create_buttons_from_data(countries, "loc", rows, cols)

    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["lc"].format(user["first_name"]),
        reply_markup=buttons,
    )


def church_location_callback_handler(update, context):
    """
    This function handles the callback from the church location prompt
    """
    chat_id = update.effective_chat.id
    query_data = update.callback_query.data.split("=")

    if query_data[1] == "more":
        countries = get_countries()
        rows, cols = 4, 1
        updated_buttons = handle_view_more(
            update.callback_query,
            countries,
            "loc",
            rows,
            cols,
        )

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc_other"],
            reply_markup=updated_buttons,
        )
    else:
        country = find_text_for_callback(update.callback_query)
        church_locations = get_church_locations(country)

        buttons = create_buttons_from_data(church_locations, f"br={country}", 4, 2)

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc_country"].format(country),
            reply_markup=buttons,
        )


def handle_branch_selection_callback(update, context):
    """
    This function handles the callback from the church location prompt
    """
    chat_id = update.effective_chat.id
    query_data = update.callback_query.data.split("=")

    if query_data[2] == "more":
        country = query_data[1]
        church_locations = get_church_locations(country)
        updated_buttons = handle_view_more(
            update.callback_query,
            church_locations,
            f"br={country}",
            4,
            2,
        )
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc_other"],
            reply_markup=updated_buttons,
        )
    else:
        branch = find_text_for_callback(update.callback_query)
        db.users.update_one({"chat_id": chat_id}, {"$set": {"location": branch}})
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc_done"].format(branch),
        )

        user = db.users.find_one({"chat_id": chat_id})
        if user["last_command"] == "first_time_location_set":
            PromptHelper.birthday_prompt(chat_id)
            db.users.update_one(
                {"chat_id": chat_id},
                {"$set": {"last_command": "first_time_birthday_set"}},
            )
        if user["last_command"].startswith("location_counseling"):
            msg_id = user["last_command"].split("=")[-1]
            set_user_last_command(chat_id, None)
            add_note(
                update,
                context,
                config["messages"]["counselor_request_note"],
                msg_id,
            )


def stats(update, context):
    """
    This function gives you statistics about the bot
    """
    chat_id = update.effective_chat.id

    if db.users.find_one({"chat_id": chat_id, "admin": True}):
        total_users = db.users.count_documents({})
        active_users = db.users.count_documents({"active": True})
        mute_users = db.users.count_documents({"mute": True})
        total_sermons = db.sermons.count_documents({})
        birthdays = db.users.count_documents({"birthday": {"$exists": True}})
        today = datetime.today()
        todays_birthdays = db.users.count_documents(
            {"birthday": f"{today.month}-{today.day}"}
        )

        pipeline = [
            {
                "$group": {
                    "_id": "$location",  # Group by the location field
                    "count": {"$sum": 1},  # Count the occurrences
                }
            },
            {
                "$sort": {"count": -1}
            },  # Optional: sorts the results by count in descending order
        ]

        location_counts_cursor = db.users.aggregate(pipeline)
        location_counts = {doc["_id"]: doc["count"] for doc in location_counts_cursor}

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["stats"].format(
                total_users,
                active_users,
                mute_users,
                total_sermons,
                birthdays,
                todays_birthdays,
                json.dumps(location_counts, indent=2),
            ),
            parse_mode="Markdown",
        )
        set_user_last_command(chat_id, None)
    else:
        unknown(update, context)


def check_user_in_conversation(chat_id):
    """
    This function validates the last command of the user.
    """
    user = db.users.find_one({"chat_id": chat_id})
    if user["last_command"]:
        if user["last_command"].startswith("in-conversation"):
            return True
    else:
        return False


def notify_in_conversation(chat_id):
    """
    This function notifies the user that they are in a conversation.
    """
    keyboard = validate_user_keyboard(chat_id)
    bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["in_conversation"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


def counselor_dashboard(update, context):
    """
    Displays the counselor's dashboard or prompts for counselor verification.
    """
    chat_id = Int64(update.effective_chat.id)
    user = db.users.find_one({"chat_id": chat_id})

    if not user or user.get("role") != "counselor":
        # Prompt for counselor verification
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["not_counselor_prompt"],
        )
        db.users.update_one(
            {"chat_id": chat_id}, {"$set": {"last_command": "verify_counselor"}}
        )
        return

    total_pending_requests = db.counseling_requests.count_documents(
        {"status": "pending"}
    )
    total_counselors = db.users.count_documents({"role": "counselor"})
    # Count requests handled
    requests_answered = db.counseling_requests.count_documents(
        {"counselor_chat_id": chat_id}
    )

    # Topics assigned
    if user.get("global"):
        topic_docs = db.counseling_topics.find({}, {"topic": 1})
    else:
        topic_docs = db.counseling_topics.find({"counselors": chat_id}, {"topic": 1})

    topics = [doc["topic"] for doc in topic_docs]

    # Use message template from config
    dashboard_message = config["messages"]["counselor_dashboard"].format(
        name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
        pending=total_pending_requests,
        c_avail=total_counselors,
        requests=requests_answered,
        access="Global Access" if user.get("global") else "Assigned",
        topics=(
            "\n".join([f"• {t}" for t in topics]) if topics else "_No topics assigned._"
        ),
    )

    update_topic_keyboard = [
        [
            InlineKeyboardButton(
                "Update Topics",
                callback_data="update_topics=" + str(chat_id),
            )
        ]
    ]

    context.bot.send_message(
        chat_id=chat_id,
        text=dashboard_message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(update_topic_keyboard),
    )


def handle_counselor_verification(update, context):
    """
    Handles the verification of a counselor.
    """
    chat_id = Int64(update.effective_chat.id)
    password = update.message.text.strip()
    if password == os.getenv("COUNSELOR_PASSWORD"):
        db.users.update_one({"chat_id": chat_id}, {"$set": {"role": "counselor"}})
        keyboard = validate_user_keyboard(chat_id)
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_verified"],
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        set_user_last_command(chat_id, None)
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["counselor_verification_failed"],
        )


def handle_counselor_topic_update(update, context):
    """
    Handles the update of counseling topics for a counselor.
    """
    chat_id = Int64(update.effective_chat.id)
    user = db.users.find_one({"chat_id": chat_id})

    if not user or user.get("role") != "counselor":
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["not_counselor_prompt"],
        )
        db.users.update_one(
            {"chat_id": chat_id}, {"$set": {"last_command": "verify_counselor"}}
        )
        return

    # Fetch and display all topics
    topics = list(db.counseling_topics.find({}, {"topic": 1}))
    context.user_data["available_topics"] = topics  # Store temporarily

    message = config["messages"]["update_topics_prompt"] + "\n\n"
    for idx, topic in enumerate(topics, start=1):
        message += f"{idx}. {topic['topic']}\n"

    message += "\n" + config["messages"]["topic_selection_instruction"]

    db.users.update_one(
        {"chat_id": chat_id}, {"$set": {"last_command": "select_topics"}}
    )

    context.bot.send_message(chat_id=chat_id, text=message)


def handle_topic_selection(update, context):
    """
    Adds selected topics to the counselor's current assignments.
    """
    chat_id = Int64(update.effective_chat.id)
    user = db.users.find_one({"chat_id": chat_id})

    if not user or user.get("role") != "counselor":
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["not_counselor_prompt"]
        )
        return

    text = update.message.text.strip()
    selected_indexes = text.split(",")

    try:
        indexes = [int(i.strip()) for i in selected_indexes]
    except ValueError:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["invalid_topic_input"]
        )
        return

    topics = context.user_data.get("available_topics", [])
    selected_topics = []

    for i in indexes:
        if 1 <= i <= len(topics):
            selected_topics.append(topics[i - 1]["topic"])

    if not selected_topics:
        context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["no_valid_topics"]
        )
        return

    # ✅ Add to each selected topic (no removal)
    for topic_name in selected_topics:
        db.counseling_topics.update_one(
            {"topic": topic_name}, {"$addToSet": {"counselors": chat_id}}
        )

    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["topics_updated_confirmation"].format(
            topics=", ".join(selected_topics)
        ),
    )
