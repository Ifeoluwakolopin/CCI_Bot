from . import db, bot, config
from .keyboards import location_buttons, month_buttons
from concurrent.futures import ThreadPoolExecutor, as_completed
from .database import set_user_active
from telegram import InlineKeyboardMarkup, CallbackQuery


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

        user = db.users.find_one({"chat_id": chat_id})
        try:
            bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["lc"].format(user["first_name"]),
                reply_markup=InlineKeyboardMarkup(location_buttons),
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
        try:
            bot.send_message(
                chat_id=chat_id,
                text=config["messages"]["birthday_prompt"].format(user["first_name"]),
                reply_markup=InlineKeyboardMarkup(month_buttons),
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
