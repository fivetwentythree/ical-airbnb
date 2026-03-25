from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen


USER_AGENT = "ical-airbnb/0.1"


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    body: str | None
    etag: Optional[str]
    last_modified: Optional[str]
    not_modified: bool = False


def fetch_feed(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout_seconds: int = 20,
) -> FetchResult:
    headers = {
        "Accept": "text/calendar, text/plain;q=0.9, */*;q=0.8",
        "User-Agent": USER_AGENT,
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    request = Request(url, headers=headers, method="GET")

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body_bytes = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            body = body_bytes.decode(charset, errors="replace")
            return FetchResult(
                status_code=response.status,
                body=body,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                not_modified=False,
            )
    except HTTPError as exc:
        if exc.code == 304:
            return FetchResult(
                status_code=304,
                body=None,
                etag=etag,
                last_modified=last_modified,
                not_modified=True,
            )
        raise

