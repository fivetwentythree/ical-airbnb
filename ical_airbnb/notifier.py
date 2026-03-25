from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from .detector import NotificationCandidate


def send_discord_message(
    webhook_url: str, notification: NotificationCandidate, *, timeout_seconds: int = 15
) -> None:
    embed = {
        "title": notification.title,
        "color": notification.color,
        "fields": [
            {
                "name": field.name,
                "value": field.value,
                "inline": field.inline,
            }
            for field in notification.fields
        ],
        "footer": {"text": "Airbnb iCal Monitor"},
        "timestamp": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    payload = json.dumps(
        {
            "username": "Airbnb iCal Monitor",
            "embeds": [embed],
        }
    ).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"Discord webhook failed with status {response.status}")
