# CCI Bot

CCI Bot is a Python Telegram bot for Celebration Church International. It helps users find sermons, receive devotionals and service updates, set their CCI location and birthday, send feedback, and request or manage counseling conversations.

## Stack

- Python 3.11 (`runtime.txt`, `Dockerfile`)
- [`python-telegram-bot`](https://python-telegram-bot.org/) 22.8 for Telegram polling/webhooks
- MongoDB via `pymongo`
- `python-dotenv` for local environment variables
- APScheduler for scheduled jobs in `jobs.py`
- Requests + Beautiful Soup for web scraping sermon, devotional, location, and Eventbrite data
- Docker and Docker Compose for containerized bot/scheduler processes
- Heroku-style `Procfile` and a self-hosted GitHub Actions deployment workflow

### Security dependency baseline

The requirements include the October 21, 2026 security fixes: certifi
2026.10.19, cryptography 50.0.0, idna 3.15, PyMongo 4.18.2,
python-dotenv 1.2.2, requests 2.33.0, soupsieve 2.9.0, Tornado 6.5.9,
and urllib3 2.8.0. dnspython 2.8.0 satisfies PyMongo's dependency
requirement and replaces its vulnerable 2.0.0 pin.
Setuptools 84.2.1 and the pip 26.2.2 installation step address additional
installer/build-dependency advisories found when checking the resolved
environment. APScheduler moves to 3.11.3 because 3.9.1 imports `pkg_resources`,
which the patched setuptools no longer provides. The scheduler is still
APScheduler 3; its asyncio scheduler now awaits Telegram jobs, without changing
cron schedules.
CMake stays on major version 3 at 3.31.10 because the 3.27.7 macOS wheel's
malformed wheel metadata fails the patched pip's platform check.

### MongoDB compatibility contract

PyMongo 4.18.2 replaces the vulnerable 3.11.0 driver for Dependabot alerts
78–81 and GHSA-m87m-mmvp-v9qm. **MongoDB Server 4.4 or newer is now a
required driver-compatibility minimum.** Use a MongoDB release still receiving
upstream security support for deployment; the protocol minimum does not imply
that an end-of-life server is secure. Supporting older servers is intentionally
not retained at the cost of the known driver vulnerabilities.

The checked-in Docker/Compose, workflow, runtime and application configuration
do not pin a conflicting MongoDB server version. This is an explicit supported
server requirement, not verification of the currently deployed database.
Production server version, authentication, certificates and topology have not
been inspected or tested, and this dependency update does not deploy anything.

User search uses `count_documents()` instead of the removed `Cursor.count()`
API, preserving the original filter and result projection. No database schema
migration is included. PyMongo 4 defaults `directConnection` to `false`, allowing
replica-set discovery. Keep that default for discoverable replica sets; an
intentionally single-endpoint connection can explicitly set
`directConnection=true` in its URI. Do not force it globally, disable TLS
verification or silently rewrite connection settings.
See the [PyMongo migration guide](https://pymongo.readthedocs.io/en/4.18.2/migrate-to-pymongo4.html)
for renamed/removed URI options. The application continues to use `tlsCAFile`
with the certifi CA bundle.

### Maintained Telegram transport

The October 22 follow-up upgrades the same Telegram SDK from 12.8 to 22.8,
removing its bundled, unversioned urllib3 transport. That legacy transport
contained the unbounded chunk-size read described by GHSA-vxq7-64xx-v4gw;
the separate top-level urllib3 2.8.0 pin did not patch it. Telegram requests
now use `telegram.request.HTTPXRequest`, HTTPX 0.28.1, httpcore 1.0.9 and
h11 0.16.0, with anyio 4.15.1 and typing_extensions 4.16.0 pinned.
The `webhooks` SDK extra retains the webhook entrypoint.

Handlers and their messaging helpers explicitly await the SDK. Application
dispatch stays sequential, preserving command/conversation state ordering;
broadcast delivery remains bounded to 20 concurrent recipients on the same
event loop. Delivery failures are counted rather than reported as successes.
Commands, callback data, keyboard values, MongoDB fields and counseling
request/conversation/transfer/follow-up flows are retained. Unsupported
`resize_keyboard` arguments are removed only from inline keyboards, not reply
keyboards. Synchronous database access and scraper calls remain synchronous;
this migration is not a performance or product rewrite.

## Project structure

```text
app.py                 # Starts the Telegram bot (polling or webhook)
jobs.py                # APScheduler jobs for birthdays, sermons, tickets, and devotionals
bot/                   # Bot setup, commands, database helpers, keyboards, scrapers
chat/                  # Counseling chat message and callback handlers
config.json            # Message templates and bot copy
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
   python -m pip install --upgrade pip==26.2.2
   pip install -r requirements.txt
   ```

3. Create a local `.env` from the example and fill in real values:

   ```bash
   cp .env.example .env
   ```

   Keep `.env` local only. It is ignored by Git and must never be committed.

## Environment variables

See `.env.example` for the complete list of expected variable names.

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Telegram bot token used by the SDK Application and shared bot |
| `MONGO_URI` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | MongoDB database name |
| `EVENT_TOKEN` | Yes | Eventbrite API token used by ticket scraping |
| `COUNSELOR_PASSWORD` | Yes | Password for counselor verification |
| `COUNSELOR_REQUEST_PASSWORD` | Yes | Password for viewing active counseling requests |
| `PORT` | Deploy only | Webhook port; defaults to `5000` locally |

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

Run scheduled work in a separate process, as Docker Compose already does:

```bash
python jobs.py
```

The scheduler owns an asyncio event loop and initializes/closes its Telegram
client around the scheduled jobs. Daily birthday (23:00), daily sermon (06:00)
and Saturday feedback (06:00) jobs retain their existing local-time schedules;
ticket/devotional helper functions remain available, and the previously
disabled devotional schedule stays disabled. The obsolete scheduler start
after the blocking bot runner returned is removed: stopping the bot no longer
starts a second scheduler after shutdown.

## Validation

There is no automated test suite in this repository yet. Use Python compilation as the current safety gate:

```bash
source .venv/bin/activate
python -m pip check
python -m compileall -q .
```

Importing `app.py` is not used as a routine gate because module import initializes Telegram and MongoDB clients from environment variables.
Dependency and compilation checks do not validate live MongoDB connectivity,
Telegram polling/webhooks, scheduled jobs, or deployment on the Raspberry Pi.

Pull requests additionally run a GitHub-hosted dependency check and an isolated
MongoDB 8.0 TLS replica-set smoke check of existing user, sermon, topic,
conversation and statistics helpers. The check binds only a loopback port and
uses synthetic data and a disposable private CA. Database/logger bindings are
injected to avoid starting the bot; production authentication, certificates,
network topology and Telegram services are not exercised. It also verifies the
effective replica-discovery default, an explicit `directConnection=true` URI,
and rejection of the private CA when only public certifi roots are trusted.
The driver protocol minimum of MongoDB 4.4 is not an integration result for
every supported server version.

The same hosted workflow runs `.github/scripts/telegram_smoke.py` against a
separate empty disposable database. It injects synthetic configuration and
environment variables before importing the actual application; `.env` is not
loaded and the real `config.json` is not opened. Real SDK requests use HTTPX's
mock transport, with non-loopback socket connections forbidden. The procedural
smoke covers registration, sequential dispatch, awaited calls, onboarding,
commands, counseling messages/transfers/follow-ups, broadcasts (including
failed/empty delivery), cron definitions and an actual asyncio-scheduled send.
Polling/webhook runner selection and arguments are intercepted, not started.
Every resolved Python dependency, including installer packages, is checked
against published PyPI advisories and the versions/audit are retained as a
workflow artifact. No live Telegram service, provider credentials, production
database or production deployment is used. This is not live Bot API,
Raspberry Pi, external scraper or production-data validation.

## Docker

Build and run both long-lived processes with Docker Compose:

```bash
docker compose build
docker compose up -d
```

The compose file starts separate `bot` and `scheduler` services and writes logs under `./logs`.

## Deployment

- `Procfile` runs `python3 app.py -d` for webhook-style platforms.
- `Dockerfile` builds the Python runtime image.
- `docker-compose.yml` runs separate bot and scheduler containers.
- `.github/workflows/deploy.yml` deploys from `main` on a self-hosted Raspberry Pi runner.
  Pull requests use GitHub-hosted validation only: they neither publish the
  production image nor run the Pi deployment job.

## Status and notes

The bot is operational code with deployment assets, but maintainability tooling is light: there are no tests, linting, type checking, or formatter configuration yet. Several handlers catch broad exceptions and sometimes swallow errors, so changes should be validated carefully and logging should be improved when touching those paths.
