"""Collector for a sampled Native 0G staking benchmark.

The official Explorer exposes validator-specific APY rather than one network-wide
staking APY. Until an official all-validator API is integrated, this collector
uses a transparent, version-controlled sample of active validators and computes
a delegation-weighted APY. The result must therefore be described as a sampled
benchmark, not as the exact network-wide staking yield.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from bs4 import BeautifulSoup

from .common import CollectionError, fetch_html, utc_now_iso


STRATEGY_ID = "NATIVE_STAKE_0G"
EXPLORER_BASE = "https://explorer.0g.ai/mainnet/validators"

DEFAULT_VALIDATOR_SAMPLE = (
    "0xec856948cf28a7c36e4c0d7877d027ba0a8af17d",
    "0x33f59323858ee0f29f5cc9e5abc05d42a424225f",
    "0x54c2a4ca7742175f297946c28beaa69540f88867",
    "0x77d9f3a83cc0af0a4f7e9dcd78ebae967248f494",
)


@dataclass(frozen=True)
class ValidatorObservation:
    """One validator observation parsed from the official 0G Explorer."""

    address: str
    status: str
    total_delegations_0g: float
    staking_apy: float
    commission_rate: float
    source_url: str


def _page_text(html_or_text: str) -> str:
    return BeautifulSoup(html_or_text, "html.parser").get_text(" ", strip=True)


def _required_match(pattern: str, text: str, field: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        raise CollectionError(f"Could not parse {field} from validator page")
    return match.group(1)


def parse_validator_page(
    html_or_text: str,
    *,
    address: str,
    source_url: str,
) -> ValidatorObservation:
    """Parse status, delegation, APY, and commission from one Explorer page."""

    text = _page_text(html_or_text)

    status = _required_match(
        r"Status\s+(ACTIVE|INACTIVE)",
        text,
        "status",
    ).upper()
    delegation = float(
        _required_match(
            r"Total\s+Delegations\s+([0-9][0-9,]*(?:\.[0-9]+)?)\s+0G",
            text,
            "total delegations",
        ).replace(",", "")
    )
    staking_apy = float(
        _required_match(
            r"Staking\s+APY\s+([0-9]+(?:\.[0-9]+)?)%",
            text,
            "staking APY",
        )
    ) / 100.0
    commission = float(
        _required_match(
            r"Commission\s+([0-9]+(?:\.[0-9]+)?)%",
            text,
            "commission",
        )
    ) / 100.0

    return ValidatorObservation(
        address=address,
        status=status,
        total_delegations_0g=delegation,
        staking_apy=staking_apy,
        commission_rate=commission,
        source_url=source_url,
    )


def fetch_validator_observation(address: str) -> ValidatorObservation:
    """Fetch and parse one validator from the official 0G Explorer."""

    url = f"{EXPLORER_BASE}/{address}/delegators"
    return parse_validator_page(
        fetch_html(url),
        address=address,
        source_url=url,
    )


def build_native_snapshot(
    observations: Iterable[ValidatorObservation],
    *,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build one snapshot row from active sampled validator observations."""

    active = [item for item in observations if item.status == "ACTIVE"]
    if not active:
        raise CollectionError("No ACTIVE validator observations available")

    total_weight = sum(item.total_delegations_0g for item in active)
    if total_weight <= 0:
        raise CollectionError("Active validator sample has zero delegation weight")

    weighted_apy = sum(
        item.staking_apy * item.total_delegations_0g
        for item in active
    ) / total_weight

    weighted_commission = sum(
        item.commission_rate * item.total_delegations_0g
        for item in active
    ) / total_weight

    addresses = "|".join(item.address for item in active)

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": None,
        "gross_apy": weighted_apy,
        "incentive_apy": 0.0,
        "yield_fee_status": "UNKNOWN",
        "tvl_usd": None,
        "liquidity_usd": None,
        "volume_24h_usd": None,
        "protocol_fee_rate": None,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": 0.0,
        "exit_slippage_rate": 0.0,
        "exit_time_days": None,
        "slashing_stress_loss": None,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": "LIVE_INCOMPLETE",
        "source": "0G_EXPLORER_VALIDATOR_SAMPLE",
        "notes": (
            f"Delegation-weighted APY from {len(active)} active sampled validators; "
            f"weighted commission={weighted_commission:.6f}; "
            f"validators={addresses}; not a network-wide validator census"
        ),
    }


def collect_native_staking_snapshot(
    validators: Iterable[str] = DEFAULT_VALIDATOR_SAMPLE,
) -> dict[str, object]:
    """Collect the sampled Native 0G staking benchmark."""

    observations: list[ValidatorObservation] = []
    failures: list[str] = []

    for address in validators:
        try:
            observations.append(fetch_validator_observation(address))
        except CollectionError as exc:
            failures.append(f"{address}:{exc}")

    if not observations:
        raise CollectionError(
            "Native staking collection failed for every sampled validator: "
            + " | ".join(failures)
        )

    snapshot = build_native_snapshot(observations)

    if failures:
        snapshot["notes"] = (
            str(snapshot["notes"])
            + "; collection_failures="
            + " | ".join(failures)
        )

    return snapshot
