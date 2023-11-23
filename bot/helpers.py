from . import db, bot, config
from concurrent.futures import ThreadPoolExecutor, as_completed
from .database import set_user_active
from telegram import InlineKeyboardMarkup, CallbackQuery, InlineKeyboardButton


def find_text_for_callback(callback_query: CallbackQuery) -> str | None:
    """
    Searches for the text associated with the callback_data within a callback_query object.

    The function iterates through the 'inline_keyboard' of the 'reply_markup' in the 'message'
    part of the callback_query to find a button whose 'callback_data' matches the callback_data in
    the callback_query. If found, it returns the 'text' of that button. If no matching callback_data is found,
    it returns None.

    Args:
        callback_query (CallbackQuery): The callback query object received from the Telegram API.

    Returns:
        str | None: The text of the button that matches the callback_data, or None if no match is found.
    """
    callback_data = callback_query.data
    inline_keyboard = callback_query.message.reply_markup.inline_keyboard

    for row in inline_keyboard:
        for button in row:
            if button.callback_data == callback_data:
                return button.text
    return None


def create_buttons_from_data(
    data: list, callback_info: str, rows: int, cols: int, start_index: int = 0
) -> InlineKeyboardMarkup:
    """
    Creates a list of InlineKeyboardButtons from the provided data, displaying a limited number of items at a time.
    Includes a 'View More' button to navigate through additional items.

    Args:
        data (list): The list of data items from the database.
        callback_info (str): Base information to be included in the callback data of each button.
        rows (int): Number of rows for the button layout.
        cols (int): Number of columns for the button layout.
        start_index (int): The starting index from the data list to display the buttons.

    Returns:
        InlineKeyboardMarkup: The InlineKeyboardMarkup object with the created buttons.
    """
    buttons = []
    total_buttons = rows * cols
    end_index = start_index + total_buttons
    data_len = len(data)

    # Limit end_index to the length of the data
    end_index = min(end_index, data_len)

    for idx, item in enumerate(data[start_index:end_index], start=start_index):
        row_idx = (idx - start_index) // cols
        if len(buttons) <= row_idx:
            buttons.append([])

        button_text = str(item)
        callback_data = f"{callback_info}={idx}"
        buttons[row_idx].append(
            InlineKeyboardButton(button_text, callback_data=callback_data)
        )

    # Add 'View More' button if there are more items to display
    if data_len > end_index:
        view_more_callback_data = f"{callback_info}=more={end_index}"
        buttons.append(
            [InlineKeyboardButton("View More", callback_data=view_more_callback_data)]
        )

    return InlineKeyboardMarkup(buttons, resize_keyboard=True)


def handle_view_more(
    callback_query: dict, data: list, callback_info: str, rows: int, cols: int
) -> InlineKeyboardMarkup:
    """
    Handles the 'View More' button click, generating the next set of buttons from the data.

    Args:
        callback_query (dict): The callback query received from the Telegram API.
        data (list): The list of data items from the database.
        callback_info (str): Base information to be included in the callback data of each button.
        rows (int): Number of rows for the button layout.
        cols (int): Number of columns for the button layout.

    Returns:
        InlineKeyboardMarkup: The InlineKeyboardMarkup object with the next set of created buttons.
    """
    # Extract the last index from the callback data
    last_index_str = callback_query.data.split("=")[-1]
    last_index = int(last_index_str)

    # Generate the next set of buttons starting from the last index
    return create_buttons_from_data(
        data, callback_info, rows, cols, start_index=last_index
    )


class PromptHelper:
    @staticmethod
    def location_prompt(chat_id: int) -> None:
        """
        This functions takes in a chat id, and sends a message
        to request for the user's physical church location.

        Keyword arguments:
        chat_id -- identifies a specific user
        Return: None
        """
        # TODO: check church location schema and fix.
        user = db.users.find_one({"chat_id": chat_id})
        locations = db.church_locations.find({})
        keyboard = create_buttons_from_data(locations, "loc", 3, 1)
        try:
            bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["lc"].format(user["first_name"]),
                reply_markup=keyboard,
                resize_keyboard=True,
            )
        except:
            set_user_active(chat_id, False)

    @staticmethod
    def birthday_prompt(chat_id):
        """
        This functions takes in a chat id, and gets the birthdate
        of a particular user

        Keyword arguments:
        chat_id -- identifies a specific user
        Return: None
        """
        user = db.users.find_one({"chat_id": chat_id})
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        buttons = create_buttons_from_data(
            months, callback_info="bd", rows=3, cols=4, start_index=1
        )
        try:
            bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_prompt"].format(user["first_name"]),
                reply_markup=buttons,
            )
        except:
            set_user_active(chat_id, False)


class MessageHelper:
    @staticmethod
    def send_text(chat_id: int, message: str) -> bool:
        """
        This takes in a user's id and a message string. It sends the
        associated user the message via the Telegram Bot API

        Keyword arguments:
        chat_id -- identifies a specific user
        message -- str: input message to be sent

        Return: None or True
        """
        try:
            bot.send_message(
                chat_id=chat_id, text=message, disable_web_page_preview="True"
            )
            return True
        except:
            return False

    @staticmethod
    def send_photo(chat_id: int, photo, caption: str = "") -> bool:
        """
        This takes in an ID, photo and caption. It sends the associated
        user the photo with the given caption via the Telegram Bot API

        Keyword arguments:
        chat_id -- identifies a specific user
        photo -- str: link or path to a picture
        caption -- str: text to associate with the picture

        Return: None or True
        """
        try:
            bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            return True
        except:
            return False

    @staticmethod
    def send_animation(chat_id: int, animation, caption: str = "") -> bool:
        """
        This takes in an ID, animation and caption. It sends the associated
        user the animation with the given caption via the Telegram Bot API

        Keyword arguments:
        chat_id -- identifies a specific user
        animation -- str: link or path to the animation
        caption -- str: text to associate with the animation

        Return: None or True
        """
        try:
            bot.send_animation(chat_id=chat_id, animation=animation, caption=caption)
            return True
        except:
            return False

    @staticmethod
    def send_video(chat_id, video, caption=""):
        """
        This takes in an ID, video and caption. It sends the associated
        user the photo with the given caption via the Telegram Bot API

        Keyword arguments:
        chat_id -- identifies a specific user
        video -- str: link or path to the video
        caption -- str: text to associate with the video

        Return: None or True
        """
        try:
            bot.send_video(chat_id=chat_id, video=video, caption=caption)
            return True
        except:
            return False


class BroadcastHandlers:
    @staticmethod
    def broadcast_message(users, content, send_function, *args):
        """
        Generic method for broadcasting messages (text, photo, animation, video) to users.

        Parameters:
        users -- list of users to send the message to
        content -- the message or media content to send
        send_function -- function from MessageHelper to send the message
        *args -- additional arguments required by the send_function
        """

        def worker(chat_id):
            try:
                return send_function(chat_id, content, *args), None
            except Exception as e:
                set_user_active(chat_id, False)
                return False, e

        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map of future to user chat_id
            future_to_chat_id = {
                executor.submit(worker, user["chat_id"]): user["chat_id"]
                for user in users
            }
            for future in as_completed(future_to_chat_id):
                chat_id = future_to_chat_id[future]
                success, error = future.result()
                if error:
                    print(f"Error sending message to {chat_id}: {str(error)}")
