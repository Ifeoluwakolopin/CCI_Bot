import time
import pymongo
import json
import telegram
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from sermons import cci_sermons, t30
from events import service_ticket
from timeloop import Timeloop

config = json.load(open("config.json"))

client = pymongo.MongoClient(config["db"]["client"])
db = client[config["db"]["name"]]
bot = telegram.Bot(token=config["bot_token"])

t = Timeloop()


@t.job(interval=timedelta(minutes=2))
def send_devotional():
    d = t30()
    try:
        button = [[InlineKeyboardButton("Read more", url=d["link"])]]
        for user in db.users.find({"mute":False}):
            bot.send_message(
                chat_id=user["chat_id"], text="Today's Devotional"
            )
            bot.send_photo(
                chat_id=user["chat_id"], photo=d["image"], caption=d["title"], reply_markup=InlineKeyboardMarkup(button)
            )
    except:
        pass

def notify_tickets(date):

    start_time = f'{date}T08:00:00'
    ticket = service_ticket(start_time)
    try:
        buttons = [[InlineKeyboardButton("Book first service", url=ticket[0]["link"])],
            [InlineKeyboardButton("Book second service", url=ticket[1]["link"])]]
        for user in db.users.find({"mute":False}):
            bot.send_message(
                chat_id=user["chat_id"], text=config["messages"]["tickets"].format(ticket[0]["name"]), reply_markup=InlineKeyboardMarkup(buttons)
            )
        return True
    except:
        return None

@t.job(interval=timedelta(days=1))
def ticket_task():
    day = datetime.today().weekday()
    if day != 2:
        pass
    else:
        d = date.today()
        while notify_tickets(d) == None:
            time.sleep(1200)
            notify_tickets(d)


if __name__ == '__main__':
    t.start(block=True)