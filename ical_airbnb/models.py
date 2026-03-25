from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BookingEvent:
    property_id: str
    property_name: str
    property_timezone: str
    calendar_id: str
    source: str
    uid: str
    start_date: str
    end_date: str
    summary: str
    fingerprint: str

    @property
    def state_key(self) -> str:
        return self.uid

    def to_state(self) -> dict[str, str]:
        return {
            "property_id": self.property_id,
            "property_name": self.property_name,
            "property_timezone": self.property_timezone,
            "calendar_id": self.calendar_id,
            "source": self.source,
            "uid": self.uid,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "summary": self.summary,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_state(cls, data: dict[str, Any]) -> "BookingEvent":
        return cls(
            property_id=str(data["property_id"]),
            property_name=str(data["property_name"]),
            property_timezone=str(data["property_timezone"]),
            calendar_id=str(data["calendar_id"]),
            source=str(data["source"]),
            uid=str(data["uid"]),
            start_date=str(data["start_date"]),
            end_date=str(data["end_date"]),
            summary=str(data.get("summary", "")),
            fingerprint=str(data["fingerprint"]),
        )

