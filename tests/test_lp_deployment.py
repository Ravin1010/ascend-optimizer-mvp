"""Tests for live V3 deployment planning."""

import pytest

from src.ascend_optimizer.lp_deployment import (
    Q96,
    PoolState,
    derive_aligned_range,
    get_sqrt_ratio_at_tick,
    target_usdc_value_fraction,
)
from src.ascend_optimizer.collectors.jaine import W0G_TOKEN, USDCE_TOKEN


def test_tickmath_known_values() -> None:
    assert get_sqrt_ratio_at_tick(0) == Q96
    assert get_sqrt_ratio_at_tick(1) == 79232123823359799118286999568
    assert get_sqrt_ratio_at_tick(-1) == 79224201403219477170569942574


def test_modelled_range_is_aligned_to_tick_spacing() -> None:
    lower, upper = derive_aligned_range(
        current_tick=0,
        tick_spacing=60,
    )

    assert lower == -2280
    assert upper == 1860
    assert lower % 60 == 0
    assert upper % 60 == 0
    assert lower < 0 < upper


def test_range_target_handles_18_vs_6_decimal_raw_price() -> None:
    # At a human 1 USDC per 1 W0G price, raw token1/token0 is 1e6 / 1e18
    # when token0=W0G and token1=USDC.e. V3 sqrtPriceX96 therefore carries
    # the decimal-scale difference rather than requiring manual rescaling.
    current_tick = -276325
    sqrt_price = get_sqrt_ratio_at_tick(current_tick)
    state = PoolState(
        pool="0x0000000000000000000000000000000000000001",
        token0=W0G_TOKEN,
        token1=USDCE_TOKEN,
        sqrt_price_x96=sqrt_price,
        tick=current_tick,
        tick_spacing=60,
    )
    lower, upper = derive_aligned_range(
        current_tick=current_tick,
        tick_spacing=60,
    )

    fraction = target_usdc_value_fraction(
        state,
        tick_lower=lower,
        tick_upper=upper,
    )

    assert 0.0 < fraction < 1.0
    # The +/-20% range is not exactly value-symmetric around spot, so this
    # should be close to, but intentionally not exactly, a 50/50 split.
    assert abs(fraction - 0.5) < 0.10
    assert abs(fraction - 0.5) > 0.001


def test_invalid_tick_spacing_is_rejected() -> None:
    with pytest.raises(ValueError, match="tick_spacing"):
        derive_aligned_range(
            current_tick=0,
            tick_spacing=0,
        )
