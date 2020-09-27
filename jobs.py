import time
import pymongo
import json
import telegram
from datetime import date, datetime
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from sermons import cci_sermons, t30
from events import service_ticket

config = json.load(open("config.json"))

client = pymongo.MongoClient(config["db"]["host"], config["db"]["port"])
db = client[config["db"]["name"]]
bot = telegram.Bot(token=config["bot_token"])


def send_devotional():
    d = t30()
    button = [[InlineKeyboardButton("Read more", url=d["link"])]]
    for user in db.users.find({"mute":False}):
        bot.send_photo(
            chat_id=user["chat_id"], photo=d["image"], caption=d["title"], reply_markup=InlineKeyboardMarkup(button)
        )

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

if __name__ == "__main__":
    while True:
        pass