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

    # Update the last command with a general broadcast tag
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": "broadcast"}})


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
    button = [[InlineKeyboardButton("Read blog posts", url="https://ccing.org/blogs/")]]
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["blog_posts"],
        reply_markup=InlineKeyboardMarkup(button),
    )
    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
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


def campuses(update, context):
    """
    This gives a list of church campuses.
    """
    chat_id = update.effective_chat.id
    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
        # TODO: Handle church location prompt
        pass


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
            db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})
    except:
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["cancel"],
            parse_mode="Markdown",
            disable_web_page_preview="True",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


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
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


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
    button = [
        [InlineKeyboardButton("Register", url="https://ccing.org/membership-class/")]
    ]
    context.bot.send_photo(
        chat_id=chat_id,
        photo=open("img/membership.jpg", "rb"),
        caption=config["messages"]["membership"],
        reply_markup=InlineKeyboardMarkup(button),
    )
    if check_user_in_conversation(chat_id):
        notify_in_conversation(chat_id)
    else:
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
        db.users.update_one({"chat_id": chat_id}, {"$set": {"active": False}})


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
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


def reboot_about(update, context):
    chat_id = update.effective_chat.id
    keyboard = validate_user_keyboard(chat_id)
    context.bot.send_message(
        chat_id=chat_id,
        text=config["messages"]["reboot_camp"]["about"],
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


def set_church_location(update, context):
    """
    This function sets the church location for a user
    """
    chat_id = update.effective_chat.id
    church_locations = get_church_locations()
    countries = [location["locationName"] for location in church_locations]

    user = db.users.find_one({"chat_id": chat_id})
    rows, cols = 3, 2
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
    church_locations = get_church_locations()
    countries = [location["locationName"] for location in church_locations]
    rows, cols = 3, 2

    if query_data[1] == "more":
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
        location = find_text_for_callback(update.callback_query).lower()
        db.users.update_one({"chat_id": chat_id}, {"$set": {"location": location}})
        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["lc_done"].format(location),
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
        location_based_stats = ""
        birthdays = db.users.count_documents({"birthday": {"$exists": True}})
        today = datetime.today()
        x = str(today.month) + "-" + str(today.day)
        todays_birthdays = db.users.count_documents({"birthday": x})

        for loc in db.users.distinct("location"):
            loc_count = db.users.count_documents({"location": loc})
            location_based_stats += loc + " users: " + str(loc_count)
            location_based_stats += "\n"

        context.bot.send_message(
            chat_id=chat_id,
            text=config["messages"]["stats"].format(
                total_users,
                active_users,
                mute_users,
                total_sermons,
                location_based_stats,
                birthdays,
                todays_birthdays,
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
