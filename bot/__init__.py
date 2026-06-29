import logging
import os

import certifi
import telegram
from dotenv import load_dotenv
from pymongo import MongoClient
from telegram.ext import Updater

from .logging_config import configure_logging
from .settings import load_config

load_dotenv()

configure_logging()
logger = logging.getLogger(__name__)

config = load_config()

bot_token = os.getenv("BOT_TOKEN")
mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME")

if not bot_token:
    raise RuntimeError("BOT_TOKEN must be configured")
if not mongo_uri:
    raise RuntimeError("MONGO_URI must be configured")
if not db_name:
    raise RuntimeError("DB_NAME must be configured")

bot = telegram.Bot(bot_token)

PORT = int(os.environ.get("PORT", 5000))

updater = Updater(bot_token, use_context=True)
dp = updater.dispatcher


def _env_bool(name: str) -> bool | None:
    value = os.getenv(name)
    if value in (None, ""):
        return None
    return value.lower() in {"1", "true", "yes", "on"}


def _mongo_client_kwargs(uri: str) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "serverSelectionTimeoutMS": int(
            os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")
        )
    }
    tls_enabled = _env_bool("MONGO_TLS")
    tls_ca_file = os.getenv("MONGO_TLS_CA_FILE")

    if tls_enabled is not None:
        kwargs["tls"] = tls_enabled
    if tls_ca_file:
        kwargs["tlsCAFile"] = tls_ca_file
    elif tls_enabled or (tls_enabled is None and uri.startswith("mongodb+srv://")):
        kwargs["tlsCAFile"] = certifi.where()

    return kwargs


# Database
client = MongoClient(mongo_uri, **_mongo_client_kwargs(mongo_uri))
db = client[db_name]
