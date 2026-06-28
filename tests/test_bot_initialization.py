import importlib
import sys
import types


class DummyMongoClient:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __getitem__(self, name):
        return {"name": name}


class DummyUpdater:
    def __init__(self, *args, **kwargs):
        self.dispatcher = object()


def test_bot_package_initializes_with_mocked_dependencies(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123456:dummy-token")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("DB_NAME", "cci_bot_test")

    telegram = types.ModuleType("telegram")
    telegram.Bot = lambda token: {"token": token}
    telegram_ext = types.ModuleType("telegram.ext")
    telegram_ext.Updater = DummyUpdater
    pymongo = types.ModuleType("pymongo")
    pymongo.MongoClient = DummyMongoClient
    certifi = types.ModuleType("certifi")
    certifi.where = lambda: "/dev/null"
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    dotenv.dotenv_values = lambda *args, **kwargs: {}

    monkeypatch.setitem(sys.modules, "telegram", telegram)
    monkeypatch.setitem(sys.modules, "telegram.ext", telegram_ext)
    monkeypatch.setitem(sys.modules, "pymongo", pymongo)
    monkeypatch.setitem(sys.modules, "certifi", certifi)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    sys.modules.pop("bot", None)

    bot = importlib.import_module("bot")

    assert bot.bot == {"token": "123456:dummy-token"}
    assert bot.db == {"name": "cci_bot_test"}
