# Setup Guide

This file walks you through turning this scaffold into a working app on GitHub Actions, including support for multiple properties and multiple calendar sources.

## What you are setting up

You will end up with:

- a GitHub repository containing this code
- a scheduled GitHub Actions workflow that runs every 5 minutes
- one or more Airbnb iCal URLs stored as GitHub Secrets
- a Discord webhook stored as a GitHub Secret
- a persisted `data/state.json` file that GitHub Actions updates after each run

## Before you start

You need:

- a GitHub account
- a Discord server and channel where you can create a webhook
- the Airbnb export calendar URL for each property
- optional extra iCal URLs from other platforms like Booking.com

## Important privacy note

If your repo is public, the committed `data/state.json` file is public too.

That means:

- public repo = easiest fully free option
- private repo = better privacy, but GitHub free usage limits apply

If you want the simplest fully free path, use a public repo and accept that the state file is visible.

## Step 1: Create a Discord webhook

In Discord:

1. Open the server settings.
2. Open `Integrations`.
3. Open `Webhooks`.
4. Create a new webhook.
5. Copy the webhook URL.

You will save that URL in GitHub as `DISCORD_WEBHOOK_URL`.

## Step 2: Collect your iCal URLs

For each property, collect the Airbnb export calendar URL.

If you use multiple platforms, collect those too.

Suggested secret naming pattern:

- `AIRBNB_MAIN_ICAL`
- `AIRBNB_BEACH_ICAL`
- `BOOKING_MAIN_ICAL`
- `VRBO_MAIN_ICAL`

## Step 3: Initialize this folder as a Git repository

This workspace is not currently a Git repo, so initialize it first.

Run:

```bash
git init
git branch -M main
git add .
git commit -m "Initial iCal monitor scaffold"
```

## Step 4: Create a GitHub repository and push this code

You can do this either in the GitHub web UI or with the GitHub CLI.

### Option A: GitHub web UI

1. Create a new repo on GitHub.
2. Do not add a README or `.gitignore` there.
3. Copy the repo URL.
4. Back in your terminal, run:

```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

### Option B: GitHub CLI

```bash
gh repo create ical-airbnb --public --source=. --remote=origin --push
```

If you want more privacy, create it as `--private` instead of `--public`.

## Step 5: Add GitHub Secrets

In your GitHub repo:

1. Open `Settings`
2. Open `Secrets and variables`
3. Open `Actions`
4. Add these repository secrets

Minimum required secrets:

- `DISCORD_WEBHOOK_URL`
- `AIRBNB_MAIN_ICAL`

If you have more properties or platforms, add one secret for each feed URL.

Example secret list for two properties:

- `DISCORD_WEBHOOK_URL`
- `AIRBNB_MAIN_ICAL`
- `BOOKING_MAIN_ICAL`
- `AIRBNB_BEACH_ICAL`

## Step 6: Configure your properties and feeds

Edit [config.example.json](/Users/lochana-mbp/Documents/DEV/ical-airbnb/config.example.json).

The app currently reads this file directly in GitHub Actions, so you can keep the filename as-is.

Note:

- the GitHub Actions run frequency is controlled by the cron schedule in `.github/workflows/poll.yml`
- `poll_interval_seconds` in the config does not change the GitHub schedule

### Single-property example

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

### Multiple-properties example

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
        },
        {
          "id": "booking",
          "source": "booking_com",
          "url": "env:BOOKING_MAIN_ICAL"
        }
      ]
    },
    {
      "id": "beach-house",
      "name": "Beach House",
      "timezone": "Australia/Hobart",
      "feeds": [
        {
          "id": "airbnb",
          "source": "airbnb",
          "url": "env:AIRBNB_BEACH_ICAL"
        }
      ]
    }
  ]
}
```

## Step 7: Update the GitHub Actions workflow env block

Edit [poll.yml](/Users/lochana-mbp/Documents/DEV/ical-airbnb/.github/workflows/poll.yml).

In the `Poll calendars` step, add every secret you referenced in `config.example.json`.

### Current env block

```yaml
env:
  DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
  AIRBNB_MAIN_ICAL: ${{ secrets.AIRBNB_MAIN_ICAL }}
```

### Expanded env block for multiple properties

```yaml
env:
  DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
  AIRBNB_MAIN_ICAL: ${{ secrets.AIRBNB_MAIN_ICAL }}
  BOOKING_MAIN_ICAL: ${{ secrets.BOOKING_MAIN_ICAL }}
  AIRBNB_BEACH_ICAL: ${{ secrets.AIRBNB_BEACH_ICAL }}
```

Important:

- every `env:SOME_SECRET_NAME` in the config file must also exist in this workflow `env:` block
- if you forget one, the app will fail with a missing environment variable error

## Step 8: Commit and push your config changes

After editing the config and workflow:

```bash
git add config.example.json .github/workflows/poll.yml
git commit -m "Configure properties and GitHub Actions secrets"
git push
```

## Step 9: Run the workflow manually the first time

In GitHub:

1. Open the `Actions` tab
2. Open the `Poll calendars` workflow
3. Click `Run workflow`

This lets you test everything immediately instead of waiting for the next 5-minute schedule.

## Step 10: Confirm it worked

Check three places:

### GitHub Actions logs

You want to see the workflow complete successfully.

### Discord

You should get a message only if:

- a booking is new
- a booking changed
- a booking disappeared
- an overlap was detected

If nothing changed since the last poll, Discord may stay quiet. That is normal.

### Repository changes

If the run saw or updated state, `data/state.json` may be committed automatically by the workflow.

## Step 11: Optional local test

If you want to test locally before relying on GitHub:

1. use `config.example.json` as-is, or create your own `config.json`
2. export the same environment variables
3. run the app manually

Example:

```bash
export DISCORD_WEBHOOK_URL="<your webhook>"
export AIRBNB_MAIN_ICAL="<your airbnb ical url>"
.venv/bin/python -m ical_airbnb.main --config config.example.json --state-file data/state.json --dry-run
```

Use `--dry-run` first so it prints detections without sending Discord messages.

## Step 12: Add more properties later

Whenever you add a new property:

1. create a new GitHub Secret for its iCal URL
2. add a new property block in `config.example.json`
3. add the matching secret to the workflow `env:` block
4. commit and push
5. run the workflow manually once

### Example: add a second Airbnb-only property

Add this secret:

- `AIRBNB_CITY_ICAL`

Add this property to the config:

```json
{
  "id": "city-studio",
  "name": "City Studio",
  "timezone": "Australia/Hobart",
  "feeds": [
    {
      "id": "airbnb",
      "source": "airbnb",
      "url": "env:AIRBNB_CITY_ICAL"
    }
  ]
}
```

Add this to the workflow env block:

```yaml
AIRBNB_CITY_ICAL: ${{ secrets.AIRBNB_CITY_ICAL }}
```

## Step 13: Add another platform for overlap detection

If one property is listed on more than one platform, add both feeds under the same property.

That is how overlap detection works.

Example:

```json
{
  "id": "main-apartment",
  "name": "Main Apartment",
  "timezone": "Australia/Hobart",
  "feeds": [
    {
      "id": "airbnb",
      "source": "airbnb",
      "url": "env:AIRBNB_MAIN_ICAL"
    },
    {
      "id": "booking",
      "source": "booking_com",
      "url": "env:BOOKING_MAIN_ICAL"
    }
  ]
}
```

If those date ranges overlap, the app can send a Discord conflict alert.

## Step 14: Know what not to expect

This app is a monitoring tool, not a guaranteed real-time prevention system.

That means:

- iCal feed delays still exist
- GitHub scheduled jobs can be delayed
- conflict alerts are useful, but not instant prevention

## Troubleshooting

### The workflow fails with a missing environment variable

That means one of these is true:

- the secret does not exist in GitHub
- the secret name in GitHub does not match the config
- the secret exists, but you forgot to add it to the workflow `env:` block

### The workflow cannot push `data/state.json`

Check:

- the repo allows GitHub Actions to write contents
- the workflow still includes `permissions: contents: write`

If needed, open your repo's Actions settings and enable read/write workflow permissions.

### No Discord messages arrive

Possible reasons:

- the Discord webhook URL is wrong
- there were no booking changes to report
- the feed failed to fetch
- the workflow failed before notification sending

Start by checking the GitHub Actions logs.

### Scheduled runs stop happening

Open the `Actions` tab and confirm the workflow is still enabled.

If GitHub disables scheduled workflows after inactivity, re-enable the workflow and trigger one manual run.

## Recommended file checklist

Before you consider setup complete, verify these files are present and committed:

- [pyproject.toml](/Users/lochana-mbp/Documents/DEV/ical-airbnb/pyproject.toml)
- [uv.lock](/Users/lochana-mbp/Documents/DEV/ical-airbnb/uv.lock)
- [config.example.json](/Users/lochana-mbp/Documents/DEV/ical-airbnb/config.example.json)
- [poll.yml](/Users/lochana-mbp/Documents/DEV/ical-airbnb/.github/workflows/poll.yml)
- [main.py](/Users/lochana-mbp/Documents/DEV/ical-airbnb/ical_airbnb/main.py)
- [state.json](/Users/lochana-mbp/Documents/DEV/ical-airbnb/data/state.json)

## Fastest path summary

If you want the shortest possible version:

1. Create a Discord webhook.
2. Collect all Airbnb iCal URLs.
3. Push this project to GitHub.
4. Add GitHub Secrets.
5. Edit `config.example.json`.
6. Edit `.github/workflows/poll.yml` to expose every secret.
7. Push the changes.
8. Run the workflow manually once.
9. Wait for the 5-minute schedule to take over.
