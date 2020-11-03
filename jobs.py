import time
import pymongo
import json
import telegram
import requests
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from sermons import cci_sermons, t30
from events import service_ticket
from apscheduler.schedulers.blocking import BlockingScheduler

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
                db.users.update_one({"chat_id", user["chat_id"]}, {"$set":{"active":False}})
    u = db.users.count_documents({"mute":False, "active":True})
    db.devotionals.insert_one(d)
    with open('jobs.log', 'a') as jl:
        jl.write("{0}:DEVOTIONAL: Sent devotional to {1} users".format(datetime.now(), u))
        jl.close()


@sched.scheduled_job('cron', day_of_week='mon-sun', hour=1)    
def insert_sermon():
    """
    Checks daily for new sermons from the site and inserts into
    db if any
    """
    sermons = cci_sermons()
    for sermon in sermons:
        if db.sermons.find_one({"title":sermon["title"]}) is not None:
            pass
        else:
            db.sermons.insert_one(sermon)
            with open('jobs.log', 'a') as jl:
                jl.write("{0}:SERMON: Inserted new sermon '{1}' to db".format(datetime.now(), sermon["title"]))
                jl.close()

def notify_tickets():
    """
    Send a notification to users and returns True on success
    """
    ticket = service_ticket()
    if len(ticket) == 2:
        buttons = [[InlineKeyboardButton("Book first service", url=ticket[0]["link"])],
            [InlineKeyboardButton("Book second service", url=ticket[1]["link"])]]
    else:
        buttons = [[InlineKeyboardButton("Reserve a seat", url=ticket[0]["link"])]]
    for user in db.users.find({"mute":False}):
        try:
            bot.send_photo(
                chat_id=user["chat_id"], photo=ticket[0]["image"], caption=config["messages"]["tickets"].format(ticket[0]["name"]), reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            if str(e) == "Forbidden: bot was blocked by the user":
                db.users.update_one({"chat_id", user["chat_id"]}, {"$set":{"active":False}})


@sched.scheduled_job('cron', day_of_week='wed', hour=11, minute=15)
def ticket_task():
    notify_tickets()
    u = db.users.count_documents({"mute":False, "active":True})
    with open('jobs.log', 'a') as jl:
        jl.write("{0}:TICKET: Notified {1} users".format(datetime.now(), u))
        jl.close()

@sched.scheduled_job('interval', minutes=25)
def wake():
    requests.get('https://secret-sands-37903.herokuapp.com/')
    print("Waking app...")
    


if __name__ == '__main__':
    sched.start()