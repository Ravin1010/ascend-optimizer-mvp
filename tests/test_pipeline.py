"""Integration tests for the full Ascend optimizer pipeline."""

from pathlib import Path

import pytest

from src.ascend_optimizer.data_loader import (
    load_datasets,
    load_snapshots,
    load_strategies,
)
from src.ascend_optimizer.pipeline import (
    build_optimizer_candidates,
    run_optimizer_pipeline,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_current_scaffold_surfaces_missing_data_without_fabrication() -> None:
    bundle = load_datasets(PROJECT_ROOT / "data")

    candidates = build_optimizer_candidates(
        bundle.strategies,
        bundle.snapshots,
        amount=1000,
        asset_price_usd=1,
        horizon_days=90,
    )

    assert len(candidates) == 7
    assert candidates["net_return_horizon"].isna().all()
    assert not candidates["optimizer_eligible"].any()
    assert candidates["return_error"].str.contains(
        "gross_apy or gross_apr"
    ).all()


def _demo_inputs():
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    snapshots = load_snapshots(
        strategies,
        PROJECT_ROOT / "data" / "demo_strategy_snapshots.csv",
    )
    return strategies, snapshots


def test_demo_conservative_allocation() -> None:
    strategies, snapshots = _demo_inputs()

    result = run_optimizer_pipeline(
        strategies,
        snapshots,
        amount=1000,
        asset_price_usd=1,
        horizon_days=90,
        profile="Conservative",
    ).result

    assert result.allocations == pytest.approx(
        {
            "NATIVE_STAKE_0G": 0.20,
            "GIMO_STAKE_0G": 0.40,
            "ASCEND_STAKE_A0G": 0.40,
        }
    )
    assert result.idle_weight == pytest.approx(0)


def test_demo_balanced_allocation() -> None:
    strategies, snapshots = _demo_inputs()

    result = run_optimizer_pipeline(
        strategies,
        snapshots,
        amount=1000,
        asset_price_usd=1,
        horizon_days=90,
        profile="Balanced",
    ).result

    assert result.allocations == pytest.approx(
        {
            "JAINE_LP_0G_USDC": 0.60,
            "ASCEND_RESTAKE": 0.40,
        }
    )
    assert result.portfolio_lp_il_stress == pytest.approx(0.048)
    assert result.portfolio_slashing_stress_loss == pytest.approx(0.048)


def test_demo_aggressive_allocation() -> None:
    strategies, snapshots = _demo_inputs()

    result = run_optimizer_pipeline(
        strategies,
        snapshots,
        amount=1000,
        asset_price_usd=1,
        horizon_days=90,
        profile="Aggressive",
    ).result

    assert result.allocations == pytest.approx(
        {
            "JAINE_LP_0G_USDC": 0.20,
            "ASCEND_RESTAKE": 0.80,
        }
    )
    assert result.portfolio_bridge_exposure == pytest.approx(0.20)
    assert result.portfolio_slashing_stress_loss == pytest.approx(0.096)


def test_morpho_stays_excluded_even_with_demo_numbers() -> None:
    strategies, snapshots = _demo_inputs()

    run = run_optimizer_pipeline(
        strategies,
        snapshots,
        amount=1000,
        asset_price_usd=1,
        horizon_days=90,
        profile="Aggressive",
    )

    assert "MORPHO_LEND_0G" not in run.result.allocations
    assert "optimizer_eligible=False" in run.result.excluded_strategies[
        "MORPHO_LEND_0G"
    ]
