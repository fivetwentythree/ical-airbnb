# Airbnb iCal to Discord: Free GitHub Implementation

## Goal

Build a zero-dollar booking monitor that:

- works when your computer is off
- supports multiple properties
- sends Discord alerts
- detects new bookings, updates, cancellations, and overlap risks

## Best fully free approach

The cleanest zero-cost option is:

> a Python poller run by GitHub Actions every 5 minutes, using a JSON state file committed back to the repository

This removes the need for Docker, a VPS, or any paid hosting.

## Why this version is different

The earlier SQLite + always-on host design is better operationally, but it is not completely free unless you already own hardware that stays on.

For a true zero-dollar cloud setup, GitHub Actions is the best fit if you accept these tradeoffs:

- polling is best-effort, not real-time
- scheduled runs can be delayed
- local runner storage is ephemeral
- persistent state must live in Git

## Final architecture

```text
GitHub Actions schedule
        ↓
Python poller
        ↓
Airbnb iCal fetch
        ↓
iCal parser + normalizer
        ↓
JSON state file
        ↓
Change detector + overlap detector
        ↓
Discord webhook
        ↓
Commit updated state back to GitHub
```

## What is in this scaffold

This repo now includes:

- a local `.venv` created with `uv`
- a dependency-light Python app under `ical_airbnb/`
- a GitHub Actions workflow in `.github/workflows/poll.yml`
- an example config file in `config.example.json`
- a persisted state file in `data/state.json`

## How the free version works

### Runtime

GitHub Actions runs the poller every 5 minutes.

### State storage

Because GitHub-hosted runners are ephemeral, the workflow writes changes to `data/state.json` and commits that file back to the repo.

That state file stores:

- per-calendar fetch metadata
- normalized active events
- sent notification dedupe keys

## Privacy tradeoff

If the repo is public, any committed state file is public too.

That means the fully free setup is simplest when:

- you are okay with the repo being private only while you stay inside GitHub's free private-usage limits, or
- you are okay with the state being public, or
- you move state into a separate private repo later

For a stricter privacy model, the next step would be:

- public code repo for free Actions minutes
- separate private state repo updated by a token

That is still free, but adds setup complexity.

## Multi-property support

The app is designed for one config file with multiple properties and feeds.

Each property has:

- `id`
- `name`
- `timezone`
- `feeds`

Each feed has:

- `id`
- `source`
- `url`

Example shape:

```json
{
  "discord_webhook_url": "env:DISCORD_WEBHOOK_URL",
  "poll_interval_seconds": 300,
  "properties": [
    {
      "id": "main-apartment",
      "name": "Main Apartment",
      "timezone": "Australia/Hobart",
      "feeds": [
        {
          "id": "airbnb",
          "source": "airbnb",
          "url": "env:AIRBNB_MAIN_ICAL"
        }
      ]
    }
  ]
}
```

Environment-variable placeholders are resolved at runtime.

## Detection logic

For each feed poll, the app:

1. sends conditional HTTP requests with `ETag` and `Last-Modified` when available
2. parses `.ics` events
3. normalizes event dates into the property's timezone
4. compares current events to the saved state
5. emits Discord notifications only for real changes
6. checks overlaps across calendars inside the same property
7. writes updated state back to `data/state.json`

## Notifications sent

The scaffold supports:

- new booking
- updated booking
- removed or cancelled booking
- possible double booking detected

Each notification is deduplicated so repeated workflow runs do not spam Discord.

## Project structure

```text
ical-airbnb/
├── .github/
│   └── workflows/
│       └── poll.yml
├── .venv/
├── data/
│   └── state.json
├── ical_airbnb/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── detector.py
│   ├── fetcher.py
│   ├── ics_parser.py
│   ├── main.py
│   ├── models.py
│   ├── notifier.py
│   └── state.py
├── .python-version
├── config.example.json
├── pyproject.toml
└── IMPLEMENTATION.md
```

## Why this scaffold avoids extra dependencies

To keep the free setup simpler, the starter uses the Python standard library for:

- HTTP requests
- JSON state storage
- Discord webhook calls
- basic iCal parsing

That keeps GitHub Actions setup lighter and easier to reason about.

## Workflow behavior

The GitHub workflow does four things:

1. checks out the repo
2. sets up Python and `uv`
3. runs the poller
4. commits `data/state.json` if it changed

The workflow is intentionally simple because the free version should be easy to maintain.

## Secrets you need in GitHub

At minimum:

- `DISCORD_WEBHOOK_URL`
- `AIRBNB_MAIN_ICAL`

If you add more properties or more feeds, add more secrets and update the config file to reference them.

## Honest limitations

This is the best zero-cost cloud version, but it is not perfect.

Limitations:

- GitHub scheduling is not guaranteed real-time
- missed or delayed runs are possible
- storing state in Git is less elegant than SQLite
- public-repo privacy needs thought before committing booking state

## Best next improvement if you outgrow this

If the free version works and you later want better reliability, the first upgrade should be:

> keep the Python app, but move runtime to an always-on host and move state to SQLite

That keeps the code mostly the same while improving durability.

## Bottom line

If "completely free" matters more than perfect reliability, this GitHub Actions design is the best implementation.

It is the simplest version that:

- runs in the cloud
- costs nothing
- supports multiple properties
- sends Discord alerts
- does not require Docker
