from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .models import BookingEvent


@dataclass(frozen=True)
class NotificationCandidate:
    dedupe_key: str
    kind: str
    content: str


def calendar_state_key(property_id: str, calendar_id: str) -> str:
    return f"{property_id}:{calendar_id}"


def current_date_in_timezone(timezone_name: str) -> date:
    return datetime.now(ZoneInfo(timezone_name)).date()


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def diff_events(
    previous_state: dict[str, dict[str, str]],
    current_events: list[BookingEvent],
    *,
    today: date,
) -> list[NotificationCandidate]:
    previous_events = {
        key: BookingEvent.from_state(item) for key, item in previous_state.items()
    }
    current_map = {
        event.state_key: event
        for event in current_events
        if parse_iso_date(event.end_date) > today
    }

    candidates: list[NotificationCandidate] = []
    for key, event in current_map.items():
        previous = previous_events.get(key)
        if previous is None:
            candidates.append(
                NotificationCandidate(
                    dedupe_key=_dedupe_key("new", event),
                    kind="new",
                    content=_format_new_booking(event),
                )
            )
            continue

        if previous.fingerprint != event.fingerprint:
            candidates.append(
                NotificationCandidate(
                    dedupe_key=_dedupe_key("updated", event),
                    kind="updated",
                    content=_format_updated_booking(previous, event),
                )
            )

    for key, event in previous_events.items():
        if key in current_map:
            continue
        if parse_iso_date(event.end_date) <= today:
            continue
        candidates.append(
            NotificationCandidate(
                dedupe_key=_dedupe_key("cancelled", event),
                kind="cancelled",
                content=_format_cancelled_booking(event),
            )
        )

    return candidates


def detect_overlaps(
    events_by_property: dict[str, list[BookingEvent]],
) -> list[NotificationCandidate]:
    candidates: list[NotificationCandidate] = []

    for events in events_by_property.values():
        sorted_events = sorted(
            events,
            key=lambda event: (
                event.start_date,
                event.end_date,
                event.calendar_id,
                event.uid,
            ),
        )
        for index, left in enumerate(sorted_events):
            for right in sorted_events[index + 1 :]:
                if left.calendar_id == right.calendar_id:
                    continue
                if right.start_date >= left.end_date:
                    break
                if not _overlaps(left, right):
                    continue

                candidates.append(
                    NotificationCandidate(
                        dedupe_key=_overlap_key(left, right),
                        kind="overlap",
                        content=_format_overlap(left, right),
                    )
                )

    return candidates


def _overlaps(left: BookingEvent, right: BookingEvent) -> bool:
    return left.start_date < right.end_date and right.start_date < left.end_date


def _dedupe_key(kind: str, event: BookingEvent) -> str:
    seed = "|".join(
        [
            kind,
            event.property_id,
            event.calendar_id,
            event.uid,
            event.fingerprint,
        ]
    )
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()


def _overlap_key(left: BookingEvent, right: BookingEvent) -> str:
    seed_parts = sorted(
        [
            f"{left.calendar_id}:{left.uid}:{left.fingerprint}",
            f"{right.calendar_id}:{right.uid}:{right.fingerprint}",
        ]
    )
    return hashlib.sha1("|".join(seed_parts).encode("utf-8")).hexdigest()


def _format_new_booking(event: BookingEvent) -> str:
    lines = [
        "New booking",
        f"Property: {event.property_name}",
        f"Source: {_label(event.source)}",
        f"Check-in: {event.start_date}",
        f"Check-out: {event.end_date}",
    ]
    if event.summary:
        lines.append(f"Summary: {event.summary}")
    return "\n".join(lines)


def _format_updated_booking(previous: BookingEvent, current: BookingEvent) -> str:
    lines = [
        "Updated booking",
        f"Property: {current.property_name}",
        f"Source: {_label(current.source)}",
        f"Old dates: {previous.start_date} -> {previous.end_date}",
        f"New dates: {current.start_date} -> {current.end_date}",
    ]
    if current.summary:
        lines.append(f"Summary: {current.summary}")
    return "\n".join(lines)


def _format_cancelled_booking(event: BookingEvent) -> str:
    lines = [
        "Booking removed or cancelled",
        f"Property: {event.property_name}",
        f"Source: {_label(event.source)}",
        f"Dates: {event.start_date} -> {event.end_date}",
    ]
    if event.summary:
        lines.append(f"Summary: {event.summary}")
    return "\n".join(lines)


def _format_overlap(left: BookingEvent, right: BookingEvent) -> str:
    return "\n".join(
        [
            "Possible double booking detected",
            f"Property: {left.property_name}",
            f"{_label(left.source)}: {left.start_date} -> {left.end_date}",
            f"{_label(right.source)}: {right.start_date} -> {right.end_date}",
        ]
    )


def _label(value: str) -> str:
    return value.replace("_", " ").title()

