from telegram import KeyboardButton, InlineKeyboardButton

sermon_buttons = [
    KeyboardButton("latest sermon"),
    KeyboardButton("get sermon"),
]

buttons1 = [
    KeyboardButton("map"),
    KeyboardButton("help"),
]

buttons2 = [
    KeyboardButton("Reboot Camp")
]

buttons3 = [
    KeyboardButton("statistics"),
    KeyboardButton("broadcast"),
]

bc_buttons = [
    [
        KeyboardButton("text"),
        KeyboardButton("video"),
        KeyboardButton("photo")
    ],
    [
        KeyboardButton("animation"),
        KeyboardButton("usage")
    ]
]

counseling_buttons =[
    KeyboardButton("counseling"),
]

categories_keyboard = [
    [KeyboardButton("Love"), KeyboardButton("Joy")],
    [KeyboardButton("Hope"), KeyboardButton("Grief")],
    [KeyboardButton("Wisdom"), KeyboardButton("Marriage")],
]

normal_keyboard = [sermon_buttons, buttons1]
admin_keyboard = [sermon_buttons, buttons1, buttons3]