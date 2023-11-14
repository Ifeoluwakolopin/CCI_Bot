from . import db, logger
from .models import BotUser
from .bot_types import Result


def set_user_last_command(chat_id: int, last_command: str | None) -> bool:
    """
    This sets the last_command field of a user to the current time.

    Keyword arguments:
    chat_id -- int: identifies a specific user
    last_command -- str: the last command the user used

    Return: True or False
    """
    try:
        if not last_command:
            db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})
        else:
            db.users.update_one(
                {"chat_id": chat_id}, {"$set": {"last_command": last_command}}
            )
        return True
    except:
        return False


def set_user_active(chat_id: int, active: bool) -> Result:
    """
    This sets the active field of a user to the current time.

    Keyword arguments:
    chat_id -- int: identifies a specific user
    active -- bool: True or False

    Return: True or False
    """
    try:
        db.users.update_one({"chat_id": chat_id}, {"$set": {"active": active}})
        return Result.SUCCESS
    except Exception as e:
        return Result.ERROR(e.__str__())


def add_user_to_db(user: BotUser) -> Result:
    """
    This adds a user to the database.

    Keyword arguments:
    user -- BotUser: an instance of the BotUser class

    Return: True or False
    """
    try:
        if not db.users.find_one({"chat_id": user.chat_id}):
            db.users.insert_one(user.__dict__)
            return Result.SUCCESS
        return Result.SKIPPED
    except Exception as e:
        return Result.ERROR(e.__str__())


def search_db_title(title: str) -> list:
    """
    This takes in a string and searches a MongoDB collection
    if the title is in the database.

    Keyword arguments:
    title -- string containing words to be searched.
    Return: list of documents containing title
    """
    query = {
        "title": {"$regex": title, "$options": "i"}
    }  # Case-insensitive regex search
    result = list(db.sermons.find(query))
    return result


def insert_sermon(sermon: dict):
    """
    This takes in a sermon and checks inserts the sermon into the
    database if it does not already exist.

    Keyword arguments:
    sermon -- dict: contains attributes that define a sermon

    Return: returns True or None if sermon exists in the database
    """

    if db.sermons.find_one({"title": sermon["title"]}) is not None:
        return None
    else:
        db.sermons.insert_one(sermon)
        logger.info("SERMON: Inserted new sermon '{0}' to db".format(sermon["title"]))
        return True


def add_topic_to_db(topic: str):
    """
    This takes in a topic and adds it to the database if it does not

    Keyword arguments:
    topic -- str: contains the topic to be added to the database

    Return: None

    """

    if not db.counseling_topics.find_one({"topic": topic}):
        db.counseling_topics.insert_one({"topic": topic, "faqs": [], "count": 1})
    else:
        db.counseling_topics.update_one({"topic": topic}, {"$inc": {"count": 1}})
