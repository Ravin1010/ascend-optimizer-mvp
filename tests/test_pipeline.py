"""Integration tests for the full Ascend optimizer pipeline."""

from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.lp_execution import LPExecutionQuote
from src.ascend_optimizer.data_loader import (
    load_datasets,
    load_snapshots,
    load_strategies,
)
from src.ascend_optimizer.pipeline import (
    build_optimizer_candidates,
    resolve_runtime_lp_exposures,
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

    # Live Ascend is intentionally excluded until its live risk measurements
    # are complete. Jaine/Oku exceed Conservative slippage limits, so the two
    # eligible staking routes each hit the 40% concentration cap and 20% stays
    # idle.
    assert result.allocations == pytest.approx(
        {
            "NATIVE_STAKE_0G": 0.40,
            "GIMO_STAKE_0G": 0.40,
        }
    )
    assert result.idle_weight == pytest.approx(0.20)


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

    # Embedded Ascend restaking is no longer a separate allocatable route.
    # Jaine has the best eligible return and reaches Balanced's 60%
    # concentration cap; Gimo fills the remaining 40%.
    assert result.allocations == pytest.approx(
        {
            "JAINE_LP_0G_USDC": 0.60,
            "GIMO_STAKE_0G": 0.40,
        }
    )
    assert result.portfolio_lp_il_stress == pytest.approx(0.60 * 0.08)
    assert result.portfolio_slashing_stress_loss == pytest.approx(
        0.40 * 0.015
    )


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

    # Oku has the highest eligible demo return and reaches Aggressive's 80%
    # concentration cap. Jaine fills the remaining 20%; both are non-bridge
    # LP routes in the demo metadata.
    assert result.allocations == pytest.approx(
        {
            "JAINE_LP_0G_USDC": 0.20,
            "OKU_LP_0G_USDC": 0.80,
        }
    )
    assert result.portfolio_bridge_exposure == pytest.approx(0)
    assert result.portfolio_lp_il_stress == pytest.approx(
        0.20 * 0.08 + 0.80 * 0.10
    )
    assert result.portfolio_slashing_stress_loss == pytest.approx(0)


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


def test_runtime_lp_exposures_use_user_amount_and_modelled_stress() -> None:
    strategies, snapshots = _demo_inputs()

    snapshots = snapshots.copy()
    mask = snapshots["strategy_id"] == "JAINE_LP_0G_USDC"
    snapshots.loc[mask, "entry_slippage_rate"] = pd.NA
    snapshots.loc[mask, "exit_slippage_rate"] = pd.NA
    snapshots.loc[mask, "lp_stress_loss_20pct"] = pd.NA

    captured = {}

    def fake_quote_fn(**kwargs):
        captured.update(kwargs)
        return LPExecutionQuote(
            strategy_id=kwargs["strategy_id"],
            fee_tier=3000,
            entry_slippage_rate=0.004,
            exit_slippage_rate=0.006,
            entry_amount_out_usdc=49.6,
            exit_amount_out_0g=49.4,
        )

    latest, errors = resolve_runtime_lp_exposures(
        snapshots,
        amount=100,
        asset_price_usd=2,
        lp_quote_fn=fake_quote_fn,
    )

    jaine = latest.loc[
        latest["strategy_id"] == "JAINE_LP_0G_USDC"
    ].iloc[0]

    assert errors == {}
    assert captured["amount_0g"] == pytest.approx(100)
    assert captured["asset_price_usd"] == pytest.approx(2)
    assert jaine["entry_slippage_rate"] == pytest.approx(0.004)
    assert jaine["exit_slippage_rate"] == pytest.approx(0.006)
    assert jaine["lp_stress_loss_20pct"] == pytest.approx(
        0.06358893302521518
    )
    assert jaine["data_status"] == "PARTIAL_MODELLED"


def test_runtime_lp_quote_failure_keeps_strategy_ineligible() -> None:
    strategies, snapshots = _demo_inputs()

    snapshots = snapshots.copy()
    mask = snapshots["strategy_id"] == "JAINE_LP_0G_USDC"
    snapshots.loc[mask, "entry_slippage_rate"] = pd.NA
    snapshots.loc[mask, "exit_slippage_rate"] = pd.NA
    snapshots.loc[mask, "lp_stress_loss_20pct"] = pd.NA

    from src.ascend_optimizer.collectors.common import CollectionError

    def failing_quote_fn(**kwargs):
        raise CollectionError("quote unavailable")

    candidates = build_optimizer_candidates(
        strategies,
        snapshots,
        amount=100,
        asset_price_usd=2,
        horizon_days=90,
        lp_quote_fn=failing_quote_fn,
    )

    jaine = candidates.loc[
        candidates["strategy_id"] == "JAINE_LP_0G_USDC"
    ].iloc[0]

    assert not jaine["optimizer_eligible"]
    assert "entry_slippage_rate" in jaine["missing_exposures"]
    assert jaine["runtime_exposure_error"] == "quote unavailable"


def test_pipeline_annotates_profile_specific_eligibility() -> None:
    strategies, snapshots = _demo_inputs()

    run = run_optimizer_pipeline(
        strategies,
        snapshots,
        amount=1000,
        asset_price_usd=1,
        horizon_days=90,
        profile="Balanced",
    )

    oku = run.candidates.loc[
        run.candidates["strategy_id"] == "OKU_LP_0G_USDC"
    ].iloc[0]
    jaine = run.candidates.loc[
        run.candidates["strategy_id"] == "JAINE_LP_0G_USDC"
    ].iloc[0]

    # Oku demo max slippage is 1.2%, above Balanced's 1.0% limit.
    assert not oku["profile_eligible"]
    assert "slippage_exceeds_profile_limit" in oku[
        "profile_exclusion_reasons"
    ]

    # Jaine demo max slippage is 0.6%, within Balanced's 1.0% limit.
    assert jaine["profile_eligible"]
    assert jaine["profile_exclusion_reasons"] == ""
