import requests, json

config = json.load(open("config.json"))

def service_ticket(start="", end=""):
    """
    This takes in a string of time
    in the format'yyy-mm-ddThh-mm-ss' and returns tickets available
    for the provided time.
    """
    params = {
        'token':config["event_token"],
        'start_date.range_start':start,
        'start_date.range_end':end
    }
    base_url = 'https://www.eventbriteapi.com/v3/organizations/180780002373/events/'
    r = requests.get(base_url, params=params)
    try:
        return [{"image":event["logo"]["url"],
           "link":event["url"]} for event in r.json()["events"]]
    except:
        return []
