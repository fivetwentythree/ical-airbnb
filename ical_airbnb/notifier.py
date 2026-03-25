from __future__ import annotations

import json
from urllib.request import Request, urlopen


def send_discord_message(webhook_url: str, content: str, *, timeout_seconds: int = 15) -> None:
    payload = json.dumps({"content": content}).encode("utf-8")
    request = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"Discord webhook failed with status {response.status}")

