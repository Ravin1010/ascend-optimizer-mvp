"""Merkl incentive APR integration for LP strategies.

Merkl opportunity APR may include protocol/native APR. To avoid double counting
our independently-derived swap-fee APR, this module uses only aprRecord
breakdowns whose type is CAMPAIGN.

Merkl expresses APR values as percentages (for example 4.2 means 4.2%). The
collector converts the summed campaign APR to a decimal APY using daily
compounding before placing it in the frozen incentive_apy snapshot field.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable
from urllib.parse import urlencode

from .common import CollectionError, fetch_json
from ..net_return_engine import apr_to_apy


MERKL_API_BASE = "https://api.merkl.xyz/v4/opportunities"
OG_CHAIN_ID = 16661

JsonFn = Callable[..., Any]


@dataclass(frozen=True)
class MerklIncentiveObservation:
    """Pool-specific active Merkl campaign yield."""

    pool_address: str
    campaign_apr: float
    incentive_apy: float
    matched_opportunities: int
    matched_campaigns: int

    @property
    def has_active_incentive(self) -> bool:
        return self.campaign_apr > 0


def _finite_non_negative(value: Any) -> float | None:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(converted) or converted < 0:
        return None

    return converted


def parse_merkl_campaign_incentive(
    payload: Any,
    *,
    pool_address: str,
) -> MerklIncentiveObservation:
    """Extract unique CAMPAIGN APR breakdowns for one pool."""

    if not isinstance(payload, list):
        raise CollectionError("Merkl opportunities response must be a list")

    target = pool_address.lower()
    matching = [
        item
        for item in payload
        if isinstance(item, dict)
        and str(item.get("identifier", "")).lower() == target
        and str(item.get("status", "LIVE")).upper() == "LIVE"
    ]

    campaign_aprs_percent: dict[str, float] = {}

    for opportunity in matching:
        apr_record = opportunity.get("aprRecord")
        breakdowns = (
            apr_record.get("breakdowns", [])
            if isinstance(apr_record, dict)
            else []
        )

        for breakdown in breakdowns:
            if not isinstance(breakdown, dict):
                continue
            if str(breakdown.get("type", "")).upper() != "CAMPAIGN":
                continue

            value = _finite_non_negative(breakdown.get("value"))
            if value is None or value <= 0:
                continue

            identifier = str(breakdown.get("identifier", "")).strip()
            if not identifier:
                identifier = f"anonymous:{len(campaign_aprs_percent)}"

            campaign_aprs_percent[identifier] = max(
                campaign_aprs_percent.get(identifier, 0.0),
                value,
            )

    campaign_apr = sum(campaign_aprs_percent.values()) / 100.0
    incentive_apy = (
        apr_to_apy(campaign_apr, 365)
        if campaign_apr > 0
        else 0.0
    )

    return MerklIncentiveObservation(
        pool_address=pool_address,
        campaign_apr=campaign_apr,
        incentive_apy=incentive_apy,
        matched_opportunities=len(matching),
        matched_campaigns=len(campaign_aprs_percent),
    )


def fetch_merkl_pool_incentive(
    pool_address: str,
    *,
    chain_id: int = OG_CHAIN_ID,
    json_fn: JsonFn | None = None,
) -> MerklIncentiveObservation:
    """Fetch active Merkl campaign APR for one pool address."""

    fetcher = json_fn or fetch_json
    query = urlencode(
        {
            "chainId": chain_id,
            "identifier": pool_address,
            "status": "LIVE",
            "items": 100,
            "test": "false",
        }
    )
    url = f"{MERKL_API_BASE}?{query}"

    payload = fetcher(
        url,
        headers={"Accept": "application/json"},
    )

    return parse_merkl_campaign_incentive(
        payload,
        pool_address=pool_address,
    )
