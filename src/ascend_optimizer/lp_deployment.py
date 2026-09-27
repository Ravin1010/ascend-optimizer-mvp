"""Pre-deployment planning for 0G W0G/USDC.e V3 LP adapters.

Discovers the live primary pool at run time, reads slot0/tickSpacing/token
ordering, constructs the capstone's +/-20% modelled range, aligns it to valid
ticks, and emits exact Uniswap V3 sqrt ratios plus constructor parameters.

The MVP's 50/50 entry split is retained as a first-order approximation; this
tool reports the range-implied target USDC value share and its deviation from
50% so the assumption is explicit before deployment.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from math import ceil, floor, isfinite, log
from typing import Any, Callable

from .collectors.common import CollectionError, rpc_call
from .collectors.jaine import (
    W0G_TOKEN,
    USDCE_TOKEN,
    collect_market_observation as collect_jaine_market,
)
from .collectors.oku import collect_market_observation as collect_oku_market


RPC_URL = "https://evmrpc.0g.ai"
SLOT0_SELECTOR = "0x3850c7bd"
TICK_SPACING_SELECTOR = "0xd0c93a7c"
TOKEN0_SELECTOR = "0x0dfe1681"
TOKEN1_SELECTOR = "0xd21220a7"

MIN_TICK = -887272
MAX_TICK = 887272
Q96 = 1 << 96
Q192 = 1 << 192

LOWER_MULTIPLIER = 0.80
UPPER_MULTIPLIER = 1.20

RpcFn = Callable[[str, str, list[Any]], Any]


@dataclass(frozen=True)
class PoolState:
    pool: str
    token0: str
    token1: str
    sqrt_price_x96: int
    tick: int
    tick_spacing: int


@dataclass(frozen=True)
class LPDeploymentPlan:
    venue: str
    pool: str
    fee_tier: int
    liquidity_usd: float | None
    current_tick: int
    tick_spacing: int
    tick_lower: int
    tick_upper: int
    sqrt_lower_x96: int
    sqrt_upper_x96: int
    token0: str
    token1: str
    target_usdc_value_fraction: float
    fifty_fifty_deviation_bps: float
    target_usdc_bps: int

    def constructor_args(self) -> tuple[object, ...]:
        return (
            self.pool,
            self.fee_tier,
            self.tick_lower,
            self.tick_upper,
            self.sqrt_lower_x96,
            self.sqrt_upper_x96,
            self.target_usdc_bps,
        )


def _call(rpc: RpcFn, to: str, data: str) -> str:
    return rpc(
        RPC_URL,
        "eth_call",
        [{"to": to, "data": data}, "latest"],
    )


def _decode_uint(raw: str, field: str) -> int:
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise CollectionError(f"Invalid {field} result: {raw!r}")
    try:
        return int(raw, 16)
    except ValueError as exc:
        raise CollectionError(f"Invalid {field} result: {raw!r}") from exc


def _decode_signed_word(raw: str, field: str) -> int:
    value = _decode_uint(raw, field)
    if value >= 1 << 255:
        value -= 1 << 256
    return value


def _decode_address(raw: str, field: str) -> str:
    value = _decode_uint(raw, field)
    return "0x" + f"{value & ((1 << 160) - 1):040x}"


def fetch_pool_state(
    pool: str,
    *,
    rpc_fn: RpcFn | None = None,
) -> PoolState:
    rpc = rpc_fn or rpc_call

    slot0_raw = _call(rpc, pool, SLOT0_SELECTOR)
    payload = slot0_raw.removeprefix("0x")
    if len(payload) < 128:
        raise CollectionError(f"slot0 result too short for {pool}")

    sqrt_price_x96 = int(payload[:64], 16)
    tick_word = int(payload[64:128], 16)
    if tick_word >= 1 << 255:
        tick_word -= 1 << 256

    spacing = _decode_signed_word(
        _call(rpc, pool, TICK_SPACING_SELECTOR),
        "tickSpacing",
    )
    token0 = _decode_address(
        _call(rpc, pool, TOKEN0_SELECTOR),
        "token0",
    )
    token1 = _decode_address(
        _call(rpc, pool, TOKEN1_SELECTOR),
        "token1",
    )

    if sqrt_price_x96 <= 0:
        raise CollectionError("pool sqrtPriceX96 must be > 0")
    if spacing <= 0:
        raise CollectionError("pool tickSpacing must be > 0")
    if not MIN_TICK <= tick_word <= MAX_TICK:
        raise CollectionError(f"pool tick outside V3 bounds: {tick_word}")

    pair = {token0.lower(), token1.lower()}
    expected = {W0G_TOKEN.lower(), USDCE_TOKEN.lower()}
    if pair != expected:
        raise CollectionError(
            f"unexpected pool token pair: token0={token0}, token1={token1}"
        )

    return PoolState(
        pool=pool,
        token0=token0,
        token1=token1,
        sqrt_price_x96=sqrt_price_x96,
        tick=tick_word,
        tick_spacing=spacing,
    )


def get_sqrt_ratio_at_tick(tick: int) -> int:
    """Exact integer port of Uniswap V3 TickMath.getSqrtRatioAtTick."""

    if tick < MIN_TICK or tick > MAX_TICK:
        raise ValueError(f"tick outside V3 bounds: {tick}")

    abs_tick = -tick if tick < 0 else tick
    ratio = (
        0xFFFcb933BD6FAD37AA2D162D1A594001
        if abs_tick & 0x1
        else 0x100000000000000000000000000000000
    )

    constants = (
        (0x2, 0xFFF97272373D413259A46990580E213A),
        (0x4, 0xFFF2E50F5F656932EF12357CF3C7FDCC),
        (0x8, 0xFFE5CACA7E10E4E61C3624EAA0941CD0),
        (0x10, 0xFFCB9843D60F6159C9DB58835C926644),
        (0x20, 0xFF973B41FA98C081472E6896DFB254C0),
        (0x40, 0xFF2EA16466C96A3843EC78B326B52861),
        (0x80, 0xFE5DEE046A99A2A811C461F1969C3053),
        (0x100, 0xFCBE86C7900A88AEDCFFC83B479AA3A4),
        (0x200, 0xF987A7253AC413176F2B074CF7815E54),
        (0x400, 0xF3392B0822B70005940C7A398E4B70F3),
        (0x800, 0xE7159475A2C29B7443B29C7FA6E889D9),
        (0x1000, 0xD097F3BDFD2022B8845AD8F792AA5825),
        (0x2000, 0xA9F746462D870FDF8A65DC1F90E061E5),
        (0x4000, 0x70D869A156D2A1B890BB3DF62BAF32F7),
        (0x8000, 0x31BE135F97D08FD981231505542FCFA6),
        (0x10000, 0x9AA508B5B7A84E1C677DE54F3E99BC9),
        (0x20000, 0x5D6AF8DEDB81196699C329225EE604),
        (0x40000, 0x2216E584F5FA1EA926041BEDFE98),
        (0x80000, 0x48A170391F7DC42444E8FA2),
    )

    for mask, multiplier in constants:
        if abs_tick & mask:
            ratio = (ratio * multiplier) >> 128

    if tick > 0:
        ratio = ((1 << 256) - 1) // ratio

    remainder_mask = (1 << 32) - 1
    return (ratio >> 32) + (1 if ratio & remainder_mask else 0)


def derive_aligned_range(
    current_tick: int,
    tick_spacing: int,
    *,
    lower_multiplier: float = LOWER_MULTIPLIER,
    upper_multiplier: float = UPPER_MULTIPLIER,
) -> tuple[int, int]:
    if tick_spacing <= 0:
        raise ValueError("tick_spacing must be > 0")
    if (
        not isfinite(lower_multiplier)
        or not isfinite(upper_multiplier)
        or not 0 < lower_multiplier < 1 < upper_multiplier
    ):
        raise ValueError("range multipliers must satisfy 0 < lower < 1 < upper")

    log_base = log(1.0001)
    lower_delta = floor(log(lower_multiplier) / log_base)
    upper_delta = ceil(log(upper_multiplier) / log_base)

    raw_lower = current_tick + lower_delta
    raw_upper = current_tick + upper_delta

    tick_lower = (raw_lower // tick_spacing) * tick_spacing
    tick_upper = -((-raw_upper) // tick_spacing) * tick_spacing

    min_aligned = -((-MIN_TICK) // tick_spacing) * tick_spacing
    max_aligned = (MAX_TICK // tick_spacing) * tick_spacing
    tick_lower = max(min_aligned, tick_lower)
    tick_upper = min(max_aligned, tick_upper)

    if tick_lower >= tick_upper:
        raise ValueError("aligned range is empty")

    return tick_lower, tick_upper


def _amounts_for_unit_liquidity(
    sqrt_price_x96: int,
    sqrt_lower_x96: int,
    sqrt_upper_x96: int,
) -> tuple[float, float]:
    p = sqrt_price_x96 / Q96
    lower = sqrt_lower_x96 / Q96
    upper = sqrt_upper_x96 / Q96

    if p <= lower:
        return (1.0 / lower - 1.0 / upper, 0.0)
    if p >= upper:
        return (0.0, upper - lower)
    return (1.0 / p - 1.0 / upper, p - lower)


def target_usdc_value_fraction(
    state: PoolState,
    *,
    tick_lower: int,
    tick_upper: int,
) -> float:
    sqrt_lower = get_sqrt_ratio_at_tick(tick_lower)
    sqrt_upper = get_sqrt_ratio_at_tick(tick_upper)
    amount0, amount1 = _amounts_for_unit_liquidity(
        state.sqrt_price_x96,
        sqrt_lower,
        sqrt_upper,
    )

    raw_price_1_per_0 = (
        state.sqrt_price_x96 * state.sqrt_price_x96 / Q192
    )
    token0_value_in_token1 = amount0 * raw_price_1_per_0
    total_value_token1 = token0_value_in_token1 + amount1
    if total_value_token1 <= 0:
        raise CollectionError("range has zero value at current pool price")

    if state.token1.lower() == USDCE_TOKEN.lower():
        usdc_value = amount1
    else:
        usdc_value = token0_value_in_token1

    return usdc_value / total_value_token1


def build_plan(
    venue: str,
    *,
    rpc_fn: RpcFn | None = None,
) -> LPDeploymentPlan:
    normalized = venue.strip().lower()
    if normalized == "jaine":
        observation = collect_jaine_market(rpc_fn=rpc_fn)
    elif normalized == "oku":
        observation = collect_oku_market(rpc_fn=rpc_fn)
    else:
        raise ValueError("venue must be 'jaine' or 'oku'")

    state = fetch_pool_state(
        observation.pool.address,
        rpc_fn=rpc_fn,
    )
    tick_lower, tick_upper = derive_aligned_range(
        state.tick,
        state.tick_spacing,
    )
    sqrt_lower = get_sqrt_ratio_at_tick(tick_lower)
    sqrt_upper = get_sqrt_ratio_at_tick(tick_upper)

    usdc_fraction = target_usdc_value_fraction(
        state,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
    )

    return LPDeploymentPlan(
        venue=normalized.upper(),
        pool=observation.pool.address,
        fee_tier=observation.pool.fee_tier,
        liquidity_usd=observation.liquidity_usd,
        current_tick=state.tick,
        tick_spacing=state.tick_spacing,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        sqrt_lower_x96=sqrt_lower,
        sqrt_upper_x96=sqrt_upper,
        token0=state.token0,
        token1=state.token1,
        target_usdc_value_fraction=usdc_fraction,
        fifty_fifty_deviation_bps=abs(usdc_fraction - 0.5) * 10_000,
        target_usdc_bps=round(usdc_fraction * 10_000),
    )


def print_plan(plan: LPDeploymentPlan) -> None:
    print(f"{plan.venue} W0G/USDC.e deployment preflight")
    print(f"pool: {plan.pool}")
    print(f"fee_tier: {plan.fee_tier}")
    print(f"liquidity_usd: {plan.liquidity_usd}")
    print(f"token0: {plan.token0}")
    print(f"token1: {plan.token1}")
    print(f"current_tick: {plan.current_tick}")
    print(f"tick_spacing: {plan.tick_spacing}")
    print(f"tick_lower: {plan.tick_lower}")
    print(f"tick_upper: {plan.tick_upper}")
    print(f"sqrt_lower_x96: {plan.sqrt_lower_x96}")
    print(f"sqrt_upper_x96: {plan.sqrt_upper_x96}")
    print(
        "target_usdc_value_fraction: "
        f"{plan.target_usdc_value_fraction:.6f}"
    )
    print(
        "50_50_deviation_bps: "
        f"{plan.fifty_fifty_deviation_bps:.2f}"
    )
    print(f"target_usdc_bps: {plan.target_usdc_bps}")
    print("constructor_args_without_vault:")
    print(
        f"  {plan.pool} {plan.fee_tier} "
        f"{plan.tick_lower} {plan.tick_upper} "
        f"{plan.sqrt_lower_x96} {plan.sqrt_upper_x96} "
        f"{plan.target_usdc_bps}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate live V3 LP adapter deployment parameters."
    )
    parser.add_argument(
        "--venue",
        required=True,
        choices=("jaine", "oku"),
    )
    args = parser.parse_args()
    print_plan(build_plan(args.venue))


if __name__ == "__main__":
    main()
