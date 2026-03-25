from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when the app configuration is invalid."""


@dataclass(frozen=True)
class FeedConfig:
    id: str
    source: str
    url: str


@dataclass(frozen=True)
class PropertyConfig:
    id: str
    name: str
    timezone: str
    feeds: list[FeedConfig]


@dataclass(frozen=True)
class AppConfig:
    discord_webhook_url: str
    poll_interval_seconds: int
    properties: list[PropertyConfig]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)

    data = _resolve_env_values(raw_data)

    properties: list[PropertyConfig] = []
    seen_property_ids: set[str] = set()
    for property_data in data.get("properties", []):
        property_id = _required_str(property_data, "id")
        if property_id in seen_property_ids:
            raise ConfigError(f"Duplicate property id: {property_id}")
        seen_property_ids.add(property_id)

        seen_feed_ids: set[str] = set()
        feeds: list[FeedConfig] = []
        for feed_data in property_data.get("feeds", []):
            feed_source = _required_str(feed_data, "source")
            feed_id = str(feed_data.get("id", feed_source)).strip()
            if not feed_id:
                raise ConfigError(f"Feed id is required for property {property_id}")
            if feed_id in seen_feed_ids:
                raise ConfigError(
                    f"Duplicate feed id '{feed_id}' in property {property_id}"
                )
            seen_feed_ids.add(feed_id)
            feeds.append(
                FeedConfig(
                    id=feed_id,
                    source=feed_source,
                    url=_required_str(feed_data, "url"),
                )
            )

        if not feeds:
            raise ConfigError(f"Property {property_id} must include at least one feed")

        properties.append(
            PropertyConfig(
                id=property_id,
                name=_required_str(property_data, "name"),
                timezone=_required_str(property_data, "timezone"),
                feeds=feeds,
            )
        )

    if not properties:
        raise ConfigError("At least one property is required")

    return AppConfig(
        discord_webhook_url=_required_root_str(data, "discord_webhook_url"),
        poll_interval_seconds=int(data.get("poll_interval_seconds", 300)),
        properties=properties,
    )


def _resolve_env_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env_values(item) for item in value]
    if isinstance(value, str) and value.startswith("env:"):
        env_name = value.split(":", 1)[1]
        env_value = os.getenv(env_name)
        if not env_value:
            raise ConfigError(f"Missing required environment variable: {env_name}")
        return env_value
    return value


def _required_root_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config field '{key}' is required")
    return value.strip()


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config field '{key}' is required")
    return value.strip()

