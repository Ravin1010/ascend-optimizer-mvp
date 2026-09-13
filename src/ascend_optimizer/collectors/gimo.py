"""On-chain collector for Gimo st0G liquid staking.

The public 0G RPC is not an archive node, so historical eth_call queries can
fail with "missing trie node". The collector therefore samples the current
st0G getRate() value and stores it in a local rate-history CSV. Once at least
one sufficiently old local sample exists, it annualizes exchange-rate growth
into a realized trailing APY.

Gimo documentation states that staking rewards after protocol commission are
reflected in the st0G exchange rate. Derived APY is therefore marked
NET_OF_PROTOCOL_FEES so the documented 10% commission is not deducted twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .common import CollectionError, rpc_call, utc_now_iso
from .native_staking import (
    MODELLED_SEVERE_SLASH_STRESS,
    fetch_0g_price_usd,
)


STRATEGY_ID = "GIMO_STAKE_0G"

RPC_URL = "https://evmrpc.0g.ai"
ST0G_TOKEN_CONTRACT = "0x7bBC63D01CA42491c3E084C941c3E86e55951404"
STAKE_CONTRACT = "0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF"

# keccak256("getRate()")[:4]
GET_RATE_SELECTOR = "0x679aefce"
TOTAL_SUPPLY_SELECTOR = "0x18160ddd"
DECIMALS_SELECTOR = "0x313ce567"

RATE_SCALE = 10**18
SECONDS_PER_DAY = 86_400
SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY
DEFAULT_LOOKBACK_SECONDS = 7 * SECONDS_PER_DAY
MIN_HISTORY_SECONDS = 24 * 60 * 60

DOCUMENTED_REWARD_COMMISSION = 0.10
DOCUMENTED_EPOCH_DAYS = 22.0

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RATE_HISTORY_PATH = PROJECT_ROOT / "data" / "gimo_rate_history.csv"
RATE_HISTORY_COLUMNS = ("timestamp", "block_number", "rate")

RpcFn = Callable[[str, str, list[Any]], Any]


@dataclass(frozen=True)
class GimoRateSample:
    """One current on-chain st0G exchange-rate sample."""

    rate: float
    block_number: int
    block_timestamp: int


@dataclass(frozen=True)
class GimoRateObservation:
    """Current/reference samples plus derived realized APY."""

    current: GimoRateSample
    reference: GimoRateSample | None
    realized_apy: float | None

    @property
    def elapsed_seconds(self) -> int | None:
        if self.reference is None:
            return None
        return self.current.block_timestamp - self.reference.block_timestamp


@dataclass(frozen=True)
class GimoNetworkObservation:
    """Current st0G supply/depth and modelled underlying staking stress."""

    total_supply_st0g: float
    tvl_0g: float
    price_usd: float
    tvl_usd: float
    slashing_stress_loss: float


def _hex_to_int(value: str, field: str) -> int:
    try:
        return int(value, 16)
    except (TypeError, ValueError) as exc:
        raise CollectionError(
            f"Invalid hexadecimal {field}: {value!r}"
        ) from exc


def _block_timestamp(
    rpc: RpcFn,
    block_number: int,
) -> int:
    result = rpc(
        RPC_URL,
        "eth_getBlockByNumber",
        [hex(block_number), False],
    )
    if not isinstance(result, dict):
        raise CollectionError(
            f"Missing block data for block {block_number}"
        )
    return _hex_to_int(result.get("timestamp"), "block timestamp")


def _get_current_rate(
    rpc: RpcFn,
) -> float:
    raw = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": ST0G_TOKEN_CONTRACT,
                "data": GET_RATE_SELECTOR,
            },
            "latest",
        ],
    )

    integer_rate = _hex_to_int(raw, "getRate result")
    if integer_rate <= 0:
        raise CollectionError("Gimo getRate returned a non-positive value")

    return integer_rate / RATE_SCALE


def fetch_current_gimo_rate_sample(
    *,
    rpc_fn: RpcFn | None = None,
) -> GimoRateSample:
    """Fetch the current block/timestamp and current st0G getRate()."""

    rpc = rpc_fn or rpc_call

    latest_hex = rpc(RPC_URL, "eth_blockNumber", [])
    latest_block = _hex_to_int(latest_hex, "latest block number")
    timestamp = _block_timestamp(rpc, latest_block)
    rate = _get_current_rate(rpc)

    return GimoRateSample(
        rate=rate,
        block_number=latest_block,
        block_timestamp=timestamp,
    )


def fetch_gimo_network_observation(
    current_rate: float,
    *,
    rpc_fn: RpcFn | None = None,
    price_fn: Callable[[], float] = fetch_0g_price_usd,
) -> GimoNetworkObservation:
    """Derive current Gimo depth from st0G supply and the live exchange rate."""

    rpc = rpc_fn or rpc_call

    raw_supply = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": ST0G_TOKEN_CONTRACT,
                "data": TOTAL_SUPPLY_SELECTOR,
            },
            "latest",
        ],
    )
    raw_decimals = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": ST0G_TOKEN_CONTRACT,
                "data": DECIMALS_SELECTOR,
            },
            "latest",
        ],
    )

    supply_integer = _hex_to_int(raw_supply, "st0G totalSupply")
    decimals = _hex_to_int(raw_decimals, "st0G decimals")

    if decimals < 0 or decimals > 36:
        raise CollectionError(f"Unexpected st0G decimals: {decimals}")

    total_supply_st0g = supply_integer / (10 ** decimals)
    if total_supply_st0g < 0:
        raise CollectionError("st0G total supply cannot be negative")

    price_usd = float(price_fn())
    if not isfinite(price_usd) or price_usd <= 0:
        raise CollectionError("0G USD price must be finite and > 0")

    tvl_0g = total_supply_st0g * float(current_rate)
    tvl_usd = tvl_0g * price_usd

    return GimoNetworkObservation(
        total_supply_st0g=total_supply_st0g,
        tvl_0g=tvl_0g,
        price_usd=price_usd,
        tvl_usd=tvl_usd,
        # Gimo has no separate protocol slashing mechanism, but users remain
        # exposed to the underlying validator set. Reuse the same transparent
        # severe-staking stress scenario as Native 0G.
        slashing_stress_loss=MODELLED_SEVERE_SLASH_STRESS,
    )


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


def load_rate_history(path: Path = DEFAULT_RATE_HISTORY_PATH) -> pd.DataFrame:
    """Load local getRate samples; return an empty frame on first run."""

    if not path.exists():
        return pd.DataFrame(columns=RATE_HISTORY_COLUMNS)

    frame = pd.read_csv(path)

    missing = [column for column in RATE_HISTORY_COLUMNS if column not in frame.columns]
    if missing:
        raise CollectionError(
            f"Gimo rate history schema mismatch; missing columns={missing}"
        )

    frame = frame.loc[:, list(RATE_HISTORY_COLUMNS)].copy()
    frame["timestamp"] = pd.to_numeric(frame["timestamp"], errors="coerce")
    frame["block_number"] = pd.to_numeric(
        frame["block_number"], errors="coerce"
    )
    frame["rate"] = pd.to_numeric(frame["rate"], errors="coerce")

    if frame.isna().any().any():
        raise CollectionError("Gimo rate history contains invalid values")

    return frame.sort_values("timestamp").reset_index(drop=True)


def select_reference_sample(
    history: pd.DataFrame,
    current: GimoRateSample,
    *,
    lookback_seconds: int = DEFAULT_LOOKBACK_SECONDS,
    min_history_seconds: int = MIN_HISTORY_SECONDS,
) -> GimoRateSample | None:
    """Choose the local sample closest to the target trailing lookback.

    Samples younger than min_history_seconds are ignored so a sub-daily window
    is not annualized into a misleadingly volatile APY.
    """

    if history.empty:
        return None

    target = current.block_timestamp - lookback_seconds

    candidates = history[
        history["timestamp"]
        <= current.block_timestamp - min_history_seconds
    ].copy()

    if candidates.empty:
        return None

    candidates["distance_to_target"] = (
        candidates["timestamp"] - target
    ).abs()

    row = candidates.sort_values(
        ["distance_to_target", "timestamp"]
    ).iloc[0]

    return GimoRateSample(
        rate=float(row["rate"]),
        block_number=int(row["block_number"]),
        block_timestamp=int(row["timestamp"]),
    )


def append_rate_sample(
    sample: GimoRateSample,
    path: Path = DEFAULT_RATE_HISTORY_PATH,
) -> None:
    """Persist a current getRate sample without duplicating a block."""

    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_rate_history(path)

    if (
        not history.empty
        and (history["block_number"] == sample.block_number).any()
    ):
        return

    new_row = pd.DataFrame(
        [
            {
                "timestamp": sample.block_timestamp,
                "block_number": sample.block_number,
                "rate": sample.rate,
            }
        ]
    )
    combined = pd.concat([history, new_row], ignore_index=True)
    combined = combined.sort_values("timestamp")
    combined.to_csv(path, index=False)


def build_gimo_observation(
    current: GimoRateSample,
    history: pd.DataFrame,
) -> GimoRateObservation:
    """Derive trailing APY when enough local history exists."""

    reference = select_reference_sample(history, current)

    if reference is None:
        return GimoRateObservation(
            current=current,
            reference=None,
            realized_apy=None,
        )

    elapsed = current.block_timestamp - reference.block_timestamp
    apy = annualize_exchange_rate_growth(
        current.rate,
        reference.rate,
        elapsed,
    )

    return GimoRateObservation(
        current=current,
        reference=reference,
        realized_apy=apy,
    )


def build_gimo_snapshot(
    observation: GimoRateObservation,
    *,
    network: GimoNetworkObservation | None = None,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build one optimizer snapshot from the current local-history state."""

    if observation.reference is None:
        lookback_note = (
            "no >=24h local getRate history yet; current rate captured for "
            "future trailing APY calculation"
        )
    else:
        elapsed_days = (
            observation.current.block_timestamp
            - observation.reference.block_timestamp
        ) / SECONDS_PER_DAY
        lookback_note = (
            f"realized APY from local getRate history; "
            f"lookback_days={elapsed_days:.3f}; "
            f"rate_then={observation.reference.rate:.18f}; "
            f"block_then={observation.reference.block_number}"
        )

    tvl_usd = network.tvl_usd if network is not None else None
    slashing_stress_loss = (
        network.slashing_stress_loss
        if network is not None
        else None
    )
    exposure_complete = (
        tvl_usd is not None
        and slashing_stress_loss is not None
    )

    network_note = ""
    if network is not None:
        network_note = (
            f"; total_supply_st0g={network.total_supply_st0g:.18f}; "
            f"tvl_0g={network.tvl_0g:.18f}; "
            f"price_usd={network.price_usd:.8f}; "
            f"slash_stress={network.slashing_stress_loss:.4f} "
            "(MODELLED underlying-validator severe scenario; Gimo itself "
            "does not add a separate slashing mechanism)"
        )

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": None,
        "gross_apy": observation.realized_apy,
        "incentive_apy": 0.0,
        "yield_fee_status": "NET_OF_PROTOCOL_FEES",
        "tvl_usd": tvl_usd,
        # Conservative optimizer capacity proxy: current st0G-backed TVL.
        "liquidity_usd": tvl_usd,
        "volume_24h_usd": None,
        "protocol_fee_rate": DOCUMENTED_REWARD_COMMISSION,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": 0.0,
        "exit_slippage_rate": 0.0,
        "exit_time_days": DOCUMENTED_EPOCH_DAYS,
        "slashing_stress_loss": slashing_stress_loss,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": (
            "PARTIAL_MODELLED"
            if exposure_complete
            else "LIVE_INCOMPLETE"
        ),
        "source": "GIMO_ONCHAIN_GETRATE_LOCAL_HISTORY",
        "notes": (
            f"{lookback_note}; "
            f"rate_now={observation.current.rate:.18f}; "
            f"block_now={observation.current.block_number}; "
            "exchange-rate growth is net of documented reward commission; "
            "documented reward commission=10%; "
            "withdrawals aligned with 22-day epoch cycle; "
            f"st0G={ST0G_TOKEN_CONTRACT}; stake={STAKE_CONTRACT}"
            f"{network_note}"
        ),
    }


def collect_gimo_snapshot(
    *,
    history_path: Path = DEFAULT_RATE_HISTORY_PATH,
    rpc_fn: RpcFn | None = None,
) -> dict[str, object]:
    """Collect current getRate and derive APY from locally retained history."""

    history = load_rate_history(history_path)
    current = fetch_current_gimo_rate_sample(rpc_fn=rpc_fn)
    observation = build_gimo_observation(current, history)

    network = fetch_gimo_network_observation(
        current.rate,
        rpc_fn=rpc_fn,
    )

    # Persist after deriving the observation so the current point cannot be
    # selected as its own reference sample.
    append_rate_sample(current, history_path)

    return build_gimo_snapshot(
        observation,
        network=network,
    )
