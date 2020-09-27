import requests, json
from datetime import datetime as dt

config = json.load(open("config.json"))


def service_ticket(start_time:'2020-10-31T08:00:00'):
    """
    This takes in a string of time
    in the format'yyy-mm-ddThh-mm-ss' and returns tickets available
    for the provided time.
    """
    params = {
        'token':config["event_token"],
        'only_public':'on',
        'start_date.range_start':f'{start_time}',
    }
    base_url = 'https://www.eventbriteapi.com/v3/venues/53329211/events/'
    r = requests.get(base_url, params=params)
    try:
        return [{"name":event["name"]["text"],
           "link":event["url"]} for event in r.json()["events"]]
    except:
        return []