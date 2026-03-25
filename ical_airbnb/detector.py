from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .models import BookingEvent


@dataclass(frozen=True)
class NotificationField:
    name: str
    value: str
    inline: bool = True


@dataclass(frozen=True)
class NotificationCandidate:
    dedupe_key: str
    kind: str
    title: str
    fields: tuple[NotificationField, ...]
    color: int

    def to_log_message(self) -> str:
        lines = [self.title]
        for field in self.fields:
            lines.append(f"{field.name}: {field.value}")
        return "\n".join(lines)


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
                    title="New booking",
                    fields=_new_booking_fields(event),
                    color=0x57F287,
                )
            )
            continue

        if previous.fingerprint != event.fingerprint:
            candidates.append(
                NotificationCandidate(
                    dedupe_key=_dedupe_key("updated", event),
                    kind="updated",
                    title="Updated booking",
                    fields=_updated_booking_fields(previous, event),
                    color=0x5865F2,
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
                title="Booking removed or cancelled",
                fields=_cancelled_booking_fields(event),
                color=0xED4245,
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
                        title="Possible double booking detected",
                        fields=_overlap_fields(left, right),
                        color=0xFAA61A,
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


def _new_booking_fields(event: BookingEvent) -> tuple[NotificationField, ...]:
    fields = [
        NotificationField("Property", event.property_name),
        NotificationField("Source", _label(event.source)),
        NotificationField("Check-in", event.start_date),
        NotificationField("Check-out", event.end_date),
    ]
    if event.summary:
        fields.append(NotificationField("Summary", event.summary, inline=False))
    return tuple(fields)


def _updated_booking_fields(
    previous: BookingEvent, current: BookingEvent
) -> tuple[NotificationField, ...]:
    fields = [
        NotificationField("Property", current.property_name),
        NotificationField("Source", _label(current.source)),
        NotificationField(
            "Old dates", f"{previous.start_date} -> {previous.end_date}", inline=False
        ),
        NotificationField(
            "New dates", f"{current.start_date} -> {current.end_date}", inline=False
        ),
    ]
    if current.summary:
        fields.append(NotificationField("Summary", current.summary, inline=False))
    return tuple(fields)


def _cancelled_booking_fields(event: BookingEvent) -> tuple[NotificationField, ...]:
    fields = [
        NotificationField("Property", event.property_name),
        NotificationField("Source", _label(event.source)),
        NotificationField("Dates", f"{event.start_date} -> {event.end_date}", inline=False),
    ]
    if event.summary:
        fields.append(NotificationField("Summary", event.summary, inline=False))
    return tuple(fields)


def _overlap_fields(
    left: BookingEvent, right: BookingEvent
) -> tuple[NotificationField, ...]:
    return (
        NotificationField("Property", left.property_name),
        NotificationField(
            _label(left.source), f"{left.start_date} -> {left.end_date}", inline=False
        ),
        NotificationField(
            _label(right.source), f"{right.start_date} -> {right.end_date}", inline=False
        ),
    )


def _label(value: str) -> str:
    return value.replace("_", " ").title()
