# CCI Bot

CCI Bot is a Python Telegram bot for Celebration Church International. It helps users find sermons, receive devotionals and service updates, set their CCI location and birthday, send feedback, and request or manage counseling conversations.

## Stack

- Python 3.11 (`runtime.txt`, `Dockerfile`)
- [`python-telegram-bot`](https://python-telegram-bot.org/) 12.8 for Telegram polling/webhooks
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
APScheduler 3's `BlockingScheduler`; no job schedules are changed.
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

The Telegram framework remains at 12.8 to preserve its v12 handler APIs.
`telegram.utils.request` imports a separate
`telegram.vendor.ptb_urllib3` transport whose version marker is `dev`;
updating the top-level urllib3 pin does not replace that bundled code.
Dependency-metadata scans do not establish the security of that unversioned
vendored code. A feature-preserving Telegram migration needs a separate
assessment; this update is not a security certification of the legacy framework.

## Project structure

```text
app.py                 # Starts the Telegram bot and blocking scheduler
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
| `BOT_TOKEN` | Yes | Telegram bot token used by `telegram.Bot` and `Updater` |
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

`python app.py` starts the bot in polling mode and then starts the blocking scheduler. For webhook deploy mode, use:

```bash
python app.py --deploy
```

The scheduler can also be run directly:

```bash
python jobs.py
```

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
