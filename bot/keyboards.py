from . import db
from telegram import KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

sermon_buttons = [
    KeyboardButton("latest sermon"),
    KeyboardButton("get sermon"),
]

buttons1 = [
    # TODO: Uncomment when MAP is properly fixed
    # KeyboardButton("map"),
    KeyboardButton("help"),
]

buttons3 = [
    KeyboardButton("statistics"),
    KeyboardButton("broadcast"),
]

bc_buttons = [
    [
        KeyboardButton("text"),
        KeyboardButton("video"),
    ],
    [KeyboardButton("photo"), KeyboardButton("animation")],
    [KeyboardButton("How to broadcast")],
]

counselor_keyboard = [KeyboardButton("Show Active Counseling Requests")]

counselor_keyboard2 = [
    KeyboardButton("/transfer"),
]

counseling_buttons = [
    KeyboardButton("counseling"),
]

categories_keyboard = [
    [
        InlineKeyboardButton("Spiritual Growth", callback_data="cat=" + "sg"),
        InlineKeyboardButton("Relationships", callback_data="cat=" + "r"),
    ],
    [
        InlineKeyboardButton("Career", callback_data="cat=" + "car"),
        InlineKeyboardButton("Mental Wellbeing", callback_data="cat=" + "mw"),
    ],
    [
        InlineKeyboardButton("Habits and Addictions", callback_data="cat=" + "ha"),
        InlineKeyboardButton("Marriage and Family", callback_data="cat=" + "mf"),
    ],
]

month_buttons = [
    [
        InlineKeyboardButton("January", callback_data="bd=1"),
        InlineKeyboardButton("February", callback_data="bd=2"),
        InlineKeyboardButton("March", callback_data="bd=3"),
    ],
    [
        InlineKeyboardButton("April", callback_data="bd=4"),
        InlineKeyboardButton("May", callback_data="bd=5"),
        InlineKeyboardButton("June", callback_data="bd=6"),
    ],
    [
        InlineKeyboardButton("July", callback_data="bd=7"),
        InlineKeyboardButton("August", callback_data="bd=8"),
        InlineKeyboardButton("September", callback_data="bd=9"),
    ],
    [
        InlineKeyboardButton("October", callback_data="bd=10"),
        InlineKeyboardButton("November", callback_data="bd=11"),
        InlineKeyboardButton("December", callback_data="bd=12"),
    ],
]
ask_question_or_counseling_keyboard = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Ask a question", callback_data="qa_or_c=" + str(0))],
        [
            InlineKeyboardButton(
                "Speak to a Counselor", callback_data="qa_or_c=" + str(1)
            )
        ],
    ],
    resize_keyboard=True,
)
location_buttons = []

normal_keyboard = [sermon_buttons, buttons1 + counseling_buttons]
pastor_keyboard = normal_keyboard + [counselor_keyboard, counselor_keyboard2]
admin_keyboard = pastor_keyboard + [buttons3]

keyboard_commands = [
    "latest sermon",
    "get sermon",
    "map",
    "help",
    "reboot camp",
    "statistics",
    "broadcast",
    "show active counseling requests",
    "counseling",
]


def validate_user_keyboard(chat_id) -> list:
    """
    This takes in a user id and returns the right keyboard for the user.

    Keyword arguments:
    chat_id -- user's telegram chat_id
    Return: returns correct keyboard for user
    """
    user = db.users.find_one({"chat_id": chat_id})
    if user["admin"] == True:
        return admin_keyboard
    elif user["role"] == "pastor":
        return pastor_keyboard
    else:
        return normal_keyboard
