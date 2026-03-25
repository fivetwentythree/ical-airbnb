from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import AppConfig, load_config
from .detector import (
    calendar_state_key,
    current_date_in_timezone,
    detect_overlaps,
    diff_events,
    parse_iso_date,
)
from .fetcher import fetch_feed
from .ics_parser import parse_ical_events
from .models import BookingEvent
from .notifier import send_discord_message
from .state import load_state, prune_notifications, save_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Poll Airbnb iCal feeds and send Discord notifications."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the JSON config file. Defaults to config.json.",
    )
    parser.add_argument(
        "--state-file",
        default="data/state.json",
        help="Path to the JSON state file. Defaults to data/state.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect changes without sending Discord notifications.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config = load_config(args.config)
    state = load_state(args.state_file)
    prune_notifications(state)

    run_once(
        config,
        state=state,
        state_path=Path(args.state_file),
        dry_run=args.dry_run,
    )
    return 0


def run_once(
    config: AppConfig,
    *,
    state: dict,
    state_path: Path,
    dry_run: bool = False,
) -> None:
    calendars = state.setdefault("calendars", {})
    notifications = state.setdefault("notifications", {})
    events_by_property: dict[str, list[BookingEvent]] = {
        property_config.id: [] for property_config in config.properties
    }
    pending_notifications = []
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for property_config in config.properties:
        today = current_date_in_timezone(property_config.timezone)

        for feed in property_config.feeds:
            calendar_key = calendar_state_key(property_config.id, feed.id)
            previous_calendar = calendars.get(calendar_key, {})
            previous_events = previous_calendar.get("events", {})

            try:
                fetch_result = fetch_feed(
                    feed.url,
                    etag=previous_calendar.get("etag"),
                    last_modified=previous_calendar.get("last_modified"),
                )
            except Exception:
                logging.exception(
                    "Failed to fetch feed %s for property %s",
                    feed.id,
                    property_config.id,
                )
                events_by_property[property_config.id].extend(
                    _events_from_state(previous_events)
                )
                continue

            if fetch_result.not_modified:
                current_events = _events_from_state(previous_events)
                calendars[calendar_key] = {
                    **previous_calendar,
                    "property_id": property_config.id,
                    "calendar_id": feed.id,
                    "source": feed.source,
                    "last_checked_at": now_iso,
                    "events": previous_events,
                }
                events_by_property[property_config.id].extend(current_events)
                continue

            try:
                parsed_events = parse_ical_events(
                    fetch_result.body or "",
                    property_id=property_config.id,
                    property_name=property_config.name,
                    property_timezone=property_config.timezone,
                    calendar_id=feed.id,
                    source=feed.source,
                )
            except Exception:
                logging.exception(
                    "Failed to parse feed %s for property %s",
                    feed.id,
                    property_config.id,
                )
                events_by_property[property_config.id].extend(
                    _events_from_state(previous_events)
                )
                continue

            current_events = [
                event for event in parsed_events if parse_iso_date(event.end_date) > today
            ]
            pending_notifications.extend(
                diff_events(previous_events, current_events, today=today)
            )
            events_by_property[property_config.id].extend(current_events)

            calendars[calendar_key] = {
                "property_id": property_config.id,
                "calendar_id": feed.id,
                "source": feed.source,
                "etag": fetch_result.etag,
                "last_modified": fetch_result.last_modified,
                "last_checked_at": now_iso,
                "events": {
                    event.state_key: event.to_state()
                    for event in current_events
                },
            }

    pending_notifications.extend(detect_overlaps(events_by_property))

    sent_count = 0
    for notification in pending_notifications:
        if notification.dedupe_key in notifications:
            continue

        if dry_run:
            logging.info("Dry run notification:\n%s", notification.to_log_message())
        else:
            try:
                send_discord_message(config.discord_webhook_url, notification)
            except Exception:
                logging.exception(
                    "Failed to send %s notification", notification.kind
                )
                continue

        notifications[notification.dedupe_key] = {
            "kind": notification.kind,
            "sent_at": now_iso,
        }
        sent_count += 1

    state.setdefault("meta", {})["last_run_at"] = now_iso
    save_state(state_path, state)
    logging.info("Run finished with %s new notifications", sent_count)


def _events_from_state(records: dict[str, dict[str, str]]) -> list[BookingEvent]:
    events: list[BookingEvent] = []
    for record in records.values():
        try:
            events.append(BookingEvent.from_state(record))
        except KeyError:
            logging.warning("Skipping malformed event in saved state")
    return events


if __name__ == "__main__":
    raise SystemExit(main())
