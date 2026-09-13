"""Tests for the Jaine 0G/USDC.e live collector."""

import pytest

from src.ascend_optimizer.collectors.merkl import MerklIncentiveObservation
from src.ascend_optimizer.collectors.jaine import (
    GET_POOL_SELECTOR,
    JAINE_FACTORY,
    RPC_URL,
    USDCE_TOKEN,
    W0G_TOKEN,
    JaineMarketObservation,
    JainePool,
    build_jaine_snapshot,
    collect_market_observation,
    discover_jaine_pools,
    get_pool_address,
)


def _encode_address_result(address: str) -> str:
    return "0x" + address.lower().removeprefix("0x").zfill(64)


def test_get_pool_address_builds_factory_call() -> None:
    expected_pool = "0x1111111111111111111111111111111111111111"

    def fake_rpc(url, method, params):
        assert url == RPC_URL
        assert method == "eth_call"
        assert params[0]["to"] == JAINE_FACTORY
        calldata = params[0]["data"]
        assert calldata.startswith(GET_POOL_SELECTOR)
        assert W0G_TOKEN.lower().removeprefix("0x") in calldata
        assert USDCE_TOKEN.lower().removeprefix("0x") in calldata
        assert params[1] == "latest"
        return _encode_address_result(expected_pool)

    assert get_pool_address(3000, rpc_fn=fake_rpc).lower() == expected_pool


def test_discover_jaine_pools_skips_zero_addresses() -> None:
    pool500 = "0x2222222222222222222222222222222222222222"
    pool3000 = "0x3333333333333333333333333333333333333333"

    def fake_rpc(url, method, params):
        fee_tier = int(params[0]["data"][-64:], 16)
        mapping = {
            100: "0x0000000000000000000000000000000000000000",
            500: pool500,
            3000: pool3000,
            10000: "0x0000000000000000000000000000000000000000",
        }
        return _encode_address_result(mapping[fee_tier])

    pools = discover_jaine_pools(rpc_fn=fake_rpc)

    assert [(pool.address.lower(), pool.fee_tier) for pool in pools] == [
        (pool500, 500),
        (pool3000, 3000),
    ]


def test_collect_market_observation_selects_highest_liquidity_pool() -> None:
    pool500 = "0x2222222222222222222222222222222222222222"
    pool3000 = "0x3333333333333333333333333333333333333333"

    def fake_rpc(url, method, params):
        fee_tier = int(params[0]["data"][-64:], 16)
        mapping = {
            100: "0x0000000000000000000000000000000000000000",
            500: pool500,
            3000: pool3000,
            10000: "0x0000000000000000000000000000000000000000",
        }
        return _encode_address_result(mapping[fee_tier])

    def fake_json(url, headers=None):
        if pool500.lower() in url.lower():
            reserve = "1000"
            volume = "100"
        else:
            reserve = "5000"
            volume = "200"
        return {
            "data": {
                "attributes": {
                    "name": "W0G / USDC.e",
                    "reserve_in_usd": reserve,
                    "volume_usd": {"h24": volume},
                }
            }
        }

    result = collect_market_observation(
        rpc_fn=fake_rpc,
        json_fn=fake_json,
    )

    assert result.pool.fee_tier == 3000
    assert result.liquidity_usd == pytest.approx(5000)
    assert result.volume_24h_usd == pytest.approx(200)


def test_fee_apr_proxy_matches_formula() -> None:
    observation = JaineMarketObservation(
        pool=JainePool(
            address="0x4444444444444444444444444444444444444444",
            fee_tier=3000,
        ),
        name="W0G / USDC.e",
        liquidity_usd=10_000,
        volume_24h_usd=2_000,
    )

    expected = 2_000 * 0.003 * 365 / 10_000

    assert observation.fee_apr == pytest.approx(expected)


def test_jaine_snapshot_preserves_unresolved_lp_risk_fields() -> None:
    observation = JaineMarketObservation(
        pool=JainePool(
            address="0x4444444444444444444444444444444444444444",
            fee_tier=3000,
        ),
        name="W0G / USDC.e",
        liquidity_usd=10_000,
        volume_24h_usd=2_000,
    )

    row = build_jaine_snapshot(
        observation,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apr"] == pytest.approx(
        2_000 * 0.003 * 365 / 10_000
    )
    assert row["liquidity_usd"] == pytest.approx(10_000)
    assert row["volume_24h_usd"] == pytest.approx(2_000)
    assert row["entry_slippage_rate"] is None
    assert row["exit_slippage_rate"] is None
    assert row["lp_stress_loss_20pct"] is None
    assert row["incentive_apy"] is None
    assert row["data_status"] == "LIVE_INCOMPLETE"


def test_jaine_snapshot_includes_merkl_campaign_incentive() -> None:
    observation = JaineMarketObservation(
        pool=JainePool(
            address="0x4444444444444444444444444444444444444444",
            fee_tier=3000,
        ),
        name="W0G / USDC.e",
        liquidity_usd=10_000,
        volume_24h_usd=2_000,
    )
    incentive = MerklIncentiveObservation(
        pool_address=observation.pool.address,
        campaign_apr=0.05,
        incentive_apy=0.051267,
        matched_opportunities=1,
        matched_campaigns=2,
    )

    row = build_jaine_snapshot(
        observation,
        incentive=incentive,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["incentive_apy"] == pytest.approx(0.051267)
    assert "merkl_campaign_apr=0.05" in row["notes"]
    assert "merkl_campaigns=2" in row["notes"]
