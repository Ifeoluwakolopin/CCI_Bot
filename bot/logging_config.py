import logging
import os


def configure_logging() -> None:
    """Configure application-wide logging once."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        format=(
            "%(asctime)s level=%(levelname)s logger=%(name)s "
            "process=%(process)d message=%(message)s"
        ),
        level=getattr(logging, log_level, logging.INFO),
    )
