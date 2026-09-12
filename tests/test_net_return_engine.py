"""Tests for the frozen Ascend net-return equations."""

import math

import pandas as pd
import pytest

from src.ascend_optimizer.net_return_engine import (
    ReturnCalculationError,
    ReturnInputs,
    annualize_horizon_return,
    apr_to_apy,
    calculate_from_snapshot,
    calculate_net_return,
    gross_horizon_return,
)


def test_apr_to_apy_matches_formula() -> None:
    expected = (1 + 0.12 / 12) ** 12 - 1
    assert apr_to_apy(0.12, 12) == pytest.approx(expected)


def test_gross_horizon_return_matches_formula() -> None:
    expected = (1 + 0.10) ** (90 / 365) - 1
    assert gross_horizon_return(0.10, 90) == pytest.approx(expected)


def test_zero_fee_case_reduces_to_gross_return() -> None:
    result = calculate_net_return(
        ReturnInputs(
            amount=1000,
            asset_price_usd=1,
            horizon_days=90,
            gross_apy=0.10,
            yield_fee_status="NET_OF_PROTOCOL_FEES",
        )
    )

    expected_return = (1 + 0.10) ** (90 / 365) - 1

    assert result.principal_usd == pytest.approx(1000)
    assert result.net_return_horizon == pytest.approx(expected_return)
    assert result.net_apy == pytest.approx(0.10)


def test_full_fee_and_execution_cost_equation() -> None:
    result = calculate_net_return(
        ReturnInputs(
            amount=1000,
            asset_price_usd=2,
            horizon_days=90,
            gross_apy=0.12,
            incentive_apy=0.03,
            management_fee_rate=0.01,
            performance_fee_rate=0.10,
            protocol_fee_rate=0.05,
            yield_fee_status="GROSS_BEFORE_FEES",
            gas_cost_usd=2,
            bridge_cost_usd=3,
            deposit_cost_usd=1,
            withdrawal_cost_usd=1,
            entry_slippage_rate=0.002,
            exit_slippage_rate=0.003,
        )
    )

    principal = 2000
    gross_return = (1 + 0.15) ** (90 / 365) - 1
    gross_earnings = principal * gross_return
    protocol_fee = gross_earnings * 0.05
    management_fee = principal * 0.01 * 90 / 365
    performance_fee = gross_earnings * 0.10
    slippage = principal * (0.002 + 0.003)
    fixed_costs = 2 + 3 + 1 + 1
    expected_net_profit = (
        gross_earnings
        - protocol_fee
        - management_fee
        - performance_fee
        - slippage
        - fixed_costs
    )

    assert result.total_gross_apy == pytest.approx(0.15)
    assert result.protocol_fee_usd == pytest.approx(protocol_fee)
    assert result.management_fee_usd == pytest.approx(management_fee)
    assert result.performance_fee_usd == pytest.approx(performance_fee)
    assert result.slippage_cost_usd == pytest.approx(slippage)
    assert result.fixed_execution_cost_usd == pytest.approx(fixed_costs)
    assert result.net_profit_usd == pytest.approx(expected_net_profit)
    assert result.net_return_horizon == pytest.approx(expected_net_profit / principal)


def test_net_of_protocol_fees_does_not_double_count_protocol_fee() -> None:
    result = calculate_net_return(
        ReturnInputs(
            amount=1000,
            asset_price_usd=1,
            horizon_days=365,
            gross_apy=0.10,
            protocol_fee_rate=0.20,
            yield_fee_status="NET_OF_PROTOCOL_FEES",
        )
    )

    assert result.protocol_fee_usd == 0
    assert result.net_profit_usd == pytest.approx(100)


def test_unknown_fee_status_with_nonzero_protocol_fee_is_rejected() -> None:
    with pytest.raises(ReturnCalculationError, match="fee treatment must be resolved"):
        calculate_net_return(
            ReturnInputs(
                amount=1000,
                asset_price_usd=1,
                horizon_days=90,
                gross_apy=0.10,
                protocol_fee_rate=0.10,
                yield_fee_status="UNKNOWN",
            )
        )


def test_gross_apy_takes_precedence_over_apr() -> None:
    result = calculate_net_return(
        ReturnInputs(
            amount=1000,
            asset_price_usd=1,
            horizon_days=365,
            gross_apr=0.50,
            gross_apy=0.10,
            yield_fee_status="NET_OF_PROTOCOL_FEES",
        )
    )
    assert result.base_gross_apy == pytest.approx(0.10)


def test_missing_apr_and_apy_is_rejected() -> None:
    with pytest.raises(ReturnCalculationError, match="gross_apy or gross_apr"):
        calculate_net_return(
            ReturnInputs(
                amount=1000,
                asset_price_usd=1,
                horizon_days=90,
            )
        )


def test_fraction_above_one_is_rejected() -> None:
    with pytest.raises(ReturnCalculationError, match="between 0 and 1"):
        calculate_net_return(
            ReturnInputs(
                amount=1000,
                asset_price_usd=1,
                horizon_days=90,
                gross_apy=0.10,
                entry_slippage_rate=1.01,
            )
        )


def test_annualization_rejects_total_loss_or_worse() -> None:
    with pytest.raises(ReturnCalculationError, match="greater than -1"):
        annualize_horizon_return(-1.0, 90)


def test_calculate_from_snapshot_handles_missing_optional_costs() -> None:
    snapshot = pd.Series(
        {
            "gross_apr": pd.NA,
            "gross_apy": 0.08,
            "incentive_apy": pd.NA,
            "yield_fee_status": "UNKNOWN",
            "protocol_fee_rate": pd.NA,
            "gas_cost_usd": pd.NA,
            "bridge_cost_usd": pd.NA,
            "deposit_cost_usd": pd.NA,
            "withdrawal_cost_usd": pd.NA,
            "entry_slippage_rate": pd.NA,
            "exit_slippage_rate": pd.NA,
        }
    )

    result = calculate_from_snapshot(
        snapshot,
        amount=1000,
        asset_price_usd=1,
        horizon_days=365,
    )

    assert result.net_apy == pytest.approx(0.08)
    assert math.isfinite(result.net_profit_usd)
