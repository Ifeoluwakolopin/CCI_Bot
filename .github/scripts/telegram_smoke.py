"""Isolated SDK migration smoke; synthetic data and loopback MongoDB only."""

import ast
import asyncio
import importlib
import importlib.metadata
import inspect
import io
import json
import os
from pathlib import Path
import runpy
import socket
import sys
from urllib.parse import parse_qsl
from unittest.mock import patch

import httpx
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler
from telegram.request import HTTPXRequest

sys.path.insert(0, str(Path.cwd()))
URI = "mongodb://localhost:27017/cci_telegram_smoke?replicaSet=cci_security_smoke"
TOKEN = "123456:synthetic-not-a-real-token"
sources = {
    str(path): path.read_text()
    for path in [Path("app.py"), Path("jobs.py"), *Path("bot").glob("*.py"), *Path("chat").glob("*.py")]
}
trees = {path: ast.parse(source) for path, source in sources.items()}
templates = {"messages": {}}
paths = []
for tree in trees.values():
    for node in ast.walk(tree):
        parts = []
        while isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            parts.insert(0, node.slice.value)
            node = node.value
        if isinstance(node, ast.Name) and node.id == "config" and len(parts) > 1:
            paths.append(parts)
for parts in sorted(paths, key=len, reverse=True):
    target = templates
    for key in parts[:-1]:
        target = target.setdefault(key, {})
    target.setdefault(parts[-1], "Synthetic")

real_open = open
real_connect = socket.socket.connect


def isolated_open(path, *args, **kwargs):
    if str(path) == "config.json":
        return io.StringIO(json.dumps(templates))
    if Path(path).name.startswith(".env"):
        raise RuntimeError("Environment-file access forbidden in smoke")
    return real_open(path, *args, **kwargs)


def loopback_connect(sock, address):
    if not isinstance(address, tuple) or address[0] not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Non-loopback network forbidden in smoke")
    return real_connect(sock, address)


calls = []
failed_chat = None


def telegram_response(request):
    method = request.url.path.rsplit("/", 1)[-1]
    data = json.loads(request.content) if request.content and request.headers.get("content-type", "").startswith("application/json") else dict(
        parse_qsl(request.content.decode())
    )
    calls.append((method, data))
    if method == "getMe":
        result = {"id": 123456, "is_bot": True, "first_name": "Synthetic", "username": "synthetic_bot"}
    elif method == "answerCallbackQuery":
        result = True
    else:
        if failed_chat is not None and str(data.get("chat_id")) == str(failed_chat):
            return httpx.Response(403, json={"ok": False, "error_code": 403, "description": "Forbidden: bot was blocked by the user"})
        result = {"message_id": len(calls), "date": 1, "chat": {"id": int(data["chat_id"]), "type": "private"}, "text": "Synthetic"}
    return httpx.Response(200, json={"ok": True, "result": result})


transport = httpx.MockTransport(telegram_response)
real_request_init = HTTPXRequest.__init__


def isolated_request_init(self, *args, **kwargs):
    kwargs["httpx_kwargs"] = {"transport": transport, "trust_env": False}
    real_request_init(self, *args, **kwargs)


env = {"BOT_TOKEN": TOKEN, "MONGO_URI": URI, "DB_NAME": "cci_telegram_smoke", "PORT": "5000",
       "COUNSELOR_PASSWORD": "synthetic", "COUNSELOR_REQUEST_PASSWORD": "synthetic"}

with MongoClient(URI, tlsCAFile=str(Path(".security-mongo/ca.pem").resolve()), serverSelectionTimeoutMS=10000) as client:
    db = client["cci_telegram_smoke"]
    assert not db.list_collection_names(), "Expected fresh smoke database"
    with (
        patch.dict(os.environ, env, clear=True),
        patch("builtins.open", isolated_open),
        patch("dotenv.load_dotenv", return_value=False),
        patch("pymongo.MongoClient", return_value=client) as bootstrap_client,
        patch.object(HTTPXRequest, "__init__", isolated_request_init),
        patch.object(socket.socket, "connect", loopback_connect),
    ):
        package = importlib.import_module("bot")
        main = importlib.import_module("bot.main")
        jobs = importlib.import_module("jobs")
        commands = importlib.import_module("bot.commands")
        helpers = importlib.import_module("bot.helpers")
        callbacks = importlib.import_module("chat.chat_callback_handlers")
        importlib.import_module("bot.conversation_manager")
        importlib.import_module("app")
        bootstrap_client.assert_called_once_with(URI, tlsCAFile=importlib.import_module("certifi").where())
        with patch.object(Application, "run_polling") as polling:
            main.main()
            polling.assert_called_once_with()
        registered = package.application.handlers[0]
        assert len(registered) == 8 and all(inspect.iscoroutinefunction(h.callback) and h.block for h in registered)
        assert set().union(*(h.commands for h in registered if isinstance(h, CommandHandler))) == {
            "start", "mute", "unmute", "cancel", "feedback", "transfer"
        }
        assert package.application.update_processor.max_concurrent_updates == 1
        assert package.bot is package.application.bot
        assert all(isinstance(req, HTTPXRequest) for req in package.bot._request)
        assert all(isinstance(req._client._transport, httpx.MockTransport) for req in package.bot._request)
        assert not any(name.startswith("telegram.vendor") for name in sys.modules)
        assert not (Path(importlib.import_module("telegram").__file__).parent / "vendor").exists()
        for deploy_flag in ("--deploy", "-d"):
            with patch.object(Application, "run_webhook") as webhook, patch.object(Application, "add_handler"), patch.object(sys, "argv", ["app.py", deploy_flag]):
                runpy.run_path("app.py", run_name="__main__")
                kwargs = webhook.call_args.kwargs
                assert kwargs["listen"] == "0.0.0.0" and kwargs["port"] == 5000 and kwargs["url_path"] == TOKEN
                assert kwargs["webhook_url"].endswith("/" + TOKEN)
        with patch.object(Application, "run_polling") as polling, patch.object(Application, "add_handler"), patch.object(sys, "argv", ["app.py"]):
            runpy.run_path("app.py", run_name="__main__")
            polling.assert_called_once_with()
        async_names = {
            name for module in (main, commands, helpers, callbacks, jobs, importlib.import_module("chat.chat_message_handlers"))
            for name, value in vars(module).items() if inspect.iscoroutinefunction(value) and name != "main"
        }
        async_names |= {"PromptHelper.location_prompt", "PromptHelper.birthday_prompt", "BroadcastHandlers.broadcast_message"}
        for path, tree in trees.items():
            parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = ast.unparse(node.func)
                if name in async_names or name.startswith(("bot.send_", "context.bot.send_", "update.message.reply_")):
                    assert isinstance(parents.get(node), ast.Await), f"Unawaited SDK/handler call at {path}:{node.lineno}"
        scheduled = {job.func.__name__: str(job.trigger) for job in jobs.sched.get_jobs()}
        assert set(scheduled) == {"birthday_notifier", "new_sermons", "check_feedback"}
        assert "hour='23'" in scheduled["birthday_notifier"] and "minute='0'" in scheduled["birthday_notifier"]
        assert "day_of_week='mon-sun'" in scheduled["new_sermons"] and "hour='6'" in scheduled["new_sermons"]
        assert "day_of_week='sat'" in scheduled["check_feedback"] and "hour='6'" in scheduled["check_feedback"]
        assert all(inspect.iscoroutinefunction(job.func) for job in jobs.sched.get_jobs())

        async def smoke():
            global failed_chat
            application = package.application
            async with application:
                errors = []

                async def fail(update, context):
                    errors.append(context.error)

                application.add_error_handler(fail)
                next_id = 0

                async def dispatch(uid, text=None, callback=None, markup=None):
                    nonlocal next_id
                    next_id += 1
                    message = {"message_id": next_id, "date": 1, "chat": {"id": uid, "type": "private", "first_name": "Synthetic"},
                               "from": {"id": uid, "is_bot": False, "first_name": "Synthetic"}, "text": text or "Synthetic"}
                    if markup:
                        message["reply_markup"] = markup.to_dict()
                    data = {"update_id": next_id, "message": message}
                    if text and text.startswith("/"):
                        message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text)}]
                    if callback:
                        data = {"update_id": next_id, "callback_query": {"id": str(next_id), "from": message["from"], "chat_instance": "synthetic", "data": callback, "message": message}}
                    await application.process_update(Update.de_json(data, package.bot))
                    if errors:
                        raise RuntimeError("Synthetic update failed") from errors.pop()

                db.church_locations.insert_one({"country": "Synthetic", "branches": ["Synthetic"]})
                db.counseling_topics.insert_one({"topic": "hope", "faqs": [], "count": 0})
                await dispatch(1001, "/start")
                assert db.users.find_one({"chat_id": 1001})["last_command"] == "first_time_location_set"
                await dispatch(1001, callback="loc=0", markup=helpers.create_buttons_from_data(["Synthetic"], "loc", 4, 1))
                await dispatch(1001, callback="br=Synthetic=0", markup=helpers.create_buttons_from_data(["Synthetic"], "br=Synthetic", 4, 2))
                assert db.users.find_one({"chat_id": 1001})["last_command"] == "first_time_birthday_set"
                await dispatch(1001, callback="bd=2")
                days = json.loads(calls[-1][1]["reply_markup"])["inline_keyboard"]
                assert days[-1][-1]["callback_data"] == "bd=2=29"
                await dispatch(1001, callback="bd=2=29")
                assert db.users.find_one({"chat_id": 1001})["birthday"] == "2-29"
                await dispatch(1001, "/mute")
                assert db.users.find_one({"chat_id": 1001})["mute"] is True
                await dispatch(1001, "/unmute")
                await dispatch(1001, "help")
                await dispatch(1001, "/feedback")
                await dispatch(1001, callback="feedback=technical")
                await dispatch(1001, "Synthetic feedback")
                assert db.feedback.count_documents({"user": 1001}) == 1
                await dispatch(1001, "counseling")
                await dispatch(1001, callback="counsel=0", markup=helpers.create_buttons_from_data(["hope"], "counsel", 5, 1))
                await dispatch(1001, callback="qa_or_c=hope=1", markup=InlineKeyboardMarkup([[InlineKeyboardButton("Synthetic", callback_data="qa_or_c=hope=1")]]))
                await dispatch(1001, "Synthetic\nsynthetic@example.invalid\n0000000000")
                req = db.counseling_requests.find_one({"user_chat_id": 1001})
                rid = req["request_message_id"]
                await dispatch(1001, callback=f"confirm_info=yes={rid}")
                await dispatch(1001, callback=f"confirm_loc=yes={rid}")
                await dispatch(1001, callback=f"cr-yes={rid}")
                await dispatch(1001, "Synthetic note")
                assert db.counseling_requests.find_one({"request_message_id": rid})["active"]
                for uid in (2001, 2002):
                    await dispatch(uid, "/start")
                    db.users.update_one({"chat_id": uid}, {"$set": {"role": "counselor", "last_command": None, "global": True}})
                db.counseling_topics.update_one({"topic": "hope"}, {"$set": {"counselors": [2001, 2002]}}, upsert=True)
                await dispatch(2001, callback=f"conv={rid}")
                await dispatch(1001, "Synthetic conversation")
                assert db.conversations.find_one({"from": rid})["messages"][-1]["message"] == "Synthetic conversation"
                await dispatch(2001, "/transfer")
                await dispatch(2001, callback="transfer=2002")
                await dispatch(2001, "Synthetic transfer note")
                await dispatch(2001, callback="transfer_req_confirm=true=2002")
                assert db.counseling_requests.find_one({"request_message_id": rid})["counselor_chat_id"] == 2002
                await dispatch(2002, callback=f"conv={rid}")
                await dispatch(2002, callback=f"mark_complete={rid}")
                await dispatch(2001, callback=f"follow_up={rid}")
                await dispatch(2001, callback=f"cancel_follow_up={rid}")
                await dispatch(2001, callback=f"continue_conv={rid}")
                assert db.users.find_one({"chat_id": 1001})["last_command"] == f"in-conversation-with=2001=pastor={rid}"
                await dispatch(2001, "/cancel")
                await dispatch(2001, callback="end_conv=no=2001=1001=user")
                await dispatch(2001, callback="end_conv=yes=2001=1001=user")
                assert db.counseling_requests.find_one({"request_message_id": rid})["status"] == "completed"
                assert db.users.find_one({"chat_id": 1001})["last_command"] is None
                empty = await helpers.BroadcastHandlers.broadcast_message([], "Synthetic", helpers.MessageHelper.send_text)
                assert empty == {"total": 0, "success": 0, "failure": 0}
                failed_chat = 1001
                mixed = await helpers.BroadcastHandlers.broadcast_message([1001, 2001], "Synthetic", helpers.MessageHelper.send_text)
                assert mixed == {"total": 2, "success": 1, "failure": 1}
                failed_chat = None
                sermon = {"title": "Synthetic sermon", "video": None, "image": "https://example.invalid/synthetic.jpg", "link": "https://example.invalid/sermon"}
                with patch.object(jobs.WebScrapers, "cci_sermons", return_value=[sermon]):
                    await jobs.new_sermons()
                await dispatch(1001, "latest sermon")
                await dispatch(1001, "get sermon")
                await dispatch(1001, callback="get-sermon=yes")
                await dispatch(1001, "Synthetic sermon")
                await jobs.birthday_notifier()
                await jobs.check_feedback()
                assert db.temporary.find_one({"latest_sermon": True})["title"] == "Synthetic sermon"
                event = asyncio.Event()

                async def scheduled_delivery():
                    await helpers.MessageHelper.send_text(2001, "Synthetic job")
                    event.set()

                jobs.sched.add_job(scheduled_delivery, "date")
                jobs.sched.start()
                try:
                    await asyncio.wait_for(event.wait(), timeout=5)
                finally:
                    jobs.sched.shutdown()
                    await asyncio.sleep(0)

        asyncio.run(smoke())
    client.drop_database("cci_telegram_smoke")

print(json.dumps({"status": "passed", "transport": "telegram.request.HTTPXRequest -> httpx -> httpcore -> h11",
                  "versions": {name: importlib.metadata.version(name) for name in ["python-telegram-bot", "httpx", "httpcore", "h11", "anyio", "pymongo", "APScheduler"]},
                  "telegram_requests_intercepted": len(calls), "dispatch": "sequential", "registered_handlers": 8,
                  "scheduled_jobs": scheduled, "network": "mock Telegram transport and loopback disposable MongoDB only"}))
