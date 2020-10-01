import requests, json
from datetime import datetime as dt

config = json.load(open("config.json"))


def service_ticket():
    """
    This takes in a string of time
    in the format'yyy-mm-ddThh-mm-ss' and returns tickets available
    for the provided time.
    """
    params = {
        'token':config["event_token"],
        'time_filter':'current_future'
    }
    base_url = 'https://www.eventbriteapi.com/v3/organizations/180780002373/events/'
    r = requests.get(base_url, params=params)
    try:
        return [{"name":event["name"]["text"],
           "link":event["url"]} for event in r.json()["events"]]
    except:
        return []