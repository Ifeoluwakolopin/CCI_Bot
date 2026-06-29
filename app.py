import sys

from bot import client, logger
from bot.health import start_health_server
from bot.main import main


def run() -> None:
    """Start the Telegram bot process.

    Scheduled jobs run through ``python jobs.py`` or the separate Docker Compose
    scheduler service because ``Updater.idle()`` blocks.
    """
    deploy = "--deploy" in sys.argv or "-d" in sys.argv
    start_health_server(client, logger)
    main(deploy=deploy)


if __name__ == "__main__":
    run()
