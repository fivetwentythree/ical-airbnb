from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_STATE: dict[str, Any] = {
    "version": 1,
    "meta": {},
    "calendars": {},
    "notifications": {},
}


def load_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return deepcopy(DEFAULT_STATE)

    with state_path.open("r", encoding="utf-8") as handle:
        loaded = json.load(handle)

    state = deepcopy(DEFAULT_STATE)
    state.update(loaded)
    state.setdefault("meta", {})
    state.setdefault("calendars", {})
    state.setdefault("notifications", {})
    return state


def save_state(path: str | Path, state: dict[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")


def prune_notifications(state: dict[str, Any], *, max_age_days: int = 180) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    notifications = state.setdefault("notifications", {})
    for dedupe_key, record in list(notifications.items()):
        sent_at = record.get("sent_at")
        if not isinstance(sent_at, str):
            notifications.pop(dedupe_key, None)
            continue
        try:
            parsed = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
        except ValueError:
            notifications.pop(dedupe_key, None)
            continue
        if parsed < cutoff:
            notifications.pop(dedupe_key, None)

