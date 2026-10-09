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


def test_reconciled_universe_and_gate_are_distinct_from_evidence() -> None:
    from src.ascend_optimizer.data_loader import MVP_STRATEGY_IDS, load_strategies

    strategies = load_strategies().set_index("strategy_id")
    members = strategies.index[strategies["optimizer_universe"].eq("TRUE")]
    assert set(members) == MVP_STRATEGY_IDS
    assert strategies.loc["JAINE_LP_0G_USDC", "allocation_gate"] == "CONDITIONAL"
    assert not strategies.loc["JAINE_LP_0G_USDC", "technical_eligibility"].startswith("EXCLUDED")
    assert strategies.loc["ASCEND_STAKE_A0G", "protocol_availability"] == "LIVE"
    assert strategies.loc["ASCEND_STAKE_A0G", "allocation_gate"] == "CLOSED"
    assert strategies.loc["ASCEND_STAKE_A0G", "dependency_chain_ids"] == "1"
    assert strategies.loc[list(MVP_STRATEGY_IDS), "live_capstone_proof"].eq("NOT_ESTABLISHED").all()
    morpho = strategies.loc["MORPHO_LEND_0G"]
    assert morpho["network"] == "0G Mainnet"
    assert morpho["chain_id"] == "16661"
    assert morpho["reconciliation_category"] == "OBSERVED_EXCLUDED"
    assert morpho["integration_status"] == "NOT_INTEGRATED"
    assert pd.isna(morpho["execution_chain_id"])
    assert pd.isna(morpho["contract_or_pool_id"])


@pytest.mark.parametrize("strategy_id,column,value", [
    ("ASCEND_RESTAKE", "optimizer_universe", "TRUE"),
    ("ASCEND_STAKE_A0G", "allocation_gate", "CONDITIONAL"),
    ("GIMO_STAKE_0G", "execution_chain_id", "16602"),
    ("ASCEND_RESTAKE", "parent_strategy_id", "UNKNOWN"),
])
def test_metadata_contradictions_are_rejected(strategy_id, column, value) -> None:
    frame = pd.read_csv(PROJECT_ROOT / "data/strategies.csv", dtype="string")
    frame.loc[frame.strategy_id.eq(strategy_id), column] = value
    with pytest.raises(SchemaValidationError):
        validate_strategies(frame)


def test_source_registry_and_non_candidate_inventory_validate() -> None:
    from src.ascend_optimizer.data_loader import load_source_registry, load_tracked_records

    sources = load_source_registry()
    tracked = load_tracked_records()
    assert len(sources) == 31
    assert sources.source_id.is_unique
    assert sources.capture_status.eq("NO_FRESH_CAPTURE_SUPPLIED").all()
    assert tracked.optimizer_universe.eq("FALSE").all()
    assert set(tracked.reconciliation_category) == {"OBSERVED_EXCLUDED", "AUXILIARY_NOT_STRATEGY", "KIV_FUTURE"}
    assert tracked.loc[tracked.record_id.eq("IAI"), "source_coverage"].iloc[0] == "GAP"


@pytest.mark.parametrize("column,value", [
    ("strategy_id", "UNKNOWN"),
    ("mechanism_evidence_class", "VERIFIED_LIVE_PROFIT"),
    ("last_verified_utc", "not-a-date"),
    ("capture_status", "FRESH"),
])
def test_invalid_source_registry_is_rejected(tmp_path, column, value) -> None:
    from src.ascend_optimizer.data_loader import load_source_registry

    frame = pd.read_csv(PROJECT_ROOT / "data/source_registry.csv", dtype="string")
    frame.loc[0, column] = value
    path = tmp_path / "source_registry.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(SchemaValidationError):
        load_source_registry(path)


def test_auxiliary_record_cannot_enter_optimizer_universe(tmp_path) -> None:
    from src.ascend_optimizer.data_loader import load_tracked_records

    frame = pd.read_csv(PROJECT_ROOT / "data/tracked_records.csv", dtype="string")
    frame.loc[frame.record_id.eq("W0G"), "optimizer_universe"] = "TRUE"
    path = tmp_path / "tracked_records.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(SchemaValidationError):
        load_tracked_records(path)


def test_demo_snapshot_contract_remains_explicitly_non_live() -> None:
    from src.ascend_optimizer.data_loader import load_strategies, load_snapshots

    snapshots = load_snapshots(load_strategies(), PROJECT_ROOT / "data/demo_strategy_snapshots.csv")
    assert len(snapshots) == 7
    assert snapshots.source.eq("DEMO_ONLY_ASSUMPTION").all()


def test_legacy_eligibility_cannot_override_metadata_at_load_time() -> None:
    frame = pd.read_csv(PROJECT_ROOT / "data/strategies.csv", dtype="string")
    frame.loc[frame.strategy_id.eq("JAINE_LP_0G_USDC"), "technical_eligibility"] = "EXCLUDED_LIQUIDITY_CONSTRAINED"
    frame.loc[frame.strategy_id.eq("ASCEND_STAKE_A0G"), "technical_eligibility"] = "ELIGIBLE"
    result = validate_strategies(frame).set_index("strategy_id")
    assert result.loc["JAINE_LP_0G_USDC", "allocation_gate"] == "CONDITIONAL"
    assert result.loc["ASCEND_STAKE_A0G", "allocation_gate"] == "CLOSED"
