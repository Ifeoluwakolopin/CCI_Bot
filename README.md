# CCI Bot

CCI Bot is a configurable Python Telegram bot originally built for Celebration Church International. It helps users find sermons, receive devotionals and service updates, set a branch/location and birthday, send feedback, and request or manage counseling conversations.

## Stack

- Python 3.11 (`runtime.txt`, `Dockerfile`)
- [`python-telegram-bot`](https://python-telegram-bot.org/) 12.8 for Telegram polling/webhooks
- MongoDB via `pymongo`
- `python-dotenv` for local environment variables
- APScheduler for scheduled jobs in `jobs.py`
- Requests + Beautiful Soup for web scraping sermon, devotional, location, and Eventbrite data
- Docker and Docker Compose for containerized bot/scheduler processes
- Pytest for pure-logic tests; Ruff and Black for incremental lint/format checks
- Heroku-style `Procfile` and a self-hosted GitHub Actions deployment workflow

## Project structure

```text
app.py                 # Starts the Telegram bot process
jobs.py                # APScheduler jobs for birthdays, sermons, tickets, and devotionals
bot/                   # Bot setup, commands, database helpers, keyboards, scrapers
chat/                  # Counseling chat message and callback handlers
config.json            # Message templates, links, feeds, assets, and location defaults
img/                   # Static image assets used by broadcasts/jobs
Dockerfile             # Python 3.11 container image
docker-compose.yml     # Separate bot and scheduler services
Procfile               # Web process for deploy mode
requirements.txt       # Python dependencies
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a local `.env` from the example and fill in real values:

   ```bash
   cp .env.example .env
   ```

   Keep `.env` local only. It is ignored by Git and must never be committed.

## Configuration

Runtime copy and organization-specific defaults live in `config.json`. Deployers can customize message text, links, scraper/feed URLs, fallback church branches, MAP locations, asset paths, ticket-notification location filters, and webhook settings there.

Environment variables override deploy-sensitive settings where supported. This lets each deployment use its own secrets and URLs without editing code.

## Environment variables

See `.env.example` for the complete list of expected variable names.

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token used by `telegram.Bot` and `Updater` |
| `MONGO_URI` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | MongoDB database name |
| `EVENT_TOKEN` | Yes | Eventbrite API token used by ticket scraping |
| `COUNSELOR_PASSWORD` | Yes | Password for counselor verification |
| `COUNSELOR_REQUEST_PASSWORD` | Yes | Password for viewing active counseling requests |
| `PORT` | Deploy only | Webhook port; defaults to `5000` locally |
| `HEALTH_PORT` | No | Pilot Dash `/health` HTTP port; defaults to `8080` |
| `WEBHOOK_BASE_URL` | Webhook deploy only | Public base URL used by `python app.py --deploy` |
| `EVENTBRITE_ORGANIZATION_ID` / `EVENTBRITE_EVENTS_URL` | Tickets only | Eventbrite organization or full events endpoint |

Optional overrides include `MONGO_TLS`, `MONGO_TLS_CA_FILE`, `MONGO_SERVER_SELECTION_TIMEOUT_MS`, `SERMONS_FEED_URL`, `DEVOTIONAL_FEED_URL`, `CHURCH_LOCATIONS_FEED_URL`, `BLOG_URL`, `MEMBERSHIP_URL`, `FEEDBACK_CHAT_ID`, `TICKET_LOCATION_FILTER`, `BIRTHDAY_PHOTO_PATH`, `MEMBERSHIP_PHOTO_PATH`, `FEED_USER_AGENT`, `FEED_TIMEOUT`, `WEBHOOK_LISTEN`, `WEBHOOK_URL_PATH`, `CONFIG_PATH`, `LOG_LEVEL`, `HEALTH_ENABLED`, `HEALTH_HOST`, and `APP_VERSION`.

## Running locally

Do not start the bot unless the required secrets and network access are available.

```bash
source .venv/bin/activate
python app.py
```

`python app.py` starts the bot in polling mode. For webhook deploy mode, use:

```bash
python app.py --deploy
```

The scheduler runs as a separate process:

```bash
python jobs.py
```

## Validation

Use the smallest validation gate that covers the files you changed:

```bash
source .venv/bin/activate
pytest
ruff check bot/map_utils.py bot/pagination.py tests
python -m compileall -q .
```

Importing `app.py` is not used as a routine gate because module import initializes Telegram and MongoDB clients from environment variables. Tests that need initialization should mock Telegram and MongoDB.

## Docker

Build and run both long-lived processes with Docker Compose:

```bash
docker compose build
docker compose up -d
```

The default compose stack starts `bot` and `mongo`, writes bot logs under `./logs`, and exposes Pilot Dash health on `http://localhost:${HEALTH_PORT:-8080}/health`. The scheduler remains available as an opt-in profile:

```bash
docker compose --profile scheduler up -d scheduler
```

The health response returns HTTP 200 when Mongo responds to `ping` and HTTP 503 when Mongo is unavailable.

## Deployment

- `Procfile` runs `python3 app.py -d` for webhook-style platforms.
- `Dockerfile` builds the Python runtime image.
- `docker-compose.yml` runs separate bot and scheduler containers.
- `.github/workflows/deploy.yml` deploys from `main` on a self-hosted Raspberry Pi runner.

## Status and notes

The bot is operational code with deployment assets. Maintainability work is now tracked in `PLAN.md`; keep changes small because handlers are coupled through shared `last_command` state.

`python-telegram-bot` remains pinned to 12.8 for now. A v20+ async migration should be handled as a dedicated project after more tests are in place because it affects handlers, scheduling, and counseling conversation routing.
