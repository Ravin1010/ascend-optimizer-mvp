"""Tests for the live strategy readiness report."""

from pathlib import Path

import pandas as pd

from src.ascend_optimizer.data_loader import (
    SNAPSHOT_COLUMNS,
    load_strategies,
    validate_snapshots,
)
from src.ascend_optimizer.readiness import build_readiness_table


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _row(strategy_id: str, **overrides):
    row = {column: None for column in SNAPSHOT_COLUMNS}
    row.update(
        {
            "timestamp": "2026-09-13T00:00:00+00:00",
            "strategy_id": strategy_id,
            "yield_fee_status": "NET_OF_PROTOCOL_FEES",
            "data_status": "LIVE_INCOMPLETE",
            "source": "TEST",
        }
    )
    row.update(overrides)
    return row


def test_readiness_separates_return_and_exposure_gaps() -> None:
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")

    frame = pd.DataFrame(
        [
            _row(
                "NATIVE_STAKE_0G",
                gross_apy=0.14,
                liquidity_usd=1_000_000,
                entry_slippage_rate=0,
                exit_slippage_rate=0,
                exit_time_days=7,
                slashing_stress_loss=0.01,
                bridge_fraction=0,
            ),
            _row(
                "GIMO_STAKE_0G",
                gross_apy=None,
                liquidity_usd=1_000_000,
                entry_slippage_rate=0,
                exit_slippage_rate=0,
                exit_time_days=22,
                slashing_stress_loss=0.01,
                bridge_fraction=0,
            ),
            _row(
                "JAINE_LP_0G_USDC",
                gross_apr=0.08,
                incentive_apy=0,
                liquidity_usd=100_000,
                entry_slippage_rate=None,
                exit_slippage_rate=None,
                exit_time_days=0,
                bridge_fraction=0,
                lp_stress_loss_20pct=None,
            ),
        ],
        columns=SNAPSHOT_COLUMNS,
    )

    snapshots = validate_snapshots(frame.astype("string"), strategies)
    table = build_readiness_table(strategies, snapshots)

    native = table.loc[
        table["strategy_id"] == "NATIVE_STAKE_0G"
    ].iloc[0]
    assert native["return_ready"]
    assert native["optimizer_eligible"]

    gimo = table.loc[
        table["strategy_id"] == "GIMO_STAKE_0G"
    ].iloc[0]
    assert not gimo["return_ready"]
    assert gimo["next_gap"] == "yield"

    jaine = table.loc[
        table["strategy_id"] == "JAINE_LP_0G_USDC"
    ].iloc[0]
    assert jaine["return_ready"]
    assert not jaine["optimizer_eligible"]
    assert "entry_slippage_rate" in jaine["missing_exposures"]
    assert "lp_stress_loss_20pct" in jaine["missing_exposures"]


def test_missing_live_snapshot_is_reported_explicitly() -> None:
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")

    frame = pd.DataFrame(
        [
            _row(
                "NATIVE_STAKE_0G",
                gross_apy=0.14,
            )
        ],
        columns=SNAPSHOT_COLUMNS,
    )
    snapshots = validate_snapshots(frame.astype("string"), strategies)

    table = build_readiness_table(strategies, snapshots)

    morpho = table.loc[
        table["strategy_id"] == "MORPHO_LEND_0G"
    ].iloc[0]

    assert morpho["data_status"] == "MISSING"
    assert morpho["missing_exposures"] == "no_live_snapshot"
    assert morpho["next_gap"] == "collect_or_model_snapshot"



def test_embedded_restaking_never_appears_return_ready() -> None:
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")

    frame = pd.DataFrame(
        [
            _row(
                "ASCEND_RESTAKE",
                gross_apy=0.147,
                incentive_apy=0,
            )
        ],
        columns=SNAPSHOT_COLUMNS,
    )
    snapshots = validate_snapshots(frame.astype("string"), strategies)

    table = build_readiness_table(strategies, snapshots)
    row = table.loc[
        table["strategy_id"] == "ASCEND_RESTAKE"
    ].iloc[0]

    assert not row["return_ready"]
    assert not row["optimizer_eligible"]
    assert pd.isna(row["gross_apy"])
    assert row["next_gap"] == "technical_eligibility"
