import sys

from bot.main import main


def run() -> None:
    """Start the Telegram bot process.

    Scheduled jobs run through ``python jobs.py`` or the separate Docker Compose
    scheduler service because ``Updater.idle()`` blocks.
    """
    deploy = "--deploy" in sys.argv or "-d" in sys.argv
    main(deploy=deploy)


if __name__ == "__main__":
    run()
