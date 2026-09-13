"""On-chain collector for Gimo st0G liquid staking.

The public Gimo frontend is client-rendered and cannot be relied upon as a
machine-readable APR source. Instead, this collector derives a realized APY from
the st0G contract's on-chain getRate() value.

Gimo documentation states that staking rewards, after the protocol commission,
are reflected in the st0G exchange rate. Therefore growth in getRate() is
already net of Gimo's 10% reward commission and must not be charged again by the
Net Return Engine.

The collector compares the current exchange rate with a historical on-chain rate
(default lookback: seven days) and annualizes the realized growth. The public 0G
mainnet RPC is used for both block timestamps and historical eth_call queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

from .common import CollectionError, rpc_call, utc_now_iso


STRATEGY_ID = "GIMO_STAKE_0G"

RPC_URL = "https://evmrpc.0g.ai"
ST0G_TOKEN_CONTRACT = "0x7bBC63D01CA42491c3E084C941c3E86e55951404"
STAKE_CONTRACT = "0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF"

# keccak256("getRate()")[:4]
GET_RATE_SELECTOR = "0x679aefce"

RATE_SCALE = 10**18
SECONDS_PER_DAY = 86_400
SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY
DEFAULT_LOOKBACK_SECONDS = 7 * SECONDS_PER_DAY

DOCUMENTED_REWARD_COMMISSION = 0.10
DOCUMENTED_EPOCH_DAYS = 22.0

RpcFn = Callable[[str, str, list[Any]], Any]


@dataclass(frozen=True)
class GimoRateObservation:
    """Current and historical st0G exchange-rate observation."""

    current_rate: float
    previous_rate: float
    current_block: int
    previous_block: int
    current_timestamp: int
    previous_timestamp: int
    elapsed_seconds: int
    realized_apy: float


def _hex_to_int(value: str, field: str) -> int:
    try:
        return int(value, 16)
    except (TypeError, ValueError) as exc:
        raise CollectionError(
            f"Invalid hexadecimal {field}: {value!r}"
        ) from exc


def _block(
    rpc: RpcFn,
    block_number: int,
) -> dict[str, Any]:
    result = rpc(
        RPC_URL,
        "eth_getBlockByNumber",
        [hex(block_number), False],
    )
    if not isinstance(result, dict):
        raise CollectionError(
            f"Missing block data for block {block_number}"
        )
    return result


def _block_timestamp(
    rpc: RpcFn,
    block_number: int,
) -> int:
    block = _block(rpc, block_number)
    return _hex_to_int(block.get("timestamp"), "block timestamp")


def _get_rate_at_block(
    rpc: RpcFn,
    block_number: int,
) -> float:
    raw = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": ST0G_TOKEN_CONTRACT,
                "data": GET_RATE_SELECTOR,
            },
            hex(block_number),
        ],
    )

    integer_rate = _hex_to_int(raw, "getRate result")
    if integer_rate <= 0:
        raise CollectionError(
            f"Gimo getRate returned non-positive value at block {block_number}"
        )

    return integer_rate / RATE_SCALE


def find_block_at_or_before_timestamp(
    target_timestamp: int,
    *,
    latest_block: int,
    rpc_fn: RpcFn | None = None,
) -> tuple[int, int]:
    """Binary-search the greatest block timestamp <= target_timestamp."""

    rpc = rpc_fn or rpc_call
    low = 0
    high = latest_block
    candidate_block = 0
    candidate_timestamp = _block_timestamp(rpc, 0)

    if candidate_timestamp > target_timestamp:
        raise CollectionError(
            "Target timestamp predates block 0"
        )

    while low <= high:
        mid = (low + high) // 2
        timestamp = _block_timestamp(rpc, mid)

        if timestamp <= target_timestamp:
            candidate_block = mid
            candidate_timestamp = timestamp
            low = mid + 1
        else:
            high = mid - 1

    return candidate_block, candidate_timestamp


def annualize_exchange_rate_growth(
    current_rate: float,
    previous_rate: float,
    elapsed_seconds: int,
) -> float:
    """Annualize realized growth in the net-of-fee st0G exchange rate."""

    current_rate = float(current_rate)
    previous_rate = float(previous_rate)

    if (
        not isfinite(current_rate)
        or not isfinite(previous_rate)
        or current_rate <= 0
        or previous_rate <= 0
    ):
        raise CollectionError("Exchange rates must be finite and > 0")

    if elapsed_seconds <= 0:
        raise CollectionError("elapsed_seconds must be > 0")

    if current_rate < previous_rate:
        raise CollectionError(
            "st0G exchange rate decreased over the observation window"
        )

    return (
        (current_rate / previous_rate)
        ** (SECONDS_PER_YEAR / elapsed_seconds)
        - 1.0
    )


def fetch_gimo_rate_observation(
    *,
    lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS,
    rpc_fn: RpcFn | None = None,
) -> GimoRateObservation:
    """Fetch current/historical getRate() values and derive realized APY."""

    if lookback_seconds <= 0:
        raise CollectionError("lookback_seconds must be > 0")

    rpc = rpc_fn or rpc_call

    latest_hex = rpc(RPC_URL, "eth_blockNumber", [])
    latest_block = _hex_to_int(latest_hex, "latest block number")
    current_timestamp = _block_timestamp(rpc, latest_block)

    target_timestamp = current_timestamp - lookback_seconds
    previous_block, previous_timestamp = (
        find_block_at_or_before_timestamp(
            target_timestamp,
            latest_block=latest_block,
            rpc_fn=rpc,
        )
    )

    current_rate = _get_rate_at_block(rpc, latest_block)
    previous_rate = _get_rate_at_block(rpc, previous_block)

    elapsed_seconds = current_timestamp - previous_timestamp
    realized_apy = annualize_exchange_rate_growth(
        current_rate,
        previous_rate,
        elapsed_seconds,
    )

    return GimoRateObservation(
        current_rate=current_rate,
        previous_rate=previous_rate,
        current_block=latest_block,
        previous_block=previous_block,
        current_timestamp=current_timestamp,
        previous_timestamp=previous_timestamp,
        elapsed_seconds=elapsed_seconds,
        realized_apy=realized_apy,
    )


def build_gimo_snapshot(
    observation: GimoRateObservation,
    *,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build one optimizer snapshot from on-chain exchange-rate growth."""

    lookback_days = observation.elapsed_seconds / SECONDS_PER_DAY

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": None,
        "gross_apy": observation.realized_apy,
        "incentive_apy": 0.0,
        # getRate growth reflects rewards after Gimo's documented commission.
        "yield_fee_status": "NET_OF_PROTOCOL_FEES",
        "tvl_usd": None,
        "liquidity_usd": None,
        "volume_24h_usd": None,
        # Retained as provenance/informational metadata; the return engine will
        # not deduct it again because yield_fee_status is NET_OF_PROTOCOL_FEES.
        "protocol_fee_rate": DOCUMENTED_REWARD_COMMISSION,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": 0.0,
        "exit_slippage_rate": 0.0,
        "exit_time_days": DOCUMENTED_EPOCH_DAYS,
        "slashing_stress_loss": None,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": "LIVE_INCOMPLETE",
        "source": "GIMO_ONCHAIN_GETRATE",
        "notes": (
            "Realized net-of-protocol-fee APY annualized from st0G getRate(); "
            f"lookback_days={lookback_days:.3f}; "
            f"rate_now={observation.current_rate:.18f}; "
            f"rate_then={observation.previous_rate:.18f}; "
            f"block_now={observation.current_block}; "
            f"block_then={observation.previous_block}; "
            "documented reward commission=10%; "
            "withdrawals aligned with 22-day epoch cycle; "
            f"st0G={ST0G_TOKEN_CONTRACT}; stake={STAKE_CONTRACT}"
        ),
    }


def collect_gimo_snapshot() -> dict[str, object]:
    """Collect Gimo yield from on-chain st0G exchange-rate growth."""

    observation = fetch_gimo_rate_observation()
    return build_gimo_snapshot(observation)
