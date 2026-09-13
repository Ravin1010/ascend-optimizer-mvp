"""Tests for transparent Ascend-modelled strategy snapshots."""

from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.ascend_model import (
    AscendModelError,
    build_ascend_model_rows,
    build_ascend_restake_snapshot,
    build_ascend_stake_snapshot,
    load_model_assumptions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _assumptions():
    return {
        "ASCEND_STAKE_A0G": {
            "protocol_fee_rate": 0.0,
            "entry_slippage_rate": 0.0,
            "exit_slippage_rate": 0.0,
        },
        "ASCEND_RESTAKE": {
            "incentive_apy": 0.0,
            "protocol_fee_rate": 0.0,
            "entry_slippage_rate": 0.0,
            "exit_slippage_rate": 0.0,
        },
    }


def _native_row():
    return pd.Series(
        {
            "strategy_id": "NATIVE_STAKE_0G",
            "gross_apr": pd.NA,
            "gross_apy": 0.147,
            "liquidity_usd": 1_000_000,
            "exit_time_days": 7,
            "slashing_stress_loss": 0.05,
        }
    )


def test_load_model_assumptions() -> None:
    result = load_model_assumptions(
        PROJECT_ROOT / "data" / "ascend_model_assumptions.csv"
    )

    assert result["ASCEND_STAKE_A0G"]["protocol_fee_rate"] == 0
    assert result["ASCEND_RESTAKE"]["incentive_apy"] == 0


def test_ascend_stake_inherits_native_yield_and_exposures() -> None:
    row = build_ascend_stake_snapshot(
        _native_row(),
        _assumptions(),
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["strategy_id"] == "ASCEND_STAKE_A0G"
    assert row["gross_apy"] == pytest.approx(0.147)
    assert row["liquidity_usd"] == pytest.approx(1_000_000)
    assert row["exit_time_days"] == pytest.approx(7)
    assert row["slashing_stress_loss"] == pytest.approx(0.05)
    assert row["data_status"] == "MODELLED"
    assert "not A0GI" in row["notes"]


def test_restake_excludes_points_and_preserves_route_gaps() -> None:
    stake = build_ascend_stake_snapshot(
        _native_row(),
        _assumptions(),
        timestamp="2026-09-13T00:00:00+00:00",
    )

    row = build_ascend_restake_snapshot(
        stake,
        _assumptions(),
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apy"] == pytest.approx(0.147)
    assert row["incentive_apy"] == 0
    assert row["exit_time_days"] is None
    assert row["slashing_stress_loss"] is None
    assert row["bridge_fraction"] is None
    assert row["data_status"] == "PARTIAL_MODELLED"
    assert "points are excluded" in row["notes"]


def test_model_rows_require_native_snapshot() -> None:
    empty = pd.DataFrame(
        columns=["timestamp", "strategy_id"]
    )

    with pytest.raises(AscendModelError, match="Native 0G snapshot"):
        build_ascend_model_rows(empty, _assumptions())
