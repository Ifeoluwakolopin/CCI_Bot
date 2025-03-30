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
    KeyboardButton("location"),
]

counseling_button = [
    KeyboardButton("counseling"),
]

buttons3 = [
    KeyboardButton("statistics"),
    KeyboardButton("broadcast"),
    KeyboardButton("find user"),
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


normal_keyboard = [sermon_buttons, buttons1]
pastor_keyboard = (
    [counseling_button] + normal_keyboard + [counselor_keyboard, counselor_keyboard2]
)
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


def get_counseling_feedback_keyboard(user_chat_id, pastor_chat_id):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "1",
                    callback_data="counseling_feedback=1="
                    + str(user_chat_id)
                    + "="
                    + str(pastor_chat_id),
                ),
                InlineKeyboardButton(
                    "2",
                    callback_data="counseling_feedback=2="
                    + str(user_chat_id)
                    + "="
                    + str(pastor_chat_id),
                ),
                InlineKeyboardButton(
                    "3",
                    callback_data="counseling_feedback=3="
                    + str(user_chat_id)
                    + "="
                    + str(pastor_chat_id),
                ),
                InlineKeyboardButton(
                    "4",
                    callback_data="counseling_feedback=4="
                    + str(user_chat_id)
                    + "="
                    + str(pastor_chat_id),
                ),
                InlineKeyboardButton(
                    "5",
                    callback_data="counseling_feedback=5="
                    + str(user_chat_id)
                    + "="
                    + str(pastor_chat_id),
                ),
            ]
        ],
        resize_keyboard=True,
    )
