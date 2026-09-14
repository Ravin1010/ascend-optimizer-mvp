"""Tests for the Section 6.4 profile evaluation harness."""

from pathlib import Path

import pytest

from src.ascend_optimizer.data_loader import load_snapshots, load_strategies
from src.ascend_optimizer.evaluation import (
    evaluate_profiles,
    evaluation_table,
    verify_constraints,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _demo_inputs():
    strategies = load_strategies(
        PROJECT_ROOT / "data" / "strategies.csv"
    )
    snapshots = load_snapshots(
        strategies,
        PROJECT_ROOT / "data" / "demo_strategy_snapshots.csv",
    )
    return strategies, snapshots


def test_evaluation_runs_all_three_profiles() -> None:
    strategies, snapshots = _demo_inputs()

    cases = evaluate_profiles(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        price_usd=1,
    )

    assert [case.run.profile for case in cases] == [
        "Conservative",
        "Balanced",
        "Aggressive",
    ]


def test_evaluation_verifies_all_profile_constraints() -> None:
    strategies, snapshots = _demo_inputs()

    cases = evaluate_profiles(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        price_usd=1,
    )

    assert all(case.constraints.all_ok for case in cases)


def test_evaluation_table_is_report_friendly() -> None:
    strategies, snapshots = _demo_inputs()

    cases = evaluate_profiles(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        price_usd=1,
    )
    table = evaluation_table(cases)

    assert list(table["profile"]) == [
        "Conservative",
        "Balanced",
        "Aggressive",
    ]
    assert table["constraints_ok"].all()
    assert set(table["scope"]) == {"LIVE_ONLY"}
    assert "allocations" in table.columns


def test_modelled_scope_is_explicit() -> None:
    strategies, snapshots = _demo_inputs()

    cases = evaluate_profiles(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        price_usd=1,
        include_modelled=True,
    )
    table = evaluation_table(cases)

    assert set(table["scope"]) == {"LIVE_PLUS_MODELLED"}
    assert all(case.run.include_modelled for case in cases)


def test_verify_constraints_detects_valid_solution() -> None:
    strategies, snapshots = _demo_inputs()

    case = evaluate_profiles(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        price_usd=1,
    )[1]

    checked = verify_constraints(case.run)

    assert checked.all_ok
    assert checked.concentration_ok
    assert checked.bridge_ok
    assert checked.lp_stress_ok
    assert checked.slashing_ok
