"""Live collector for Ascend a0G SourceCore on 0G mainnet.

Ascend a0G is a yield-bearing SourceCore share. The collector samples the
current a0G exchange rate from totalAssets()/totalSupply(), reads Mellow
withdrawal-queue timing, and stores local exchange-rate history. A trailing APY
is derived only after at least 24 hours of local observations.

The live a0G architecture bridges backing toward the target restaking layer.
Until the exact live bridged fraction and an appropriate underlying
restaking/slashing stress are measured, those exposure fields remain blank.
That deliberately keeps ASCEND_STAKE_A0G optimizer-ineligible even when a
trailing APY becomes available.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .common import CollectionError, rpc_call, utc_now_iso
from .native_staking import fetch_0g_price_usd


STRATEGY_ID = "ASCEND_STAKE_A0G"

RPC_URL = "https://evmrpc.0g.ai"
SOURCE_CORE = "0x4B3c2f55fa67679b382c979A082Df1B32079B4cB"
W0G = "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c"

RATE_SCALE = 10**18
SECONDS_PER_DAY = 86_400
SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY
MIN_HISTORY_SECONDS = SECONDS_PER_DAY
DEFAULT_LOOKBACK_SECONDS = 7 * SECONDS_PER_DAY

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RATE_HISTORY_PATH = PROJECT_ROOT / "data" / "ascend_a0g_rate_history.csv"
RATE_HISTORY_COLUMNS = ("timestamp", "block_number", "rate")

RpcFn = Callable[[str, str, list[Any]], Any]


@dataclass(frozen=True)
class AscendRateSample:
    rate: float
    total_assets_0g: float
    total_supply_a0g: float
    block_number: int
    block_timestamp: int


@dataclass(frozen=True)
class AscendQueueObservation:
    queue_address: str
    epoch_duration_seconds: int
    withdrawal_delay_seconds: int

    @property
    def max_exit_time_days(self) -> float:
        return (
            self.epoch_duration_seconds
            + self.withdrawal_delay_seconds
        ) / SECONDS_PER_DAY


def _hex_to_int(value: str, field: str) -> int:
    try:
        return int(value, 16)
    except (TypeError, ValueError) as exc:
        raise CollectionError(
            f"Invalid hexadecimal {field}: {value!r}"
        ) from exc


def _selector(rpc: RpcFn, signature: str) -> str:
    raw = "0x" + signature.encode("utf-8").hex()
    digest = rpc(RPC_URL, "web3_sha3", [raw])
    if not isinstance(digest, str) or not digest.startswith("0x"):
        raise CollectionError(
            f"Invalid web3_sha3 response for {signature}: {digest!r}"
        )
    return digest[:10]


def _eth_call_uint(
    rpc: RpcFn,
    target: str,
    signature: str,
) -> int:
    raw = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": target,
                "data": _selector(rpc, signature),
            },
            "latest",
        ],
    )
    return _hex_to_int(raw, signature)


def _eth_call_address(
    rpc: RpcFn,
    target: str,
    signature: str,
) -> str:
    raw = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": target,
                "data": _selector(rpc, signature),
            },
            "latest",
        ],
    )
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise CollectionError(
            f"Invalid address result for {signature}: {raw!r}"
        )
    clean = raw[2:].rjust(64, "0")
    return "0x" + clean[-40:]


def _block_timestamp(
    rpc: RpcFn,
    block_number: int,
) -> int:
    block = rpc(
        RPC_URL,
        "eth_getBlockByNumber",
        [hex(block_number), False],
    )
    if not isinstance(block, dict):
        raise CollectionError(
            f"Missing block data for block {block_number}"
        )
    return _hex_to_int(
        block.get("timestamp"),
        "block timestamp",
    )


def fetch_current_ascend_sample(
    *,
    rpc_fn: RpcFn | None = None,
) -> AscendRateSample:
    rpc = rpc_fn or rpc_call

    latest = _hex_to_int(
        rpc(RPC_URL, "eth_blockNumber", []),
        "latest block",
    )
    timestamp = _block_timestamp(rpc, latest)

    total_assets = _eth_call_uint(
        rpc,
        SOURCE_CORE,
        "totalAssets()",
    )
    total_supply = _eth_call_uint(
        rpc,
        SOURCE_CORE,
        "totalSupply()",
    )

    if total_supply <= 0:
        raise CollectionError(
            "Ascend a0G totalSupply is zero; cannot derive exchange rate"
        )

    rate = total_assets / total_supply
    if not isfinite(rate) or rate <= 0:
        raise CollectionError(
            f"Invalid Ascend a0G exchange rate: {rate!r}"
        )

    return AscendRateSample(
        rate=rate,
        total_assets_0g=total_assets / RATE_SCALE,
        total_supply_a0g=total_supply / RATE_SCALE,
        block_number=latest,
        block_timestamp=timestamp,
    )


def fetch_ascend_queue_observation(
    *,
    rpc_fn: RpcFn | None = None,
) -> AscendQueueObservation:
    rpc = rpc_fn or rpc_call

    queue = _eth_call_address(
        rpc,
        SOURCE_CORE,
        "withdrawalQueue()",
    )

    epoch_duration = _eth_call_uint(
        rpc,
        queue,
        "epochDuration()",
    )
    withdrawal_delay = _eth_call_uint(
        rpc,
        queue,
        "withdrawalDelay()",
    )

    if epoch_duration <= 0:
        raise CollectionError(
            "Ascend withdrawal epochDuration must be > 0"
        )

    return AscendQueueObservation(
        queue_address=queue,
        epoch_duration_seconds=epoch_duration,
        withdrawal_delay_seconds=withdrawal_delay,
    )


def load_rate_history(
    path: Path = DEFAULT_RATE_HISTORY_PATH,
) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(
            columns=RATE_HISTORY_COLUMNS
        )

    frame = pd.read_csv(path)
    missing = [
        column
        for column in RATE_HISTORY_COLUMNS
        if column not in frame.columns
    ]
    if missing:
        raise CollectionError(
            "Ascend a0G rate history schema mismatch; "
            f"missing columns={missing}"
        )

    frame = frame.loc[
        :,
        list(RATE_HISTORY_COLUMNS),
    ].copy()

    for column in RATE_HISTORY_COLUMNS:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    if frame.isna().any().any():
        raise CollectionError(
            "Ascend a0G rate history contains invalid values"
        )

    return frame.sort_values(
        "timestamp"
    ).reset_index(drop=True)


def append_rate_sample(
    sample: AscendRateSample,
    path: Path = DEFAULT_RATE_HISTORY_PATH,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    history = load_rate_history(path)
    if (
        not history.empty
        and (
            history["block_number"]
            == sample.block_number
        ).any()
    ):
        return

    row = pd.DataFrame(
        [
            {
                "timestamp": sample.block_timestamp,
                "block_number": sample.block_number,
                "rate": sample.rate,
            }
        ]
    )

    pd.concat(
        [history, row],
        ignore_index=True,
    ).sort_values(
        "timestamp"
    ).to_csv(
        path,
        index=False,
    )


def _reference_rate(
    history: pd.DataFrame,
    sample: AscendRateSample,
) -> tuple[float, int] | None:
    if history.empty:
        return None

    candidates = history[
        history["timestamp"]
        <= sample.block_timestamp
        - MIN_HISTORY_SECONDS
    ].copy()

    if candidates.empty:
        return None

    target = (
        sample.block_timestamp
        - DEFAULT_LOOKBACK_SECONDS
    )
    candidates["distance"] = (
        candidates["timestamp"] - target
    ).abs()

    row = candidates.sort_values(
        ["distance", "timestamp"]
    ).iloc[0]

    return (
        float(row["rate"]),
        int(row["timestamp"]),
    )


def _annualize_rate_growth(
    current: float,
    previous: float,
    elapsed_seconds: int,
) -> float:
    if (
        current <= 0
        or previous <= 0
        or elapsed_seconds <= 0
    ):
        raise CollectionError(
            "Invalid a0G rate-history inputs"
        )

    if current < previous:
        raise CollectionError(
            "a0G exchange rate decreased over the observation window"
        )

    return (
        (current / previous)
        ** (SECONDS_PER_YEAR / elapsed_seconds)
        - 1.0
    )


def build_ascend_snapshot(
    sample: AscendRateSample,
    queue: AscendQueueObservation,
    *,
    history: pd.DataFrame,
    price_usd: float,
    timestamp: str | None = None,
) -> dict[str, object]:
    price_usd = float(price_usd)
    if not isfinite(price_usd) or price_usd <= 0:
        raise CollectionError(
            "0G USD price must be finite and > 0"
        )

    reference = _reference_rate(
        history,
        sample,
    )

    gross_apy = None
    history_note = (
        "no >=24h local a0G exchange-rate history yet"
    )

    if reference is not None:
        previous_rate, previous_timestamp = reference
        elapsed = (
            sample.block_timestamp
            - previous_timestamp
        )
        gross_apy = _annualize_rate_growth(
            sample.rate,
            previous_rate,
            elapsed,
        )
        history_note = (
            "realized APY from local a0G exchange-rate history; "
            f"lookback_days={elapsed / SECONDS_PER_DAY:.3f}; "
            f"rate_then={previous_rate:.18f}"
        )

    tvl_usd = (
        sample.total_assets_0g
        * price_usd
    )

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": None,
        "gross_apy": gross_apy,
        "incentive_apy": 0.0,
        "yield_fee_status": "NET_OF_PROTOCOL_FEES",
        "tvl_usd": tvl_usd,
        "liquidity_usd": tvl_usd,
        "volume_24h_usd": None,
        "protocol_fee_rate": None,
        "gas_cost_usd": None,
        "bridge_cost_usd": None,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": 0.0,
        "exit_slippage_rate": 0.0,
        "exit_time_days": queue.max_exit_time_days,
        # Underlying target restaking/slashing configuration is not yet
        # measured defensibly for the live a0G route.
        "slashing_stress_loss": None,
        # The architecture uses an OFT bridge, but the fraction of backing
        # currently exposed to the target chain is dynamic and not guessed.
        "bridge_fraction": None,
        "lp_stress_loss_20pct": None,
        "data_status": "LIVE_INCOMPLETE",
        "source": "ASCEND_SOURCECORE_0G_RPC_LOCAL_RATE_HISTORY",
        "notes": (
            f"{history_note}; "
            f"rate_now={sample.rate:.18f}; "
            f"total_assets_0g={sample.total_assets_0g:.18f}; "
            f"total_supply_a0g={sample.total_supply_a0g:.18f}; "
            f"price_usd={price_usd:.8f}; "
            f"withdrawal_queue={queue.queue_address}; "
            f"epoch_duration_seconds={queue.epoch_duration_seconds}; "
            f"withdrawal_delay_seconds={queue.withdrawal_delay_seconds}; "
            "max exit time conservatively equals epoch duration + "
            "withdrawal delay; bridge fraction and underlying restaking "
            "slashing stress intentionally unresolved"
        ),
    }


def collect_ascend_snapshot(
    *,
    history_path: Path = DEFAULT_RATE_HISTORY_PATH,
    rpc_fn: RpcFn | None = None,
    price_fn: Callable[[], float] = fetch_0g_price_usd,
) -> dict[str, object]:
    history = load_rate_history(
        history_path
    )

    sample = fetch_current_ascend_sample(
        rpc_fn=rpc_fn
    )
    queue = fetch_ascend_queue_observation(
        rpc_fn=rpc_fn
    )
    price = price_fn()

    snapshot = build_ascend_snapshot(
        sample,
        queue,
        history=history,
        price_usd=price,
    )

    append_rate_sample(
        sample,
        history_path,
    )

    return snapshot
