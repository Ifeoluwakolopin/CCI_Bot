import os
from datetime import date as datetime

import requests
from bs4 import BeautifulSoup

from bot import config, logger
from bot.settings import env_or_config, int_env_or_config


class WebScrapers:
    @staticmethod
    def _headers() -> dict[str, str]:
        user_agent = env_or_config(
            config,
            "FEED_USER_AGENT",
            ("feeds", "user_agent"),
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)",
        )
        return {"user-agent": user_agent}

    @staticmethod
    def _timeout() -> int:
        return int_env_or_config(config, "FEED_TIMEOUT", ("feeds", "timeout"), 20) or 20

    @staticmethod
    def service_ticket(start: str = "", end: str = "") -> list:
        """
        This takes in a string of time
        in the format'yyy-mm-ddatetimehh-mm-ss' and returns tickets available
        for the provided time.
        """
        params = {
            "token": os.getenv("EVENT_TOKEN"),
            "start_date.range_start": start,
            "start_date.range_end": end,
        }
        base_url = env_or_config(
            config, "EVENTBRITE_EVENTS_URL", ("feeds", "eventbrite_events_url")
        )
        if not base_url:
            organization_id = env_or_config(
                config,
                "EVENTBRITE_ORGANIZATION_ID",
                ("feeds", "eventbrite_organization_id"),
            )
            if not organization_id:
                logger.info("Eventbrite organization ID is not configured")
                return []
            base_url = (
                "https://www.eventbriteapi.com/v3/organizations/"
                f"{organization_id}/events/"
            )
        r = requests.get(base_url, params=params, timeout=WebScrapers._timeout())
        try:
            return [
                {"image": event["logo"]["url"], "link": event["url"]}
                for event in r.json()["events"]
            ]
        except (KeyError, TypeError, ValueError):
            logger.exception("Failed to parse Eventbrite service tickets")
            return []

    @staticmethod
    def cci_sermons() -> list:
        """
        This function scrapes the CCI websites for new sermons
        and returns the latest sermons uploaded on the database

        Keyword arguments:
        None -- does not take in any arguments

        Return: list: returns a list of sermons with each sermon
        as a dictionary.
        """

        base_url = env_or_config(
            config, "SERMONS_FEED_URL", ("feeds", "sermons_url"), ""
        )
        if not base_url:
            logger.info("Sermons feed URL is not configured")
            return []
        r = requests.get(
            base_url, headers=WebScrapers._headers(), timeout=WebScrapers._timeout()
        )
        soup = BeautifulSoup(r.text, "html.parser")
        sermons_section = soup.find_all("article")
        sermons = []

        for sermon in sermons_section:
            image = title = link = download = None
            try:
                image = sermon.find("img").get("src")
                title = (
                    sermon.find("h3", {"class": "cmsmasters_sermon_title entry-title"})
                    .find("a")
                    .text
                )
                link = (
                    sermon.find("h3", {"class": "cmsmasters_sermon_title entry-title"})
                    .find("a")
                    .get("href")
                )
                download = sermon.find(
                    "a",
                    {
                        "class": "cmsmasters_sermon_media_item cmsmasters_theme_icon_sermon_download"
                    },
                ).get("href")
                video = sermon.find(
                    "a",
                    {
                        "class": "cmsmasters_sermon_media_item cmsmasters_theme_icon_sermon_video"
                    },
                ).get("href")

                if video.startswith("//"):
                    video = "https:" + video

                sermons.append(
                    {
                        "title": title,
                        "download": download,
                        "video": video,
                        "link": link,
                        "image": image,
                    }
                )
            except AttributeError:
                if not all([title, download, link, image]):
                    logger.exception("Skipping malformed sermon card")
                    continue
                logger.info("Sermon video metadata missing for title=%s", title)
                sermons.append(
                    {
                        "title": title,
                        "download": download,
                        "link": link,
                        "image": image,
                        "video": None,
                    }
                )
        return sermons

    @staticmethod
    def t30() -> dict:
        """
        This function scrapes the triumph30 website for daily devotionals
        and returns a dictionary containing the latest devotional

        Keyword arguments:
        None -- does not take in any arguments

        Return: dict: returns a dictionary containing the latest devotional
        """
        base = env_or_config(
            config, "DEVOTIONAL_FEED_URL", ("feeds", "devotional_url"), ""
        )
        if not base:
            logger.info("Devotional feed URL is not configured")
            return {}
        r = requests.get(
            base, headers=WebScrapers._headers(), timeout=WebScrapers._timeout()
        )
        soup = BeautifulSoup(r.text, "html.parser")

        title = soup.find("h3", {"class": "entry-title td-module-title"}).find("a").text
        link = (
            soup.find("h3", {"class": "entry-title td-module-title"})
            .find("a")
            .get("href")
        )
        image = soup.find("div", {"class": "td-module-thumb"}).find("img").get("src")
        excerpt = soup.find("div", {"class": "td-excerpt"}).text.strip()
        date = str(datetime.today())

        d = {
            "title": title,
            "link": link,
            "image": image,
            "date": date,
            "excerpt": excerpt,
        }

        return d

    @staticmethod
    def church_locations():
        base_url = env_or_config(
            config,
            "CHURCH_LOCATIONS_FEED_URL",
            ("feeds", "church_locations_url"),
            "",
        )
        if not base_url:
            logger.info("Church locations feed URL is not configured")
            return {}
        r = requests.get(
            base_url, headers=WebScrapers._headers(), timeout=WebScrapers._timeout()
        )
        soup = BeautifulSoup(r.text, "html.parser")

        titles_spans = soup.find_all("span", {"class": "elementskit-tab-title"})
        locations = {}
        for span in titles_spans:
            locations[span.get_text()] = []

        return locations
