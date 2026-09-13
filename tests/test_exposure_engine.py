"""Tests for measurable strategy exposure extraction."""

from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.data_loader import load_datasets
from src.ascend_optimizer.exposure_engine import (
    build_exposure_table,
    build_strategy_exposure,
    latest_snapshot_rows,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _strategy(**overrides):
    row = {
        "strategy_id": "S1",
        "category": "STAKING",
        "execution_status": "LIVE",
        "technical_eligibility": "ELIGIBLE",
        "bridge_required": "FALSE",
        "bridge_fraction": 0.0,
    }
    row.update(overrides)
    return row


def _snapshot(**overrides):
    row = {
        "strategy_id": "S1",
        "data_status": "LIVE",
        "liquidity_usd": 1_000_000,
        "entry_slippage_rate": 0.001,
        "exit_slippage_rate": 0.002,
        "exit_time_days": 7,
        "slashing_stress_loss": 0.02,
        "bridge_fraction": pd.NA,
        "lp_stress_loss_20pct": pd.NA,
    }
    row.update(overrides)
    return row


def test_staking_exposure_uses_measurable_fields() -> None:
    exposure = build_strategy_exposure(_strategy(), _snapshot())

    assert exposure.slashing_stress_loss == pytest.approx(0.02)
    assert exposure.lp_stress_loss_20pct == 0
    assert exposure.bridge_fraction == 0
    assert exposure.max_entry_exit_slippage == pytest.approx(0.002)
    assert exposure.risk_data_complete is True
    assert exposure.optimizer_eligible is True


def test_lp_exposure_uses_lp_stress_and_zero_slashing() -> None:
    strategy = _strategy(
        category="LIQUIDITY_PROVISION",
        bridge_required="FALSE",
    )
    snapshot = _snapshot(
        slashing_stress_loss=pd.NA,
        lp_stress_loss_20pct=0.08,
    )

    exposure = build_strategy_exposure(strategy, snapshot)

    assert exposure.slashing_stress_loss == 0
    assert exposure.lp_stress_loss_20pct == pytest.approx(0.08)
    assert exposure.optimizer_eligible is True


def test_snapshot_bridge_fraction_overrides_static_metadata() -> None:
    strategy = _strategy(
        bridge_required="TRUE",
        bridge_fraction=0.25,
    )
    snapshot = _snapshot(bridge_fraction=0.40)

    exposure = build_strategy_exposure(strategy, snapshot)

    assert exposure.bridge_fraction == pytest.approx(0.40)


def test_missing_required_exposure_blocks_optimizer() -> None:
    exposure = build_strategy_exposure(
        _strategy(),
        _snapshot(exit_time_days=pd.NA),
    )

    assert exposure.technical_eligible is True
    assert exposure.risk_data_complete is False
    assert exposure.optimizer_eligible is False
    assert "exit_time_days" in exposure.missing_exposures


def test_pending_strategy_is_not_technically_eligible() -> None:
    exposure = build_strategy_exposure(
        _strategy(
            execution_status="PENDING",
            technical_eligibility="EXCLUDED_PENDING",
        ),
        _snapshot(),
    )

    assert exposure.technical_eligible is False
    assert exposure.optimizer_eligible is False
    assert any(
        reason.startswith("execution_status=PENDING")
        for reason in exposure.eligibility_reasons
    )


def test_strategy_snapshot_id_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="strategy/snapshot mismatch"):
        build_strategy_exposure(
            _strategy(strategy_id="S1"),
            _snapshot(strategy_id="S2"),
        )


def test_latest_snapshot_prefers_newest_timestamp() -> None:
    snapshots = pd.DataFrame(
        [
            {"strategy_id": "S1", "timestamp": pd.Timestamp("2026-01-01", tz="UTC"), "value": 1},
            {"strategy_id": "S1", "timestamp": pd.Timestamp("2026-01-03", tz="UTC"), "value": 3},
            {"strategy_id": "S1", "timestamp": pd.Timestamp("2026-01-02", tz="UTC"), "value": 2},
            {"strategy_id": "S2", "timestamp": pd.NaT, "value": 4},
            {"strategy_id": "S2", "timestamp": pd.NaT, "value": 5},
        ]
    )

    latest = latest_snapshot_rows(snapshots)

    s1 = latest.loc[latest["strategy_id"] == "S1"].iloc[0]
    s2 = latest.loc[latest["strategy_id"] == "S2"].iloc[0]

    assert s1["value"] == 3
    assert s2["value"] == 5


def test_frozen_dataset_exposes_current_data_gaps_without_inventing_values() -> None:
    bundle = load_datasets(PROJECT_ROOT / "data")
    table = build_exposure_table(bundle.strategies, bundle.snapshots)

    assert len(table) == 7
    assert not table["optimizer_eligible"].any()

    native = table.loc[table["strategy_id"] == "NATIVE_STAKE_0G"].iloc[0]
    assert native["bridge_fraction"] == 0
    assert "liquidity_usd" in native["missing_exposures"]
    assert "exit_time_days" in native["missing_exposures"]

    morpho = table.loc[table["strategy_id"] == "MORPHO_LEND_0G"].iloc[0]
    assert morpho["technical_eligible"] == False
    assert "execution_status=PENDING" in morpho["eligibility_reasons"]
