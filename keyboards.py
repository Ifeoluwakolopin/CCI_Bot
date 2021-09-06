from telegram import KeyboardButton

buttons = [
    KeyboardButton("latest sermon"),
    KeyboardButton("get sermon"),
]

buttons1 = [ 
    KeyboardButton("devotional"),
    KeyboardButton("map"),
    KeyboardButton("help"),
]

buttons3 = [
    KeyboardButton("statistics"),
    KeyboardButton("broadcast"),
]

normal_keyboard = [buttons, buttons1]
admin_keyboard = [buttons, buttons1, buttons3]