"""Tests for Ascend optimizer dataset loading and schema validation."""

from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.data_loader import (
    SchemaValidationError,
    STRATEGY_COLUMNS,
    YIELD_FEE_STATUSES,
    load_datasets,
    validate_snapshots,
    validate_strategies,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_frozen_project_datasets_validate() -> None:
    bundle = load_datasets(PROJECT_ROOT / "data")

    assert bundle.strategy_count == 7
    assert bundle.snapshot_count == 7
    assert bundle.strategies["strategy_id"].is_unique

    assert set(bundle.strategies["strategy_id"]) == {
        "NATIVE_STAKE_0G",
        "GIMO_STAKE_0G",
        "JAINE_LP_0G_USDC",
        "OKU_LP_0G_USDC",
        "ASCEND_STAKE_A0G",
        "ASCEND_RESTAKE",
        "MORPHO_LEND_0G",
    }

    assert set(bundle.snapshots["yield_fee_status"]) <= YIELD_FEE_STATUSES


def test_missing_strategy_column_is_rejected() -> None:
    df = pd.DataFrame([{column: "x" for column in STRATEGY_COLUMNS}])
    df = df.drop(columns=["strategy_name"])

    with pytest.raises(SchemaValidationError, match="missing columns"):
        validate_strategies(df)


def test_duplicate_strategy_id_is_rejected() -> None:
    source = pd.read_csv(PROJECT_ROOT / "data" / "strategies.csv", dtype="string")
    duplicate = pd.concat([source, source.iloc[[0]]], ignore_index=True)

    with pytest.raises(SchemaValidationError, match="must be unique"):
        validate_strategies(duplicate)


def test_invalid_yield_fee_status_is_rejected() -> None:
    strategies = validate_strategies(
        pd.read_csv(PROJECT_ROOT / "data" / "strategies.csv", dtype="string")
    )
    snapshots = pd.read_csv(
        PROJECT_ROOT / "data" / "strategy_snapshots.csv",
        dtype="string",
    )
    snapshots.loc[0, "yield_fee_status"] = "NET_APY_ALREADY_MAGIC"

    with pytest.raises(SchemaValidationError, match="invalid value"):
        validate_snapshots(snapshots, strategies)


def test_orphan_snapshot_strategy_id_is_rejected() -> None:
    strategies = validate_strategies(
        pd.read_csv(PROJECT_ROOT / "data" / "strategies.csv", dtype="string")
    )
    snapshots = pd.read_csv(
        PROJECT_ROOT / "data" / "strategy_snapshots.csv",
        dtype="string",
    )
    snapshots.loc[0, "strategy_id"] = "UNKNOWN_STRATEGY"

    with pytest.raises(SchemaValidationError, match="not present in strategies.csv"):
        validate_snapshots(snapshots, strategies)


def test_fraction_outside_zero_to_one_is_rejected() -> None:
    strategies = validate_strategies(
        pd.read_csv(PROJECT_ROOT / "data" / "strategies.csv", dtype="string")
    )
    snapshots = pd.read_csv(
        PROJECT_ROOT / "data" / "strategy_snapshots.csv",
        dtype="string",
    )
    snapshots.loc[0, "entry_slippage_rate"] = "1.5"

    with pytest.raises(SchemaValidationError, match="between 0 and 1"):
        validate_snapshots(snapshots, strategies)
