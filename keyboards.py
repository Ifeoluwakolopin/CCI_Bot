from telegram import KeyboardButton

buttons = [
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

bc_btns = [[
    KeyboardButton("text"),
    KeyboardButton("video"),
    KeyboardButton("photo")],
    [
        KeyboardButton("animation"),
        KeyboardButton("usage")
    ]
]

normal_keyboard = [buttons, buttons1]
admin_keyboard = [buttons, buttons1, buttons3]