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


@sched.scheduled_job('cron', day_of_week='mon-sat', hour=6)
def send_devotional():
    d = t30()
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    for user in db.users.find({"mute":False}):
        try:
            bot.send_message(
                chat_id=user["chat_id"], text="TODAY'S DEVOTIONAL"
            )
            bot.send_photo(
                chat_id=user["chat_id"], photo=d["image"], caption=d["title"], reply_markup=InlineKeyboardMarkup(button)
            )
        except Exception as e:
            if str(e) == "Forbidden: bot was blocked by the user":
                db.users.update_one({"chat_id", user["chat_id"]}, {"$set":{"active":False}})
    u = db.users.count_documents({"mute":False, "active":True})
    print(f"Succesfully sent devotional to {u} users")

def notify_tickets(date):
    """
    Send a notification to users and returns True on success
    """
    start_time = f'{date}T08:00:00'
    ticket = service_ticket(start_time)
    buttons = [[InlineKeyboardButton("Book first service", url=ticket[0]["link"])],
        [InlineKeyboardButton("Book second service", url=ticket[1]["link"])]]
    for user in db.users.find({"mute":False}):
        try:
            bot.send_message(
                chat_id=user["chat_id"], text=config["messages"]["tickets"].format(ticket[0]["name"]), reply_markup=InlineKeyboardMarkup(buttons)
            )
            return True
        except Exception as e:
            if str(e) == "Forbidden: bot was blocked by the user":
                db.users.update_one({"chat_id", user["chat_id"]}, {"$set":{"active":False}})
            return None

#@sched.scheduled_job('cron', day_of_week='wed', hour=12)
def ticket_task():
    d = date.today() + timedelta(days=4)
    print(d)
    while notify_tickets(d) == None:
        time.sleep(300)
        notify_tickets(d)
    u = db.users.count_documents({"mute":False, "active":True})
    print(f"Succesfully notified {u} users for tickets")

@sched.scheduled_job('interval', minutes=25)
def wake():
    requests.get('https://secret-sands-37903.herokuapp.com/')
    print("Waking heroku app...")

if __name__ == '__main__':
    sched.start()