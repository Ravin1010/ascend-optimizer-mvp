"""Runtime LP execution and concentrated-liquidity stress modelling.

LP entry/exit slippage is amount-dependent, so it should not be frozen into a
collector snapshot. This module resolves slippage at optimizer runtime using the
actual user portfolio amount and live venue quoters.

MVP execution assumption for a portfolio funded in 0G:
* swap 50% of 0G value into USDC.e when entering the LP;
* on exit, swap the 50% USDC.e leg back into 0G;
* quote loss versus the current 0G USD reference is treated as execution
  slippage on the whole portfolio notional.

The LP +/-20% stress uses exact Uniswap V3 inventory formulas under a clearly
labelled modelled range: [0.8 * P0, 1.2 * P0]. The worse of a -20% and +20%
price shock is recorded as the strategy stress loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
import re
from typing import Any, Callable

from .collectors.common import CollectionError, rpc_call


RPC_URL = "https://evmrpc.0g.ai"

W0G_TOKEN = "0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c"
USDCE_TOKEN = "0x1f3AA82227281cA364bFb3d253B0f1af1Da6473E"
W0G_DECIMALS = 18
USDCE_DECIMALS = 6

JAINE_QUOTER_V1 = "0xd00883722cECAD3A1c60bCA611f09e1851a0bE02"
OKU_QUOTER_V2 = "0xaa52bB8110fE38D0d2d2AF0B85C3A3eE622CA455"

QUOTE_V1_SELECTOR = "0xf7729d43"
QUOTE_V2_SELECTOR = "0xc6a5026a"

MODELLED_RANGE_LOWER_MULTIPLIER = 0.80
MODELLED_RANGE_UPPER_MULTIPLIER = 1.20

LP_ROUTE_CONFIG = {
    "JAINE_LP_0G_USDC": {
        "quoter": JAINE_QUOTER_V1,
        "mode": "V1",
    },
    "OKU_LP_0G_USDC": {
        "quoter": OKU_QUOTER_V2,
        "mode": "V2",
    },
}

RpcFn = Callable[[str, str, list[Any]], Any]


@dataclass(frozen=True)
class LPExecutionQuote:
    """Runtime amount-dependent execution exposure for one LP strategy."""

    strategy_id: str
    fee_tier: int
    entry_slippage_rate: float
    exit_slippage_rate: float
    entry_amount_out_usdc: float
    exit_amount_out_0g: float

    @property
    def max_entry_exit_slippage(self) -> float:
        return max(self.entry_slippage_rate, self.exit_slippage_rate)


def _require_positive(name: str, value: float) -> float:
    converted = float(value)
    if not isfinite(converted) or converted <= 0:
        raise CollectionError(f"{name} must be finite and > 0")
    return converted


def _pad_address(address: str) -> str:
    clean = address.lower().removeprefix("0x")
    if len(clean) != 40:
        raise CollectionError(f"Invalid EVM address: {address!r}")
    return clean.zfill(64)


def _pad_uint(value: int) -> str:
    if value < 0:
        raise CollectionError("uint value must be non-negative")
    return hex(int(value))[2:].zfill(64)


def _decode_first_uint(raw: str) -> int:
    if not isinstance(raw, str) or not raw.startswith("0x"):
        raise CollectionError(f"Invalid quoter result: {raw!r}")

    payload = raw[2:]
    if len(payload) < 64:
        raise CollectionError(f"Quoter result too short: {raw!r}")

    try:
        return int(payload[:64], 16)
    except ValueError as exc:
        raise CollectionError(f"Invalid quoter uint result: {raw!r}") from exc


def _encode_quote_v1(
    token_in: str,
    token_out: str,
    fee_tier: int,
    amount_in: int,
) -> str:
    return (
        QUOTE_V1_SELECTOR
        + _pad_address(token_in)
        + _pad_address(token_out)
        + _pad_uint(fee_tier)
        + _pad_uint(amount_in)
        + _pad_uint(0)
    )


def _encode_quote_v2(
    token_in: str,
    token_out: str,
    fee_tier: int,
    amount_in: int,
) -> str:
    # quoteExactInputSingle((address,address,uint256,uint24,uint160))
    return (
        QUOTE_V2_SELECTOR
        + _pad_address(token_in)
        + _pad_address(token_out)
        + _pad_uint(amount_in)
        + _pad_uint(fee_tier)
        + _pad_uint(0)
    )


def quote_exact_input_single(
    *,
    quoter: str,
    mode: str,
    token_in: str,
    token_out: str,
    fee_tier: int,
    amount_in: int,
    rpc_fn: RpcFn | None = None,
) -> int:
    """Quote one V3-style exact-input swap through the venue quoter."""

    if amount_in <= 0:
        raise CollectionError("amount_in must be > 0")

    if mode == "V1":
        calldata = _encode_quote_v1(
            token_in,
            token_out,
            fee_tier,
            amount_in,
        )
    elif mode == "V2":
        calldata = _encode_quote_v2(
            token_in,
            token_out,
            fee_tier,
            amount_in,
        )
    else:
        raise CollectionError(f"Unsupported quoter mode: {mode!r}")

    rpc = rpc_fn or rpc_call
    raw = rpc(
        RPC_URL,
        "eth_call",
        [
            {
                "to": quoter,
                "data": calldata,
            },
            "latest",
        ],
    )

    amount_out = _decode_first_uint(raw)
    if amount_out <= 0:
        raise CollectionError("Quoter returned a non-positive amountOut")

    return amount_out


def extract_fee_tier(snapshot: Any) -> int:
    """Extract the selected live pool fee tier from snapshot provenance."""

    notes = str(snapshot.get("notes") or "")
    match = re.search(r"(?:^|;\s*)fee_tier=(\d+)", notes)

    if not match:
        raise CollectionError(
            "LP snapshot does not contain a selected fee_tier in notes"
        )

    fee_tier = int(match.group(1))
    if fee_tier <= 0:
        raise CollectionError("fee_tier must be > 0")

    return fee_tier


def estimate_lp_execution_slippage(
    *,
    strategy_id: str,
    snapshot: Any,
    amount_0g: float,
    asset_price_usd: float,
    rpc_fn: RpcFn | None = None,
) -> LPExecutionQuote:
    """Estimate entry/exit slippage for the actual user portfolio amount."""

    amount_0g = _require_positive("amount_0g", amount_0g)
    asset_price_usd = _require_positive(
        "asset_price_usd",
        asset_price_usd,
    )

    config = LP_ROUTE_CONFIG.get(strategy_id)
    if config is None:
        raise CollectionError(
            f"No LP execution route configured for {strategy_id}"
        )

    fee_tier = extract_fee_tier(snapshot)

    portfolio_value_usd = amount_0g * asset_price_usd
    half_amount_0g = amount_0g / 2.0
    half_value_usd = portfolio_value_usd / 2.0

    entry_amount_in = int(half_amount_0g * 10**W0G_DECIMALS)
    entry_out_raw = quote_exact_input_single(
        quoter=str(config["quoter"]),
        mode=str(config["mode"]),
        token_in=W0G_TOKEN,
        token_out=USDCE_TOKEN,
        fee_tier=fee_tier,
        amount_in=entry_amount_in,
        rpc_fn=rpc_fn,
    )
    entry_out_usdc = entry_out_raw / 10**USDCE_DECIMALS
    entry_loss_usd = max(0.0, half_value_usd - entry_out_usdc)
    entry_slippage_rate = entry_loss_usd / portfolio_value_usd

    # First-order exit assumption: half the position is in USDC.e by value.
    # USDC.e is treated as $1 for this execution proxy.
    exit_amount_in = int(half_value_usd * 10**USDCE_DECIMALS)
    exit_out_raw = quote_exact_input_single(
        quoter=str(config["quoter"]),
        mode=str(config["mode"]),
        token_in=USDCE_TOKEN,
        token_out=W0G_TOKEN,
        fee_tier=fee_tier,
        amount_in=exit_amount_in,
        rpc_fn=rpc_fn,
    )
    exit_out_0g = exit_out_raw / 10**W0G_DECIMALS
    exit_value_usd = exit_out_0g * asset_price_usd
    exit_loss_usd = max(0.0, half_value_usd - exit_value_usd)
    exit_slippage_rate = exit_loss_usd / portfolio_value_usd

    return LPExecutionQuote(
        strategy_id=strategy_id,
        fee_tier=fee_tier,
        entry_slippage_rate=entry_slippage_rate,
        exit_slippage_rate=exit_slippage_rate,
        entry_amount_out_usdc=entry_out_usdc,
        exit_amount_out_0g=exit_out_0g,
    )


def _v3_inventory(
    price: float,
    lower: float,
    upper: float,
) -> tuple[float, float]:
    """Return token0/token1 inventory for unit liquidity."""

    sqrt_lower = sqrt(lower)
    sqrt_upper = sqrt(upper)

    if price <= lower:
        return (
            1.0 / sqrt_lower - 1.0 / sqrt_upper,
            0.0,
        )

    if price >= upper:
        return (
            0.0,
            sqrt_upper - sqrt_lower,
        )

    sqrt_price = sqrt(price)
    return (
        1.0 / sqrt_price - 1.0 / sqrt_upper,
        sqrt_price - sqrt_lower,
    )


def concentrated_lp_stress_loss(
    *,
    lower_multiplier: float = MODELLED_RANGE_LOWER_MULTIPLIER,
    upper_multiplier: float = MODELLED_RANGE_UPPER_MULTIPLIER,
    shocks: tuple[float, ...] = (0.80, 1.20),
) -> float:
    """Return worst IL versus HODL under the supplied relative price shocks."""

    lower = _require_positive("lower_multiplier", lower_multiplier)
    upper = _require_positive("upper_multiplier", upper_multiplier)

    if not lower < 1.0 < upper:
        raise CollectionError(
            "Modelled LP range must satisfy lower < 1 < upper"
        )

    initial_x, initial_y = _v3_inventory(1.0, lower, upper)
    worst_loss = 0.0

    for shock in shocks:
        price = _require_positive("shock", shock)
        lp_x, lp_y = _v3_inventory(price, lower, upper)

        lp_value = lp_x * price + lp_y
        hodl_value = initial_x * price + initial_y

        if hodl_value <= 0:
            raise CollectionError("Invalid HODL benchmark value")

        relative = lp_value / hodl_value - 1.0
        worst_loss = max(worst_loss, max(0.0, -relative))

    return worst_loss


MODELLED_LP_STRESS_20PCT = concentrated_lp_stress_loss()
