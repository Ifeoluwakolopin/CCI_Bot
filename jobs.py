from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, config, db, logger
from bot.commands import notify_new_sermon
from bot.database import insert_sermon
from bot.helpers import BroadcastHandlers, MessageHelper
from bot.scrapers import WebScrapers
from bot.settings import env_or_config, int_env_or_config, list_env_or_config

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
    photo_path = env_or_config(
        config, "BIRTHDAY_PHOTO_PATH", ("assets", "birthday_photo_path"), ""
    )
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
    feedback_chat_id = int_env_or_config(
        config, "FEEDBACK_CHAT_ID", ("jobs", "feedback_chat_id")
    )
    if feedback_chat_id and db.feedback.count_documents({"status": "pending"}):
        bot.send_message(
            chat_id=feedback_chat_id, text=config["messages"]["feedback_notifier"]
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
    if not ticket:
        logger.info("No service tickets found for %s", date)
        return
    buttons = [
        [
            InlineKeyboardButton(
                f"Register for {numbers[ticket.index(service) + 1]} service",
                url=service["link"],
            )
        ]
        for service in ticket[0:2]
    ]
    ticket_locations = list_env_or_config(
        config,
        "TICKET_LOCATION_FILTER",
        ("locations", "ticket_notification_locations"),
    )
    location_filters = [{"location": {"$exists": False}}]
    if ticket_locations:
        location_filters.insert(0, {"location": {"$in": ticket_locations}})
    users = db.users.find(
        {
            "$or": location_filters,
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
        except Exception:
            logger.exception(
                "Failed to send ticket notification to chat_id=%s", user.get("chat_id")
            )


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
            logger.exception(
                "Failed to send devotional to chat_id=%s", user.get("chat_id")
            )
    u = db.users.count_documents({"mute": False, "active": True})
    db.devotionals.insert_one(d)
    logger.info(f"DEVOTIONAL: Sent devotional to {u} users")


if __name__ == "__main__":
    sched.start()
