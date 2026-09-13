"""Tests for runtime LP slippage and concentrated-liquidity stress."""

import pytest

from src.ascend_optimizer.lp_execution import (
    JAINE_QUOTER_V1,
    MODELLED_LP_STRESS_20PCT,
    OKU_QUOTER_V2,
    QUOTE_V1_SELECTOR,
    QUOTE_V2_SELECTOR,
    RPC_URL,
    USDCE_TOKEN,
    W0G_TOKEN,
    concentrated_lp_stress_loss,
    estimate_lp_execution_slippage,
    quote_exact_input_single,
)


def _encode_uint(value: int, words: int = 1) -> str:
    return "0x" + hex(value)[2:].zfill(64 * words)


def test_modelled_lp_stress_is_worse_of_plus_minus_20pct() -> None:
    result = concentrated_lp_stress_loss()

    assert result == pytest.approx(0.06358893302521518)
    assert MODELLED_LP_STRESS_20PCT == pytest.approx(result)


def test_quote_v1_encoding_and_decode() -> None:
    amount_in = 123456789

    def fake_rpc(url, method, params):
        assert url == RPC_URL
        assert method == "eth_call"
        assert params[0]["to"] == JAINE_QUOTER_V1
        assert params[0]["data"].startswith(QUOTE_V1_SELECTOR)
        assert W0G_TOKEN.lower().removeprefix("0x") in params[0]["data"]
        assert USDCE_TOKEN.lower().removeprefix("0x") in params[0]["data"]
        assert params[1] == "latest"
        return _encode_uint(987654321)

    result = quote_exact_input_single(
        quoter=JAINE_QUOTER_V1,
        mode="V1",
        token_in=W0G_TOKEN,
        token_out=USDCE_TOKEN,
        fee_tier=3000,
        amount_in=amount_in,
        rpc_fn=fake_rpc,
    )

    assert result == 987654321


def test_quote_v2_decodes_first_return_word() -> None:
    def fake_rpc(url, method, params):
        assert url == RPC_URL
        assert params[0]["to"] == OKU_QUOTER_V2
        assert params[0]["data"].startswith(QUOTE_V2_SELECTOR)
        # QuoterV2 returns four static words; amountOut is the first.
        return (
            "0x"
            + hex(123)[2:].zfill(64)
            + hex(456)[2:].zfill(64)
            + hex(7)[2:].zfill(64)
            + hex(890)[2:].zfill(64)
        )

    result = quote_exact_input_single(
        quoter=OKU_QUOTER_V2,
        mode="V2",
        token_in=W0G_TOKEN,
        token_out=USDCE_TOKEN,
        fee_tier=10000,
        amount_in=10**18,
        rpc_fn=fake_rpc,
    )

    assert result == 123


def test_execution_slippage_uses_whole_portfolio_notional() -> None:
    # 100 0G at $2 = $200 portfolio. Half is swapped on each leg.
    # Entry expected = $100, quote returns 99 USDC -> 1/200 = 0.5%.
    # Exit expected = $100, quote returns 49 0G = $98 -> 2/200 = 1%.
    call_count = 0

    def fake_rpc(url, method, params):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _encode_uint(99 * 10**6)
        return _encode_uint(49 * 10**18)

    snapshot = {"notes": "pool=0xabc; fee_tier=3000; pool_name=test"}

    result = estimate_lp_execution_slippage(
        strategy_id="JAINE_LP_0G_USDC",
        snapshot=snapshot,
        amount_0g=100,
        asset_price_usd=2,
        rpc_fn=fake_rpc,
    )

    assert result.entry_slippage_rate == pytest.approx(0.005)
    assert result.exit_slippage_rate == pytest.approx(0.01)
    assert result.max_entry_exit_slippage == pytest.approx(0.01)
