"""Live collector for the Oku / Uniswap V3 0G/USDC.e route.

Oku is the interface; the underlying route is Uniswap V3 deployed on 0G. The
collector discovers W0G/USDC.e pools directly from the verified 0G Uniswap V3
factory across standard fee tiers, then uses GeckoTerminal for observable pool
liquidity and 24-hour volume.

The trailing fee APR proxy is:

    fee_apr = volume_24h_usd * pool_fee_rate * 365 / liquidity_usd

This deliberately excludes incentives, amount-dependent slippage, and
concentrated-liquidity +/-20% stress. Those unresolved fields keep the strategy
LIVE_INCOMPLETE and therefore not optimizer-eligible yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

from .common import CollectionError, fetch_json, rpc_call, utc_now_iso
from .merkl import MerklIncentiveObservation, fetch_merkl_pool_incentive


STRATEGY_ID = "OKU_LP_0G_USDC"

RPC_URL = "https://evmrpc.0g.ai"
GECKO_NETWORK = "0g"
GECKO_API_BASE = "https://api.geckoterminal.com/api/v2"

UNISWAP_V3_FACTORY = "0xcb2436774C3e191c85056d248EF4260ce5f27A9D"
OKU_SWAP_ROUTER02 = "0x807F4E281B7A3B324825C64ca53c69F0b418dE40"
W0G_TOKEN = "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c"
USDCE_TOKEN = "0x1f3AA82227281cA364bFb3d253B0f1af1Da6473E"

GET_POOL_SELECTOR = "0x1698ee82"  # getPool(address,address,uint24)
STANDARD_FEE_TIERS = (100, 500, 3000, 10000)
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

GECKO_HEADERS = {
    "Accept": "application/json;version=20230203",
}

RpcFn = Callable[[str, str, list[Any]], Any]
JsonFn = Callable[..., Any]


@dataclass(frozen=True)
class OkuPool:
    """One Uniswap V3 W0G/USDC.e pool discovered on 0G."""

    address: str
    fee_tier: int

    @property
    def fee_rate(self) -> float:
        return self.fee_tier / 1_000_000.0


@dataclass(frozen=True)
class OkuMarketObservation:
    """Current observable measurements for one pool."""

    pool: OkuPool
    name: str | None
    liquidity_usd: float | None
    volume_24h_usd: float | None

    @property
    def fee_apr(self) -> float | None:
        if (
            self.liquidity_usd is None
            or self.volume_24h_usd is None
            or self.liquidity_usd <= 0
        ):
            return None

        return (
            self.volume_24h_usd
            * self.pool.fee_rate
            * 365.0
            / self.liquidity_usd
        )


def _pad_address(address: str) -> str:
    clean = address.lower().removeprefix("0x")
    if len(clean) != 40:
        raise CollectionError(f"Invalid EVM address: {address!r}")
    return clean.zfill(64)


def _pad_uint(value: int) -> str:
    if value < 0:
        raise CollectionError("uint value must be non-negative")
    return hex(value)[2:].zfill(64)


def _decode_address(raw: str) -> str:
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise CollectionError(f"Invalid eth_call address result: {raw!r}")

    clean = raw[2:].rjust(64, "0")
    address = "0x" + clean[-40:]

    if address.lower() == ZERO_ADDRESS:
        return ZERO_ADDRESS

    return address


def get_pool_address(
    fee_tier: int,
    *,
    rpc_fn: RpcFn | None = None,
) -> str:
    """Call Uniswap V3 factory.getPool(W0G, USDC.e, fee)."""

    rpc = rpc_fn or rpc_call

    calldata = (
        GET_POOL_SELECTOR
        + _pad_address(W0G_TOKEN)
        + _pad_address(USDCE_TOKEN)
        + _pad_uint(fee_tier)
    )

    raw = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": UNISWAP_V3_FACTORY,
                "data": calldata,
            },
            "latest",
        ],
    )

    return _decode_address(raw)


def discover_oku_pools(
    *,
    rpc_fn: RpcFn | None = None,
) -> list[OkuPool]:
    """Discover standard-fee W0G/USDC.e pools from the 0G Uniswap V3 factory."""

    pools: list[OkuPool] = []

    for fee_tier in STANDARD_FEE_TIERS:
        address = get_pool_address(fee_tier, rpc_fn=rpc_fn)

        if address.lower() != ZERO_ADDRESS:
            pools.append(
                OkuPool(
                    address=address,
                    fee_tier=fee_tier,
                )
            )

    if not pools:
        raise CollectionError(
            "No Uniswap V3 W0G/USDC.e pool found on 0G across standard fee tiers"
        )

    return pools


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(converted):
        return None

    return converted


def fetch_pool_market_data(
    pool: OkuPool,
    *,
    json_fn: JsonFn | None = None,
) -> OkuMarketObservation:
    """Fetch pool reserve and 24h volume from GeckoTerminal."""

    fetcher = json_fn or fetch_json
    url = (
        f"{GECKO_API_BASE}/networks/{GECKO_NETWORK}/pools/"
        f"{pool.address}"
    )

    payload = fetcher(url, headers=GECKO_HEADERS)

    try:
        attributes = payload["data"]["attributes"]
    except (TypeError, KeyError) as exc:
        raise CollectionError(
            f"Malformed GeckoTerminal pool response for {pool.address}"
        ) from exc

    volume = attributes.get("volume_usd")
    volume_24h = volume.get("h24") if isinstance(volume, dict) else None

    return OkuMarketObservation(
        pool=pool,
        name=attributes.get("name"),
        liquidity_usd=_optional_float(attributes.get("reserve_in_usd")),
        volume_24h_usd=_optional_float(volume_24h),
    )


def select_primary_pool(
    observations: list[OkuMarketObservation],
) -> OkuMarketObservation:
    """Choose the discovered pool with greatest observable USD liquidity."""

    if not observations:
        raise CollectionError("No Oku/Uniswap V3 pool observations available")

    return max(
        observations,
        key=lambda item: (
            item.liquidity_usd
            if item.liquidity_usd is not None
            else -1.0
        ),
    )


def collect_market_observation(
    *,
    rpc_fn: RpcFn | None = None,
    json_fn: JsonFn | None = None,
) -> OkuMarketObservation:
    """Discover candidate pools and select the most liquid observable route."""

    pools = discover_oku_pools(rpc_fn=rpc_fn)
    observations: list[OkuMarketObservation] = []

    for pool in pools:
        try:
            observations.append(
                fetch_pool_market_data(
                    pool,
                    json_fn=json_fn,
                )
            )
        except CollectionError:
            continue

    if observations:
        return select_primary_pool(observations)

    # Preserve on-chain pool discovery even if secondary market-data retrieval
    # is temporarily unavailable.
    pool = pools[0]

    return OkuMarketObservation(
        pool=pool,
        name=None,
        liquidity_usd=None,
        volume_24h_usd=None,
    )


def build_oku_snapshot(
    observation: OkuMarketObservation,
    *,
    incentive: MerklIncentiveObservation | None = None,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build one live-but-incomplete Oku / Uniswap V3 strategy snapshot."""

    incentive_apy = incentive.incentive_apy if incentive is not None else None

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": observation.fee_apr,
        "gross_apy": None,
        "incentive_apy": incentive_apy,
        "yield_fee_status": "NET_OF_PROTOCOL_FEES",
        "tvl_usd": observation.liquidity_usd,
        "liquidity_usd": observation.liquidity_usd,
        "volume_24h_usd": observation.volume_24h_usd,
        "protocol_fee_rate": 0.0,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": None,
        "exit_slippage_rate": None,
        "exit_time_days": 0.0,
        "slashing_stress_loss": None,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": "LIVE_INCOMPLETE",
        "source": "UNISWAP_V3_GECKOTERMINAL_MERKL",
        "notes": (
            f"pool={observation.pool.address}; "
            f"fee_tier={observation.pool.fee_tier}; "
            f"pool_fee_rate={observation.pool.fee_rate:.6f}; "
            f"pool_name={observation.name or 'UNKNOWN'}; "
            f"factory={UNISWAP_V3_FACTORY}; "
            f"router02={OKU_SWAP_ROUTER02}; "
            "gross_apr is a trailing 24h swap-fee APR proxy when liquidity "
            "and volume are available; "
            f"merkl_campaign_apr={incentive.campaign_apr if incentive is not None else 'UNAVAILABLE'}; "
            f"merkl_campaigns={incentive.matched_campaigns if incentive is not None else 'UNAVAILABLE'}; "
            "Merkl PROTOCOL/native APR excluded to avoid double counting; "
            "amount-dependent slippage and concentrated-LP +/-20% stress remain unresolved"
        ),
    }


def collect_oku_snapshot() -> dict[str, object]:
    """Collect the current Oku / Uniswap V3 W0G/USDC.e route."""

    observation = collect_market_observation()
    try:
        incentive = fetch_merkl_pool_incentive(observation.pool.address)
    except CollectionError:
        incentive = None

    return build_oku_snapshot(observation, incentive=incentive)
