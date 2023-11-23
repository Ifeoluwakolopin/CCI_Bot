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
    try:
        query = {
            "title": {"$regex": title, "$options": "i"}
        }  # Case-insensitive regex search
        result = list(db.sermons.find(query))
        return result
    except:
        return []


def insert_sermon(sermon: dict) -> bool:
    """
    This takes in a sermon and checks inserts the sermon into the
    database if it does not already exist.

    Keyword arguments:
    sermon -- dict: contains attributes that define a sermon

    Return: returns True or None if sermon exists in the database
    """

    if db.sermons.find_one({"title": sermon["title"]}) is not None:
        return False
    else:
        db.sermons.insert_one(sermon)
        logger.info("SERMON: Inserted new sermon '{0}' to db".format(sermon["title"]))
        return True


def update_counseling_topics(topic: str):
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


def get_church_locations() -> list:
    """
    This function returns a list of church locations from the database

    Keyword arguments:
    None

    Return: list of church locations
    """
    return list(db.church_locations.find())


def get_map_locations() -> list:
    """
    This function returns a list of map locations from the database

    Keyword arguments:
    None

    Return: list of map locations
    """
    return list(db.map_locations.find())


def get_all_counseling_topics() -> list:
    """
    Retrieves all 'topic' attributes from the 'counseling_topics' collection.

    Args:
        db: The MongoDB database instance.

    Returns:
        list: A list of all topics in the 'counseling_topics' collection.
    """
    topics = db.counseling_topics.find({}, {"topic": 1, "_id": 0})
    return [document["topic"] for document in topics]


def add_request_to_queue(counseling_request: dict) -> None:
    db.counseling_requests.insert_one(
        {
            "created": counseling_request["created"],
            "name": counseling_request["name"],
            "email": counseling_request["email"],
            "phone": counseling_request["phone"],
            "chat_id": counseling_request["chat_id"],
            "request_message_id": counseling_request["request_message_id"],
            "active": False,
            "note": counseling_request["note"],
            "status": "pending",
            "counselor_chat_id": None,
        }
    )


def get_active_counseling_requests(topic):
    requests = db.counseling_requests.find(
        {"active": True, "status": "pending", "topic": topic}
    ).sort("created", 1)
    return requests


def set_counseling_request_activity(request_id: str):
    db.counseling_requests.update_one(
        {"request_message_id": request_id}, {"$set": {"active": False}}
    )


def set_counseling_request_status(request_id: str, status: str):
    db.counseling_requests.update_one(
        {"request_message_id": request_id}, {"$set": {"status": status}}
    )


def get_top_five_requests():
    all_requests = get_active_counseling_requests()
    top_five = all_requests[0:5]
    return top_five
