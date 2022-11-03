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
    ],
    [
        KeyboardButton("photo"),
        KeyboardButton("animation")
    ],
    [
        KeyboardButton("How to broadcast")
    ]
]

counselor_keyboard = [
    KeyboardButton("Show Active Counseling Requests")
]

counselor_keyboard2 = [
    KeyboardButton("/transfer"),
]

counseling_buttons =[
    KeyboardButton("counseling"),
]

categories_keyboard = [
    [KeyboardButton("Spiritual Growth"), KeyboardButton("Relationships")],
    [KeyboardButton("Career"), KeyboardButton("Mental Wellbeing")],
    [KeyboardButton("Habits and Addictions"), KeyboardButton("Marriage and Family")]
]

location_buttons = [
        [InlineKeyboardButton("Lagos - Ikeja", callback_data="loc=Ikeja"),
        InlineKeyboardButton("Lagos - Lekki", callback_data="loc=Lekki")],
        [InlineKeyboardButton("Lagos - Yaba", callback_data="loc=Yaba"),
        InlineKeyboardButton("Ile-Ife", callback_data="loc=Ile-ife")],
        [InlineKeyboardButton("Ibadan", callback_data="loc=Ibadan"),
        InlineKeyboardButton("PortHarcourt", callback_data="loc=PH")],
        [InlineKeyboardButton("Canada", callback_data="loc=Canada"),
        InlineKeyboardButton("Abuja", callback_data="loc=Abuja")],
        [InlineKeyboardButton("United Kingdom(UK)", callback_data="loc=UK")],
        [InlineKeyboardButton("Online Member", callback_data="loc=Online"),
        InlineKeyboardButton("None", callback_data="loc=None")]
    ]

bc_location_buttons = [
        [InlineKeyboardButton("Lagos - Ikeja", callback_data="bc-to=Ikeja"),
        InlineKeyboardButton("Lagos - Lekki", callback_data="bc-to=Lekki")],
        [InlineKeyboardButton("Lagos - Yaba", callback_data="bc-to=Yaba"),
        InlineKeyboardButton("Ile-Ife", callback_data="bc-to=Ile-ife")],
        [InlineKeyboardButton("Ibadan", callback_data="bc-to=Ibadan"),
        InlineKeyboardButton("PortHarcourt", callback_data="bc-to=PH")],
        [InlineKeyboardButton("Canada", callback_data="bc-to=Canada"),
        InlineKeyboardButton("Abuja", callback_data="bc-to=Abuja")],
        [InlineKeyboardButton("United Kingdom(UK)", callback_data="bc-to=UK")],
        [InlineKeyboardButton("Online Member", callback_data="bc-to=Online"),
        InlineKeyboardButton("None", callback_data="bc-to=None")],
        [InlineKeyboardButton("Done", callback_data="bc-to=done")]
    ]

month_buttons = [
        [InlineKeyboardButton("January", callback_data="bd=1"),
        InlineKeyboardButton("February", callback_data="bd=2"),
        InlineKeyboardButton("March", callback_data="bd=3")],
        [InlineKeyboardButton("April", callback_data="bd=4"),
        InlineKeyboardButton("May", callback_data="bd=5"),
        InlineKeyboardButton("June", callback_data="bd=6")],
        [InlineKeyboardButton("July", callback_data="bd=7"),
        InlineKeyboardButton("August", callback_data="bd=8"),
        InlineKeyboardButton("September", callback_data="bd=9")],
        [InlineKeyboardButton("October", callback_data="bd=10"),
        InlineKeyboardButton("November", callback_data="bd=11"),
        InlineKeyboardButton("December", callback_data="bd=12")]
    ]

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

normal_keyboard = [sermon_buttons, buttons1]
admin_keyboard = [sermon_buttons, buttons1, buttons3, counselor_keyboard, counselor_keyboard2]
pastor_keyboard = [
    sermon_buttons, buttons1, 
    counselor_keyboard, counselor_keyboard2
]