import requests
from datetime import datetime, timedelta
from bot import bot, db, config, logger
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.blocking import BlockingScheduler
from bot.commands import notify_new_sermon
from bot.database import insert_sermon
from bot.scrapers import WebScrapers
from bot.helpers import MessageHelper, BroadcastHandlers

sched = BlockingScheduler()


@sched.scheduled_job("cron", day_of_week="mon-sun", hour=23, minute=0)
def birthday_notifier():
    """
    This function sends out daily notifications to users on their birthdays.
    """
    # Calculate tomorrow's date
    tomorrow = datetime.today() + timedelta(days=1)
    date_str = f"{tomorrow.month}-{tomorrow.day}"

    # Find users whose birthdays match tomorrow's date
    birthday_users = db.users.find({"birthday": date_str})
    users_with_birthdays = list(birthday_users)

    # Prepare the message and photo for each user
    photo_path = "img/birthday.jpg"
    messages = [
        {
            "chat_id": user["chat_id"],
            "photo": photo_path,
            "caption": config["messages"]["birthday_message1"].format(
                user["first_name"]
            ),
        }
        for user in users_with_birthdays
    ]

    # Use BroadcastHandlers to send the messages
    for message in messages:
        BroadcastHandlers.broadcast_message(
            [message["chat_id"]],  # List containing one user's chat ID
            message["photo"],
            MessageHelper.send_photo,
            message["caption"],
        )

    # Log the number of birthday wishes sent
    logger.info(f"BIRTHDAY: Sent {len(users_with_birthdays)} birthday wishes")


@sched.scheduled_job("cron", day_of_week="mon-sun", hour=6)
def new_sermons():
    """
    This functions updates the latest sermon and notifies users about the new sermon

    Keyword arguments:
    kwargs -- None

    Return: None
    """

    sermons = WebScrapers.cci_sermons()
    titles = []
    for sermon in sermons:
        if insert_sermon(sermon) is True:
            titles.append(sermon)
    if len(titles) > 0:
        lsermon = titles[0]
        lsermon["latest_sermon"] = True
        db.temporary.delete_one({"latest_sermon": True})
        db.temporary.insert_one(lsermon)
        logger.info("Updated latest Sermon to {}".format(lsermon["title"]))
        t = [i["title"] for i in titles]
        for user in db.users.find({}):
            notify_new_sermon(user["chat_id"], t)


numbers = {1: "first", 2: "second", 3: "third"}


@sched.scheduled_job("cron", day_of_week="sat", hour=6)
def check_feedback():
    feedback = db.feedback.find({"status": "pending"})
    if feedback:
        bot.send_message(
            chat_id=792501227, text=config["messages"]["feedback_notifier"]
        )


def notify_tickets():
    """
    This function sends a notification to every active user about an upcoming
    event

    Keyword arguments:
    argument -- None

    Return: None
    """

    d = (datetime.today() + timedelta(days=4)).date()
    date = str(d)
    ticket = WebScrapers.service_ticket(date, date)
    buttons = [
        [
            InlineKeyboardButton(
                "Register for {} service".format(numbers[ticket.index(service) + 1]),
                url=service["link"],
            )
        ]
        for service in ticket[0:2]
    ]
    users = db.users.find(
        {
            "$or": [
                {"location": {"$in": ["Ikeja", "Lekki", "Online", "None"]}},
                {"location": {"$exists": False}},
            ]
        }
    )
    for user in users:
        try:
            bot.send_photo(
                chat_id=user["chat_id"],
                photo=ticket[0]["image"],
                caption=config["messages"]["tickets"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as e:
            pass


# @sched.scheduled_job('cron', day_of_week='mon-sat', hour=5)
def send_devotional():
    """
    This sends the current devotional of the day to all active
    users.

    Keyword arguments:
    argument -- None

    Return: None
    """
    d = WebScrapers.t30()
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    for user in db.users.find({"mute": False}):
        try:
            bot.send_photo(
                chat_id=user["chat_id"],
                photo=d["image"],
                caption=config["messages"]["t30_caption"].format(
                    d["title"], d["excerpt"].split("\n")[0]
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
        except Exception as e:
            # sets the user as inactive if telegram throws an exception.
            if str(e) == "Forbidden: bot was blocked by the user":
                db.users.update_one(
                    {"chat_id": user["chat_id"]}, {"$set": {"active": False}}
                )
            pass
    u = db.users.count_documents({"mute": False, "active": True})
    db.devotionals.insert_one(d)
    logger.info(f"DEVOTIONAL: Sent devotional to {u} users")


# @sched.scheduled_job('cron', day_of_week='wed', hour=12)
def ticket_task():
    """
    This runs the ticket notifier function and logs results.

    Keyword arguments:
    argument -- None

    Return: None
    """
    notify_tickets()
    u = db.users.count_documents({"mute": False, "active": True})
    logger.info(f"TICKET: Notified {u} users")


@sched.scheduled_job("interval", minutes=29)
def wake():
    """
    This sends a request to the bot server to allow it maintain activity

    Keyword arguments:
    argument -- None

    Return: None
    """
    requests.get("https://cci-bot.herokuapp.com/")


if __name__ == "__main__":
    sched.start()
