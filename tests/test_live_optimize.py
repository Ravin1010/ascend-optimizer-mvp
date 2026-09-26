"""Tests for the personalized live optimizer helpers."""

from pathlib import Path

import pytest

from src.ascend_optimizer.data_loader import load_snapshots, load_strategies
from src.ascend_optimizer.live_optimize import optimize_live


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _demo_inputs():
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    snapshots = load_snapshots(
        strategies,
        PROJECT_ROOT / "data" / "demo_strategy_snapshots.csv",
    )
    return strategies, snapshots


def test_live_optimizer_fetches_price_when_not_overridden() -> None:
    strategies, snapshots = _demo_inputs()
    calls = 0

    def fake_price():
        nonlocal calls
        calls += 1
        return 2.0

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_fn=fake_price,
    )

    assert calls == 1
    assert run.asset_price_usd == pytest.approx(2.0)
    assert run.portfolio_value_usd == pytest.approx(2000)
    assert run.profile == "Balanced"
    assert run.pipeline.result.deployed_weight == pytest.approx(1.0)


def test_live_optimizer_price_override_skips_price_fetch() -> None:
    strategies, snapshots = _demo_inputs()

    def should_not_run():
        raise AssertionError("price feed should not be called")

    run = optimize_live(
        strategies,
        snapshots,
        amount=500,
        horizon_days=30,
        profile="Aggressive",
        price_usd=1.25,
        price_fn=should_not_run,
    )

    assert run.asset_price_usd == pytest.approx(1.25)
    assert run.portfolio_value_usd == pytest.approx(625)


def test_live_optimizer_rejects_a0g_as_0g_alias() -> None:
    strategies, snapshots = _demo_inputs()

    with pytest.raises(ValueError, match="a0G is a separate live external"):
        optimize_live(
            strategies,
            snapshots,
            amount=100,
            horizon_days=90,
            profile="Balanced",
            asset="a0G",
            price_usd=1,
        )


def test_live_optimizer_annualizes_portfolio_horizon_return() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Conservative",
        price_usd=1,
    )

    expected = (
        (1 + run.pipeline.result.expected_net_return_horizon)
        ** (365 / 90)
        - 1
    )

    assert run.annualized_expected_net_apy == pytest.approx(expected)


def test_live_optimizer_exposes_profile_specific_status() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    assert "profile_eligible" in run.pipeline.candidates.columns
    assert "profile_exclusion_reasons" in run.pipeline.candidates.columns

    oku = run.pipeline.candidates.loc[
        run.pipeline.candidates["strategy_id"] == "OKU_LP_0G_USDC"
    ].iloc[0]

    assert not oku["profile_eligible"]
    assert "slippage_exceeds_profile_limit" in oku[
        "profile_exclusion_reasons"
    ]


def test_live_optimizer_keeps_live_ascend_excluded_until_data_complete() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    ascend = run.pipeline.candidates.loc[
        run.pipeline.candidates["strategy_id"] == "ASCEND_STAKE_A0G"
    ].iloc[0]

    assert ascend["scope_eligible"]
    assert ascend["scope_exclusion_reason"] == ""
    assert not ascend["profile_eligible"]
    assert "technical_eligibility=EXCLUDED_LIVE_DATA_INCOMPLETE" in (
        ascend["profile_exclusion_reasons"]
    )
    assert "ASCEND_STAKE_A0G" not in run.pipeline.result.allocations


def test_include_modelled_flag_does_not_override_live_ascend_data_guard() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
        include_modelled=True,
    )

    ascend = run.pipeline.candidates.loc[
        run.pipeline.candidates["strategy_id"] == "ASCEND_STAKE_A0G"
    ].iloc[0]

    assert ascend["scope_eligible"]
    assert ascend["scope_exclusion_reason"] == ""
    assert not ascend["profile_eligible"]
    assert "technical_eligibility=EXCLUDED_LIVE_DATA_INCOMPLETE" in (
        ascend["profile_exclusion_reasons"]
    )
    assert run.include_modelled
