"""Tests for the frozen SciPy portfolio optimizer."""

import pandas as pd
import pytest

from src.ascend_optimizer.optimizer import (
    OptimizationError,
    optimize_portfolio,
)


def _candidate(
    strategy_id: str,
    net_return: float,
    *,
    eligible: bool = True,
    liquidity: float = 1_000_000,
    bridge: float = 0.0,
    lp_stress: float = 0.0,
    exit_days: float = 1.0,
    slash: float = 0.0,
    slippage: float = 0.001,
) -> dict:
    return {
        "strategy_id": strategy_id,
        "net_return_horizon": net_return,
        "optimizer_eligible": eligible,
        "liquidity_usd": liquidity,
        "bridge_fraction": bridge,
        "lp_stress_loss_20pct": lp_stress,
        "exit_time_days": exit_days,
        "slashing_stress_loss": slash,
        "max_entry_exit_slippage": slippage,
    }


def test_balanced_profile_respects_concentration_cap() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("A", 0.10),
            _candidate("B", 0.08),
            _candidate("C", 0.05),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Balanced",
    )

    assert result.allocations["A"] == pytest.approx(0.60)
    assert result.allocations["B"] == pytest.approx(0.40)
    assert result.idle_weight == pytest.approx(0.0)
    assert max(result.allocations.values()) <= 0.60 + 1e-9


def test_bridge_constraint_binds_portfolio() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("BRIDGED", 0.20, bridge=1.0),
            _candidate("LOCAL", 0.10, bridge=0.0),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Aggressive",
    )

    assert result.allocations["BRIDGED"] == pytest.approx(0.50)
    assert result.allocations["LOCAL"] == pytest.approx(0.50)
    assert result.portfolio_bridge_exposure == pytest.approx(0.50)


def test_lp_stress_constraint_binds_portfolio() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("LP", 0.20, lp_stress=0.10),
            _candidate("SAFE", 0.10),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Balanced",
    )

    assert result.allocations["LP"] == pytest.approx(0.50)
    assert result.allocations["SAFE"] == pytest.approx(0.50)
    assert result.portfolio_lp_il_stress == pytest.approx(0.05)


def test_slashing_constraint_binds_portfolio() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("RESTAKE", 0.20, slash=0.20),
            _candidate("SAFE", 0.10),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Aggressive",
    )

    assert result.allocations["RESTAKE"] == pytest.approx(0.50)
    assert result.allocations["SAFE"] == pytest.approx(0.50)
    assert result.portfolio_slashing_stress_loss == pytest.approx(0.10)


def test_liquidity_capacity_limits_strategy_weight() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("HIGH_RETURN", 0.20, liquidity=250),
            _candidate("OTHER", 0.10),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Aggressive",
    )

    assert result.allocations["HIGH_RETURN"] == pytest.approx(0.25)
    assert result.allocations["OTHER"] == pytest.approx(0.75)


def test_exit_time_above_profile_limit_excludes_strategy() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("TOO_SLOW", 0.30, exit_days=31),
            _candidate("OK", 0.10, exit_days=1),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Balanced",
    )

    assert "TOO_SLOW" not in result.allocations
    assert "exit_time_exceeds_profile_limit" in result.excluded_strategies[
        "TOO_SLOW"
    ]


def test_slippage_above_profile_limit_excludes_strategy() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("TOO_SLIPPERY", 0.30, slippage=0.011),
            _candidate("OK", 0.10, slippage=0.005),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Balanced",
    )

    assert "TOO_SLIPPERY" not in result.allocations
    assert "slippage_exceeds_profile_limit" in result.excluded_strategies[
        "TOO_SLIPPERY"
    ]


def test_ineligible_strategy_is_excluded() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("BLOCKED", 0.30, eligible=False),
            _candidate("OK", 0.10),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Aggressive",
    )

    assert "BLOCKED" not in result.allocations
    assert "optimizer_eligible=False" in result.excluded_strategies["BLOCKED"]


def test_negative_returns_prefer_idle_capital() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("LOSS_A", -0.05),
            _candidate("LOSS_B", -0.01),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Aggressive",
    )

    assert result.allocations == {}
    assert result.idle_weight == pytest.approx(1.0)
    assert result.expected_net_return_horizon == pytest.approx(0.0)


def test_all_ineligible_returns_all_idle() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("A", 0.20, eligible=False),
            _candidate("B", 0.10, eligible=False),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Conservative",
    )

    assert result.allocations == {}
    assert result.idle_weight == pytest.approx(1.0)


def test_expected_return_and_profit_are_weighted() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("A", 0.10),
            _candidate("B", 0.05),
        ]
    )

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=2000,
        profile="Aggressive",
    )

    # Aggressive concentration cap: 80% A, remaining 20% B.
    expected_return = 0.8 * 0.10 + 0.2 * 0.05
    assert result.expected_net_return_horizon == pytest.approx(expected_return)
    assert result.expected_net_profit_usd == pytest.approx(
        2000 * expected_return
    )


def test_missing_return_is_excluded_not_fabricated() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("UNKNOWN_RETURN", 0.20),
            _candidate("OK", 0.10),
        ]
    )
    candidates.loc[0, "net_return_horizon"] = pd.NA

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=1000,
        profile="Aggressive",
    )

    assert "UNKNOWN_RETURN" not in result.allocations
    assert "missing_net_return_horizon" in result.excluded_strategies[
        "UNKNOWN_RETURN"
    ]


def test_missing_required_column_is_rejected() -> None:
    candidates = pd.DataFrame([_candidate("A", 0.10)]).drop(
        columns=["liquidity_usd"]
    )

    with pytest.raises(OptimizationError, match="missing required columns"):
        optimize_portfolio(
            candidates,
            portfolio_value_usd=1000,
            profile="Balanced",
        )


def test_duplicate_strategy_ids_are_rejected() -> None:
    candidates = pd.DataFrame(
        [
            _candidate("A", 0.10),
            _candidate("A", 0.08),
        ]
    )

    with pytest.raises(OptimizationError, match="must be unique"):
        optimize_portfolio(
            candidates,
            portfolio_value_usd=1000,
            profile="Balanced",
        )


def test_nonpositive_portfolio_value_is_rejected() -> None:
    candidates = pd.DataFrame([_candidate("A", 0.10)])

    with pytest.raises(OptimizationError, match="finite and > 0"):
        optimize_portfolio(
            candidates,
            portfolio_value_usd=0,
            profile="Balanced",
        )
