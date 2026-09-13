"""Shared helpers for live strategy data collectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

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


def fetch_html(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    *,
    headers: Mapping[str, str] | None = None,
) -> str:
    """Fetch one public source page."""

    request_headers = dict(DEFAULT_HEADERS)
    if headers:
        request_headers.update(headers)

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers=request_headers,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CollectionError(f"Failed to fetch {url}: {exc}") from exc

    return response.text


def rpc_call(
    url: str,
    method: str,
    params: list[Any],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    """Execute one JSON-RPC request and return its result."""

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CollectionError(
            f"RPC request failed: method={method}, url={url}: {exc}"
        ) from exc

    if "error" in body:
        raise CollectionError(
            f"RPC error for {method}: {body['error']}"
        )

    if "result" not in body:
        raise CollectionError(
            f"RPC response missing result for {method}"
        )

    return body["result"]


def fetch_json(
    url: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    *,
    headers: Mapping[str, str] | None = None,
) -> Any:
    """Fetch one public JSON endpoint and return the decoded payload."""

    request_headers = dict(DEFAULT_HEADERS)
    request_headers["Accept"] = "application/json"
    if headers:
        request_headers.update(headers)

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers=request_headers,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CollectionError(f"Failed to fetch JSON {url}: {exc}") from exc
