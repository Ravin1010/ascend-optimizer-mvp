"""Live collector for the Jaine 0G/USDC.e concentrated-liquidity route.

Jaine is a Uniswap-V3-style CLMM on 0G. The collector discovers W0G/USDC.e
pools directly from the Jaine factory across standard V3 fee tiers, then uses
GeckoTerminal's public pool endpoint for current USD liquidity and 24-hour
volume.

The trailing fee APR is an observable proxy:

    fee_apr = volume_24h_usd * pool_fee_rate * 365 / liquidity_usd

It excludes Merkl incentives and does not model concentrated-liquidity range
utilisation, slippage, or impermanent-loss stress yet. Those missing values keep
this strategy LIVE_INCOMPLETE and prevent premature optimizer eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable

from .common import CollectionError, fetch_json, rpc_call, utc_now_iso


STRATEGY_ID = "JAINE_LP_0G_USDC"

RPC_URL = "https://evmrpc.0g.ai"
GECKO_NETWORK = "0g"
GECKO_API_BASE = "https://api.geckoterminal.com/api/v2"

JAINE_FACTORY = "0x9bdcA5798E52e592A08e3b34d3F18EeF76Af7ef4"
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
class JainePool:
    """One Jaine W0G/USDC.e pool discovered from the V3 factory."""

    address: str
    fee_tier: int

    @property
    def fee_rate(self) -> float:
        return self.fee_tier / 1_000_000.0


@dataclass(frozen=True)
class JaineMarketObservation:
    """Pool-level market measurements from GeckoTerminal."""

    pool: JainePool
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
    """Call Jaine factory.getPool(W0G, USDC.e, fee)."""

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
                "to": JAINE_FACTORY,
                "data": calldata,
            },
            "latest",
        ],
    )
    return _decode_address(raw)


def discover_jaine_pools(
    *,
    rpc_fn: RpcFn | None = None,
) -> list[JainePool]:
    """Discover all standard-fee W0G/USDC.e pools on the Jaine factory."""

    pools: list[JainePool] = []

    for fee_tier in STANDARD_FEE_TIERS:
        address = get_pool_address(fee_tier, rpc_fn=rpc_fn)
        if address.lower() != ZERO_ADDRESS:
            pools.append(
                JainePool(
                    address=address,
                    fee_tier=fee_tier,
                )
            )

    if not pools:
        raise CollectionError(
            "No Jaine W0G/USDC.e pool found across standard V3 fee tiers"
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
    pool: JainePool,
    *,
    json_fn: JsonFn | None = None,
) -> JaineMarketObservation:
    """Fetch current pool reserve and volume from GeckoTerminal."""

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

    return JaineMarketObservation(
        pool=pool,
        name=attributes.get("name"),
        liquidity_usd=_optional_float(attributes.get("reserve_in_usd")),
        volume_24h_usd=_optional_float(volume_24h),
    )


def select_primary_pool(
    observations: list[JaineMarketObservation],
) -> JaineMarketObservation:
    """Select the discovered pool with the greatest observed USD liquidity."""

    if not observations:
        raise CollectionError("No Jaine pool observations available")

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
) -> JaineMarketObservation:
    """Discover Jaine pools and choose the most liquid observable pool."""

    pools = discover_jaine_pools(rpc_fn=rpc_fn)
    observations: list[JaineMarketObservation] = []
    errors: list[str] = []

    for pool in pools:
        try:
            observations.append(
                fetch_pool_market_data(pool, json_fn=json_fn)
            )
        except CollectionError as exc:
            errors.append(f"{pool.address}:{exc}")

    if observations:
        return select_primary_pool(observations)

    # Pool discovery is still useful even if the secondary market-data API is
    # temporarily unavailable. Preserve the first on-chain-discovered route.
    pool = pools[0]
    return JaineMarketObservation(
        pool=pool,
        name=None,
        liquidity_usd=None,
        volume_24h_usd=None,
    )


def build_jaine_snapshot(
    observation: JaineMarketObservation,
    *,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build one incomplete-but-live Jaine strategy snapshot."""

    fee_apr = observation.fee_apr

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": fee_apr,
        "gross_apy": None,
        # Merkl incentive APY is deliberately not guessed.
        "incentive_apy": None,
        "yield_fee_status": "NET_OF_PROTOCOL_FEES",
        "tvl_usd": observation.liquidity_usd,
        "liquidity_usd": observation.liquidity_usd,
        "volume_24h_usd": observation.volume_24h_usd,
        "protocol_fee_rate": 0.0,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        # Slippage depends on user notional and pool state; model separately.
        "entry_slippage_rate": None,
        "exit_slippage_rate": None,
        "exit_time_days": 0.0,
        "slashing_stress_loss": None,
        "bridge_fraction": 0.0,
        # Concentrated-liquidity IL depends on selected range; model separately.
        "lp_stress_loss_20pct": None,
        "data_status": "LIVE_INCOMPLETE",
        "source": "JAINE_FACTORY_AND_GECKOTERMINAL",
        "notes": (
            f"pool={observation.pool.address}; "
            f"fee_tier={observation.pool.fee_tier}; "
            f"pool_fee_rate={observation.pool.fee_rate:.6f}; "
            f"pool_name={observation.name or 'UNKNOWN'}; "
            "gross_apr is a trailing 24h swap-fee APR proxy when liquidity "
            "and volume are available; Merkl incentives excluded; "
            "slippage and concentrated-LP +/-20% stress remain unresolved"
        ),
    }


def collect_jaine_snapshot() -> dict[str, object]:
    """Collect current Jaine W0G/USDC.e pool measurements."""

    return build_jaine_snapshot(collect_market_observation())
