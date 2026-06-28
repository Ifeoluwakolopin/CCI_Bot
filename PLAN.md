# CCI Bot modernization plan

## Decisions

- 2026-06-28: Stay on `python-telegram-bot==12.8` for this iteration. A v20+ async rewrite touches nearly every handler, the custom counseling routing, and the APScheduler process. The safer path is to add tests, improve logging/error handling, consolidate live conversation state around the current Mongo schema, then migrate PTB in a dedicated follow-up.
- Python runtime is standardized on 3.11 (`runtime.txt` and `Dockerfile`).
- The bot and scheduler are separate long-lived processes. `app.py` starts only the bot; `jobs.py` starts APScheduler.

## Completed in this pass

- Fixed Dockerfile Python image mismatch.
- Added structured logging configuration and replaced several swallowed exceptions with logged failures.
- Consolidated counseling conversation helpers around the live `active`/`from` Mongo schema and fixed inactive status updates to use `user_chat_id`.
- Implemented the previously stubbed `map_loc` command using flexible MAP document formatting.
- Added pure-logic tests, pytest, ruff, black, and `pyproject.toml`.

## Backlog

1. Add integration tests for counseling request and conversation state transitions with a fake Mongo collection.
2. Continue replacing bare `except:` blocks in scrapers and command handlers with targeted exceptions plus logging.
3. Split bot initialization from module import so tests can import handlers without Telegram/Mongo side effects.
4. Add a local Mongo service to Docker Compose for development/testing.
5. Plan the PTB v20+ async migration after the handler seams and test coverage improve.
6. Review pinned dependency compatibility, especially old PTB/tornado/pymongo constraints.
7. Add CI to run `pytest`, targeted `ruff`, and `python -m compileall -q .`.
