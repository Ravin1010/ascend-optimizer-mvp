"""Shared helpers for live strategy data collectors."""

from __future__ import annotations

from datetime import datetime, timezone

import requests


DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_HEADERS = {
    "User-Agent": "ascend-optimizer-mvp/0.1 (+NTU capstone research)"
}


class CollectionError(RuntimeError):
    """Raised when a live source cannot be collected or parsed safely."""


def utc_now_iso() -> str:
    """Return a timezone-aware UTC timestamp suitable for snapshot CSVs."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_html(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Fetch one public source page with a deterministic user agent."""

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CollectionError(f"Failed to fetch {url}: {exc}") from exc

    return response.text
