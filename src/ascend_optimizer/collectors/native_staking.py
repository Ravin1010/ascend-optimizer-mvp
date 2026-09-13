"""Collector for a sampled Native 0G staking benchmark.

Yield is derived from a transparent sample of active validators on the official
0G Explorer. The collector also resolves the three exposure inputs that were
blocking optimizer eligibility:

* delegation-depth capacity in USD;
* on-chain undelegation delay converted from blocks to days;
* a documented severe-slash stress scenario.

The severe-slash value is intentionally MODELLED rather than presented as a
verified current mainnet parameter. It uses the 5% default double-sign slash
fraction from 0G Foundation's Cosmos SDK fork as the MVP stress scenario until a
mainnet-specific slashing-parameter endpoint is verified.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re
from typing import Any, Callable, Iterable

from bs4 import BeautifulSoup

from .common import CollectionError, fetch_html, fetch_json, rpc_call, utc_now_iso


STRATEGY_ID = "NATIVE_STAKE_0G"
EXPLORER_BASE = "https://explorer.0g.ai/mainnet/validators"

RPC_URL = "https://evmrpc.0g.ai"
STAKING_CONTRACT = "0xea224dBB52F57752044c0C86aD50930091F561B9"
MIN_WITHDRAWABILITY_DELAY_SELECTOR = "0x279a0d76"

GECKO_NETWORK = "0g"
GECKO_API_BASE = "https://api.geckoterminal.com/api/v2"
W0G_TOKEN = "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c"
GECKO_HEADERS = {
    "Accept": "application/json;version=20230203",
}

RECENT_BLOCK_WINDOW = 1_000
SECONDS_PER_DAY = 86_400.0

# Modelled stress scenario, not asserted as the current mainnet configuration.
# 0G Foundation's Cosmos SDK fork defaults double-sign slashing to 1/20 = 5%.
MODELLED_SEVERE_SLASH_STRESS = 0.05

DEFAULT_VALIDATOR_SAMPLE = (
    "0xec856948cf28a7c36e4c0d7877d027ba0a8af17d",
    "0x33f59323858ee0f29f5cc9e5abc05d42a424225f",
    "0x54c2a4ca7742175f297946c28beaa69540f88867",
    "0x77d9f3a83cc0af0a4f7e9dcd78ebae967248f494",
)

RpcFn = Callable[[str, str, list[Any]], Any]
JsonFn = Callable[..., Any]


@dataclass(frozen=True)
class ValidatorObservation:
    """One validator observation parsed from the official 0G Explorer."""

    address: str
    status: str
    total_delegations_0g: float
    staking_apy: float
    commission_rate: float
    source_url: str


@dataclass(frozen=True)
class NativeNetworkObservation:
    """Network/market inputs needed by the Native 0G exposure model."""

    price_usd: float | None
    withdrawal_delay_blocks: int | None
    average_block_seconds: float | None
    exit_time_days: float | None
    slashing_stress_loss: float


def _page_text(html_or_text: str) -> str:
    return BeautifulSoup(html_or_text, "html.parser").get_text(" ", strip=True)


def _required_match(pattern: str, text: str, field: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        raise CollectionError(f"Could not parse {field} from validator page")
    return match.group(1)


def _hex_to_int(value: str, field: str) -> int:
    try:
        return int(value, 16)
    except (TypeError, ValueError) as exc:
        raise CollectionError(
            f"Invalid hexadecimal {field}: {value!r}"
        ) from exc


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


def fetch_0g_price_usd(
    *,
    json_fn: JsonFn | None = None,
) -> float:
    """Fetch the current W0G USD price from GeckoTerminal."""

    fetcher = json_fn or fetch_json
    url = (
        f"{GECKO_API_BASE}/simple/networks/{GECKO_NETWORK}/"
        f"token_price/{W0G_TOKEN}"
    )
    payload = fetcher(url, headers=GECKO_HEADERS)

    try:
        prices = payload["data"]["attributes"]["token_prices"]
    except (TypeError, KeyError) as exc:
        raise CollectionError(
            "Malformed GeckoTerminal W0G token-price response"
        ) from exc

    raw = (
        prices.get(W0G_TOKEN)
        or prices.get(W0G_TOKEN.lower())
        or prices.get(W0G_TOKEN.upper())
    )
    if raw is None:
        # Some responses normalize keys to lowercase.
        for key, value in prices.items():
            if str(key).lower() == W0G_TOKEN.lower():
                raw = value
                break

    try:
        price = float(raw)
    except (TypeError, ValueError) as exc:
        raise CollectionError(
            f"Invalid W0G USD price from GeckoTerminal: {raw!r}"
        ) from exc

    if not isfinite(price) or price <= 0:
        raise CollectionError(
            f"W0G USD price must be finite and > 0, got {price!r}"
        )

    return price


def fetch_withdrawal_delay_observation(
    *,
    rpc_fn: RpcFn | None = None,
    block_window: int = RECENT_BLOCK_WINDOW,
) -> tuple[int, float, float]:
    """Return withdrawal-delay blocks, recent block seconds, and delay days.

    The official 0G staking documentation identifies minWithdrawabilityDelay as
    the network withdrawal delay in blocks. We read that public contract getter
    and convert it to days using a recent observed block-time window.
    """

    if block_window <= 0:
        raise CollectionError("block_window must be > 0")

    rpc = rpc_fn or rpc_call

    raw_delay = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": STAKING_CONTRACT,
                "data": MIN_WITHDRAWABILITY_DELAY_SELECTOR,
            },
            "latest",
        ],
    )
    delay_blocks = _hex_to_int(raw_delay, "minWithdrawabilityDelay")
    if delay_blocks < 0:
        raise CollectionError("withdrawal delay blocks cannot be negative")

    latest_hex = rpc(RPC_URL, "eth_blockNumber", [])
    latest = _hex_to_int(latest_hex, "latest block number")

    earlier = max(0, latest - block_window)
    if earlier == latest:
        raise CollectionError("Not enough block history to estimate block time")

    latest_block = rpc(
        RPC_URL,
        "eth_getBlockByNumber",
        [hex(latest), False],
    )
    earlier_block = rpc(
        RPC_URL,
        "eth_getBlockByNumber",
        [hex(earlier), False],
    )

    if not isinstance(latest_block, dict) or not isinstance(earlier_block, dict):
        raise CollectionError("Missing block data while estimating block time")

    latest_ts = _hex_to_int(
        latest_block.get("timestamp"),
        "latest block timestamp",
    )
    earlier_ts = _hex_to_int(
        earlier_block.get("timestamp"),
        "earlier block timestamp",
    )

    elapsed_blocks = latest - earlier
    elapsed_seconds = latest_ts - earlier_ts

    if elapsed_blocks <= 0 or elapsed_seconds <= 0:
        raise CollectionError(
            "Invalid recent block window for block-time estimation"
        )

    average_block_seconds = elapsed_seconds / elapsed_blocks
    exit_time_days = (
        delay_blocks * average_block_seconds / SECONDS_PER_DAY
    )

    return delay_blocks, average_block_seconds, exit_time_days


def collect_network_observation() -> tuple[NativeNetworkObservation, list[str]]:
    """Collect market/delegation exposure inputs with graceful degradation."""

    failures: list[str] = []

    try:
        price_usd = fetch_0g_price_usd()
    except CollectionError as exc:
        price_usd = None
        failures.append(f"price:{exc}")

    try:
        delay_blocks, average_block_seconds, exit_time_days = (
            fetch_withdrawal_delay_observation()
        )
    except CollectionError as exc:
        delay_blocks = None
        average_block_seconds = None
        exit_time_days = None
        failures.append(f"withdrawal_delay:{exc}")

    return (
        NativeNetworkObservation(
            price_usd=price_usd,
            withdrawal_delay_blocks=delay_blocks,
            average_block_seconds=average_block_seconds,
            exit_time_days=exit_time_days,
            slashing_stress_loss=MODELLED_SEVERE_SLASH_STRESS,
        ),
        failures,
    )


def build_native_snapshot(
    observations: Iterable[ValidatorObservation],
    *,
    network: NativeNetworkObservation | None = None,
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

    price_usd = network.price_usd if network is not None else None
    delegation_depth_usd = (
        total_weight * price_usd
        if price_usd is not None
        else None
    )
    exit_time_days = (
        network.exit_time_days
        if network is not None
        else None
    )
    slashing_stress_loss = (
        network.slashing_stress_loss
        if network is not None
        else None
    )

    exposure_complete = (
        delegation_depth_usd is not None
        and exit_time_days is not None
        and slashing_stress_loss is not None
    )
    data_status = (
        "PARTIAL_MODELLED"
        if exposure_complete
        else "LIVE_INCOMPLETE"
    )

    addresses = "|".join(item.address for item in active)

    network_note = ""
    if network is not None:
        network_note = (
            f"; price_usd={network.price_usd}; "
            f"sample_delegation_0g={total_weight:.6f}; "
            f"withdrawal_delay_blocks={network.withdrawal_delay_blocks}; "
            f"avg_block_seconds={network.average_block_seconds}; "
            f"slash_stress={network.slashing_stress_loss:.4f} "
            "(MODELLED severe scenario from 0G Foundation Cosmos SDK "
            "default double-sign fraction; not asserted as current "
            "mainnet slashing parameter)"
        )

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": None,
        "gross_apy": weighted_apy,
        "incentive_apy": 0.0,
        "yield_fee_status": "UNKNOWN",
        # This is sampled delegation depth, not a network-wide TVL census.
        "tvl_usd": delegation_depth_usd,
        # Used by the MVP optimizer as a conservative capacity proxy.
        "liquidity_usd": delegation_depth_usd,
        "volume_24h_usd": None,
        "protocol_fee_rate": None,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": 0.0,
        "exit_slippage_rate": 0.0,
        "exit_time_days": exit_time_days,
        "slashing_stress_loss": slashing_stress_loss,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": data_status,
        "source": (
            "0G_EXPLORER_STAKING_CONTRACT_GECKOTERMINAL"
        ),
        "notes": (
            f"Delegation-weighted APY from {len(active)} active sampled validators; "
            f"weighted commission={weighted_commission:.6f}; "
            f"validators={addresses}; not a network-wide validator census"
            f"{network_note}"
        ),
    }


def collect_native_staking_snapshot(
    validators: Iterable[str] = DEFAULT_VALIDATOR_SAMPLE,
) -> dict[str, object]:
    """Collect the sampled Native 0G staking benchmark and exposures."""

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

    network, network_failures = collect_network_observation()
    failures.extend(network_failures)

    snapshot = build_native_snapshot(
        observations,
        network=network,
    )

    if failures:
        snapshot["notes"] = (
            str(snapshot["notes"])
            + "; collection_failures="
            + " | ".join(failures)
        )

    return snapshot
