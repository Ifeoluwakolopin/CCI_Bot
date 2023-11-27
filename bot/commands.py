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

    # Create and add user to database
    user = BotUser(chat_id, first_name, last_name)
    add_user_to_db(user)

    # Set user as active
    set_user_active(chat_id, True)

    # Determine keyboard based on user status
    keyboard = validate_user_keyboard(chat_id)

    # Send welcome message
    send_welcome_message(chat_id, first_name, context.bot, keyboard)

    # Trigger additional prompts
    trigger_additional_prompts(chat_id)


def send_welcome_message(chat_id, first_name, bot, keyboard):
    """
    Sends a welcome message to the user.

    Args:
        chat_id (int): The chat ID of the user.
        first_name (str): The first name of the user.
        bot (Bot): The bot instance.
        keyboard (list): The keyboard to be sent with the message.
    """
    welcome_message = config["messages"]["start"].format(first_name)
    bot.send_message(
        chat_id=chat_id,
        text=welcome_message,
        parse_mode="Markdown",
        disable_web_page_preview="True",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


def trigger_additional_prompts(chat_id):
    """
    Triggers additional prompts for the user.

    Args:
        chat_id (int): The chat ID of the user.
    """
    # TODO: uncomment when location prompt is ready
    user = db.users.find_one({"chat_id": chat_id})
    PromptHelper.location_prompt(
        chat_id, config["messages"]["lc"].format(user["first_name"])
    )
    # PromptHelper.birthday_prompt(chat_id)


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
        {"chat_id": int(user_id), "role": "pastor"}
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


def handle_broadcast(update):
    """
    Handles the broadcast action based on the admin's response.
    """
    chat_id = update.effective_chat.id
    message = update.message
    user = db.users.find_one({"chat_id": chat_id, "admin": True})
    if not user or user.get("last_command") != "broadcast":
        return

    # Fetch all users to broadcast to
    users = db.users.find({"active": True})

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

    # Reset last_command after broadcast
    set_user_last_command(chat_id, None)


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
                    [
                        InlineKeyboardButton(
                            "Send to specific users", callback_data="bc=specific"
                        )
                    ],
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

    try:
        if user["last_command"].startswith("in-conversation-with"):
            end_conversation_prompt(update, context)
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
        else:
            # cancel any other action
            context.bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["cancel"],
                parse_mode="Markdown",
                disable_web_page_preview="True",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            set_user_last_command(chat_id, None)
    except:
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

        if db.users.find_one({"chat_id": chat_id, "role": "pastor"}):
            db.users.update_one(
                {"chat_id": chat_id}, {"$addToSet": {"locations": branch}}
            )
        db.users.update_one({"chat_id": chat_id}, {"$set": {"location": branch}})
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc_done"].format(branch),
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
