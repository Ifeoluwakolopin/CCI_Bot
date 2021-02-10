import pymongo
import json
import telegram
import requests
from datetime import datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from sermons import cci_sermons, t30
from events import service_ticket
from apscheduler.schedulers.blocking import BlockingScheduler
from bot import notify_new_sermon

config = json.load(open("config.json"))

client = pymongo.MongoClient(config["db"]["client"])
db = client[config["db"]["name"]]
bot = telegram.Bot(token=config["bot_token"])

sched = BlockingScheduler()

@sched.scheduled_job('cron', day_of_week='mon-sat', hour=5)
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
        db.users.update_one({"chat_id":user["chat_id"]}, {"$set":{"last_command":None}})
    u = db.users.count_documents({"mute":False, "active":True})
    db.devotionals.insert_one(d)
    print(f"DEVOTIONAL: Sent devotional to {u} users")

def insert_sermon(sermon):
    """
    Insert new sermons into db
    """
    if db.sermons.find_one({"title":sermon["title"]}) is not None:
        return None
    else:
        db.sermons.insert_one(sermon)
        print("SERMON: Inserted new sermon '{0}' to db".format(sermon["title"]))
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
        print("Updated latest Sermon to {}".format(lsermon["title"]))
        t = [i["title"] for i in titles]
        for user in db.users.find({}):
            notify_new_sermon(user["chat_id"], t)

numbers = {1:"first", 2:"second", 3:"third"}

def notify_tickets():
    """
    Send a notification to users and returns True on success
    """
    if len(service_ticket()) > 3:
        ticket = service_ticket()[0:2]
    else:
        ticket = service_ticket()
    buttons =[[InlineKeyboardButton("Register for {} service".format(numbers[ticket.index(service)+1]), url=service["link"])] for service in ticket]
    for user in db.users.find({"mute":False}):
        try:
            bot.send_photo(
                chat_id=user["chat_id"], photo=ticket[0]["image"], caption=config["messages"]["tickets"].format(ticket[0]["name"]), reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            if str(e) == "Forbidden: bot was blocked by the user":
                #db.users.update_one({"chat_id", user["chat_id"]}, {"$set":{"active":False}})
                pass


@sched.scheduled_job('cron', day_of_week='wed', hour=12)
def ticket_task():
    notify_tickets()
    u = db.users.count_documents({"mute":False, "active":True})
    print(f"TICKET: Notified {u} users")

@sched.scheduled_job('interval', seconds=30)
def wake():
    #requests.get('https://secret-sands-37903.herokuapp.com/')
    print("done")

#@sched.scheduled_job('cron', day_of_week='mon-sun', hour=23)
def birthday_notifier():
    pass

if __name__ == '__main__':
    sched.start()