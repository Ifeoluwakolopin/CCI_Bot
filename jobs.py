import requests
from datetime import datetime, timedelta
from helpers import *
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from sermons import cci_sermons, t30
from events import service_ticket
from apscheduler.schedulers.blocking import BlockingScheduler
from bot import notify_new_sermon

sched = BlockingScheduler()

@sched.scheduled_job('cron', day_of_week='mon-sun', hour=23, minute=00)
def birthday_notifier():
    """
    This functions sends out daily notifications to users
    on their birthdays
    
    Keyword arguments:
    None - None

    Return: None
    """
    # Calculates the current date
    tommorow = datetime.today() + timedelta(days=1)
    x = str(tommorow.month)+'-'+str(tommorow.day)
    # Finds users in the database whose birthdays match the current date
    birthdays = db.users.find({"birthday":x})
    sent = 0
    for user in birthdays:
        try:
            bot.send_photo(
                chat_id=user["chat_id"], photo=open("img/birthday.jpg", "rb"),
                caption=config["messages"]["birthday_message1"].format(user["first_name"])
            )
            sent += 1
        except:
            pass
    logger.info("BIRTHDAY: Sent {sent} birthday wishes")


def insert_sermon(sermon):
    """
    This takes in
    
    Keyword arguments:
    argument -- description
    Return: return_description
    """
    
    if db.sermons.find_one({"title":sermon["title"]}) is not None:
        return None
    else:
        db.sermons.insert_one(sermon)
        logger.info("SERMON: Inserted new sermon '{0}' to db".format(sermon["title"]))
        return True

@sched.scheduled_job('cron', day_of_week='mon-sun', hour=6)
def new_sermons():
    sermons = cci_sermons()
    titles = []
    for sermon in sermons:
        if insert_sermon(sermon) is True:
            titles.append(sermon)
    if len(titles) > 0:
        lsermon = titles[0]
        lsermon["latest_sermon"] = True
        db.temporary.delete_one({"latest_sermon":True})
        db.temporary.insert_one(lsermon)
        logger.info("Updated latest Sermon to {}".format(lsermon["title"]))
        t = [i["title"] for i in titles]
        for user in db.users.find({}):
            notify_new_sermon(user["chat_id"], t)

numbers = {1:"first", 2:"second", 3:"third"}

def notify_tickets():
    """
    Send a notification to users and returns True on success
    """
    d = (datetime.today()+timedelta(days=4)).date()
    date=str(d)
    ticket = service_ticket(date, date)
    buttons =[[InlineKeyboardButton("Register for {} service".format(numbers[ticket.index(service)+1]), url=service["link"])] for service in ticket[0:2]]
    users = db.users.find({"$or":[
                {"location":{"$in":["Ikeja", "Lekki", "Online", "None"]}},
                {"location":{"$exists":False}}
            ]})
    for user in users:
        try:
            bot.send_photo(
                chat_id=user["chat_id"], photo=ticket[0]["image"], caption=config["messages"]["tickets"], 
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            pass

#@sched.scheduled_job('cron', day_of_week='mon-sat', hour=5)
def send_devotional():
    d = t30()
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    for user in db.users.find({"mute":False}):
        try:
            bot.send_photo(
                chat_id=user["chat_id"], photo=d["image"],
                caption=config["messages"]["t30_caption"].format(d["title"], d["excerpt"].split("\n")[0]),
                reply_markup=InlineKeyboardMarkup(button)
            )
        except Exception as e:
            if str(e) == "Forbidden: bot was blocked by the user":
                db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"active":False}})
            pass
    u = db.users.count_documents({"mute":False, "active":True})
    db.devotionals.insert_one(d)
    logger.info(f"DEVOTIONAL: Sent devotional to {u} users")

#@sched.scheduled_job('cron', day_of_week='wed', hour=12)
def ticket_task():
    notify_tickets()
    u = db.users.count_documents({"mute":False, "active":True})
    logger.info(f"TICKET: Notified {u} users")

@sched.scheduled_job('interval', minutes=29)
def wake():
    requests.get('https://cci-bot.herokuapp.com/')