from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import BookingEvent


def parse_ical_events(
    body: str,
    *,
    property_id: str,
    property_name: str,
    property_timezone: str,
    calendar_id: str,
    source: str,
) -> list[BookingEvent]:
    events: list[BookingEvent] = []
    current_fields: dict[str, list[tuple[dict[str, str], str]]] = {}
    in_event = False

    for line in _unfold_lines(body):
        if line == "BEGIN:VEVENT":
            current_fields = {}
            in_event = True
            continue

        if line == "END:VEVENT":
            if in_event:
                event = _build_event(
                    current_fields,
                    property_id=property_id,
                    property_name=property_name,
                    property_timezone=property_timezone,
                    calendar_id=calendar_id,
                    source=source,
                )
                if event:
                    events.append(event)
            in_event = False
            continue

        if not in_event:
            continue

        parsed_line = _parse_content_line(line)
        if not parsed_line:
            continue

        name, params, value = parsed_line
        current_fields.setdefault(name, []).append((params, value))

    return events


def _unfold_lines(body: str) -> list[str]:
    unfolded: list[str] = []
    for raw_line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw_line:
            continue
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
        else:
            unfolded.append(raw_line)
    return unfolded


def _parse_content_line(line: str) -> tuple[str, dict[str, str], str] | None:
    if ":" not in line:
        return None

    head, value = line.split(":", 1)
    parts = head.split(";")
    name = parts[0].upper().strip()
    params: dict[str, str] = {}

    for part in parts[1:]:
        if "=" not in part:
            continue
        key, param_value = part.split("=", 1)
        params[key.upper().strip()] = param_value.strip()

    return name, params, value.strip()


def _build_event(
    fields: dict[str, list[tuple[dict[str, str], str]]],
    *,
    property_id: str,
    property_name: str,
    property_timezone: str,
    calendar_id: str,
    source: str,
) -> BookingEvent | None:
    start_value = _first_field(fields, "DTSTART")
    if start_value is None:
        return None

    start_date = _parse_ical_date(
        start_value[1], params=start_value[0], fallback_timezone=property_timezone
    )

    end_value = _first_field(fields, "DTEND")
    if end_value is None:
        end_date = start_date + timedelta(days=1)
    else:
        end_date = _parse_ical_date(
            end_value[1], params=end_value[0], fallback_timezone=property_timezone
        )

    if end_date <= start_date:
        end_date = start_date + timedelta(days=1)

    summary = ""
    summary_value = _first_field(fields, "SUMMARY")
    if summary_value is not None:
        summary = _unescape_text(summary_value[1])

    uid_value = _first_field(fields, "UID")
    uid = _unescape_text(uid_value[1]) if uid_value is not None else ""
    if not uid:
        uid_seed = {
            "property_id": property_id,
            "calendar_id": calendar_id,
            "source": source,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "summary": summary,
        }
        uid = hashlib.sha1(
            json.dumps(uid_seed, sort_keys=True).encode("utf-8")
        ).hexdigest()

    fingerprint_seed = {
        "property_id": property_id,
        "calendar_id": calendar_id,
        "source": source,
        "uid": uid,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
    }
    fingerprint = hashlib.sha1(
        json.dumps(fingerprint_seed, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return BookingEvent(
        property_id=property_id,
        property_name=property_name,
        property_timezone=property_timezone,
        calendar_id=calendar_id,
        source=source,
        uid=uid,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        summary=summary,
        fingerprint=fingerprint,
    )


def _first_field(
    fields: dict[str, list[tuple[dict[str, str], str]]], name: str
) -> tuple[dict[str, str], str] | None:
    values = fields.get(name)
    if not values:
        return None
    return values[0]


def _parse_ical_date(
    raw_value: str, *, params: dict[str, str], fallback_timezone: str
) -> date:
    value = raw_value.strip()
    value_type = params.get("VALUE", "").upper()
    if value_type == "DATE" or len(value) == 8:
        return datetime.strptime(value, "%Y%m%d").date()

    fmt = "%Y%m%dT%H%M%S"
    target_zone = _zone_or_utc(fallback_timezone)

    if value.endswith("Z"):
        parsed = datetime.strptime(value[:-1], fmt).replace(tzinfo=timezone.utc)
        return parsed.astimezone(target_zone).date()

    source_zone = _zone_or_utc(params.get("TZID") or fallback_timezone)
    parsed = datetime.strptime(value, fmt).replace(tzinfo=source_zone)
    return parsed.astimezone(target_zone).date()


def _zone_or_utc(name: str | None) -> timezone | ZoneInfo:
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def _unescape_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
        .strip()
    )

