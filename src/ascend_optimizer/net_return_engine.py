"""Net return calculations for the Ascend Optimizer MVP.

The implementation follows the frozen capstone equations:

    APY = (1 + APR / n) ** n - 1
    R_gross,H = (1 + g) ** (H / 365) - 1
    E_gross = V * R_gross,H
    ManagementFee_H = V * m * H / 365
    PerformanceFee = E_gross * p
    C_slippage = V * SlippageRate
    C_execution = gas + bridge + slippage + deposit + withdrawal
    NetProfit_H = E_gross - fees - C_execution
    NetReturn_H = NetProfit_H / V
    NetAPY = (1 + NetReturn_H) ** (365 / H) - 1

All rates are represented as decimal fractions: 0.05 means 5%.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import pandas as pd


VALID_YIELD_FEE_STATUSES = frozenset(
    {
        "GROSS_BEFORE_FEES",
        "NET_OF_PROTOCOL_FEES",
        "UNKNOWN",
    }
)


class ReturnCalculationError(ValueError):
    """Raised when net-return inputs are invalid or internally inconsistent."""


@dataclass(frozen=True)
class ReturnInputs:
    """Inputs required to estimate one strategy's horizon return."""

    amount: float
    asset_price_usd: float
    horizon_days: float

    gross_apr: float | None = None
    gross_apy: float | None = None
    incentive_apy: float = 0.0
    compounding_periods_per_year: int = 365

    management_fee_rate: float = 0.0
    performance_fee_rate: float = 0.0

    protocol_fee_rate: float = 0.0
    yield_fee_status: str = "UNKNOWN"

    gas_cost_usd: float = 0.0
    bridge_cost_usd: float = 0.0
    deposit_cost_usd: float = 0.0
    withdrawal_cost_usd: float = 0.0

    entry_slippage_rate: float = 0.0
    exit_slippage_rate: float = 0.0


@dataclass(frozen=True)
class ReturnResult:
    """Detailed output used by the optimizer and dashboard."""

    principal_usd: float
    base_gross_apy: float
    incentive_apy: float
    total_gross_apy: float

    gross_horizon_return: float
    gross_earnings_usd: float

    protocol_fee_usd: float
    management_fee_usd: float
    performance_fee_usd: float

    slippage_cost_usd: float
    fixed_execution_cost_usd: float
    total_execution_cost_usd: float

    net_profit_usd: float
    net_return_horizon: float
    net_apy: float


def _require_finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value):
        raise ReturnCalculationError(f"{name} must be finite")
    return value


def _require_non_negative(name: str, value: float) -> float:
    value = _require_finite(name, value)
    if value < 0:
        raise ReturnCalculationError(f"{name} must be >= 0")
    return value


def _require_fraction(name: str, value: float) -> float:
    value = _require_finite(name, value)
    if value < 0 or value > 1:
        raise ReturnCalculationError(f"{name} must be between 0 and 1")
    return value


def _optional_float(value: Any) -> float | None:
    """Convert a pandas/scalar value to float while preserving missing values."""

    if value is None or pd.isna(value):
        return None
    return float(value)


def apr_to_apy(apr: float, compounding_periods_per_year: int = 365) -> float:
    """Convert APR to APY using n compounding periods per year."""

    apr = _require_non_negative("apr", apr)

    if not isinstance(compounding_periods_per_year, int):
        raise ReturnCalculationError("compounding_periods_per_year must be an integer")
    if compounding_periods_per_year <= 0:
        raise ReturnCalculationError("compounding_periods_per_year must be > 0")

    n = compounding_periods_per_year
    return (1.0 + apr / n) ** n - 1.0


def resolve_base_gross_apy(
    *,
    gross_apy: float | None,
    gross_apr: float | None,
    compounding_periods_per_year: int = 365,
) -> float:
    """Resolve the strategy's base gross APY.

    A supplied gross APY takes precedence. APR is converted only when gross APY
    is unavailable. At least one of the two must be known before a strategy can
    be assigned a numerical expected return.
    """

    if gross_apy is not None:
        return _require_non_negative("gross_apy", gross_apy)

    if gross_apr is not None:
        return apr_to_apy(gross_apr, compounding_periods_per_year)

    raise ReturnCalculationError(
        "Cannot calculate return: provide gross_apy or gross_apr"
    )


def gross_horizon_return(annual_apy: float, horizon_days: float) -> float:
    """Convert annual APY into the expected return over H days."""

    annual_apy = _require_non_negative("annual_apy", annual_apy)
    horizon_days = _require_finite("horizon_days", horizon_days)

    if horizon_days <= 0:
        raise ReturnCalculationError("horizon_days must be > 0")

    return (1.0 + annual_apy) ** (horizon_days / 365.0) - 1.0


def annualize_horizon_return(net_return_horizon: float, horizon_days: float) -> float:
    """Annualize an H-day net return using the frozen capstone equation."""

    net_return_horizon = _require_finite(
        "net_return_horizon",
        net_return_horizon,
    )
    horizon_days = _require_finite("horizon_days", horizon_days)

    if horizon_days <= 0:
        raise ReturnCalculationError("horizon_days must be > 0")
    if net_return_horizon <= -1:
        raise ReturnCalculationError(
            "net_return_horizon must be greater than -1 to annualize"
        )

    return (1.0 + net_return_horizon) ** (365.0 / horizon_days) - 1.0


def calculate_net_return(inputs: ReturnInputs) -> ReturnResult:
    """Calculate horizon Net Return and Net APY for one strategy.

    Protocol-fee handling is intentionally conservative:

    * GROSS_BEFORE_FEES: protocol_fee_rate is deducted from gross earnings.
    * NET_OF_PROTOCOL_FEES: no protocol fee is deducted again.
    * UNKNOWN: a non-zero protocol_fee_rate is rejected because applying it
      could double-count a fee or omit one silently.

    incentive_apy is added to base gross APY. This is the MVP approximation for
    annualized incentives; points and non-monetary rewards remain excluded.
    """

    amount = _require_non_negative("amount", inputs.amount)
    asset_price_usd = _require_non_negative(
        "asset_price_usd",
        inputs.asset_price_usd,
    )
    horizon_days = _require_finite("horizon_days", inputs.horizon_days)

    if amount <= 0:
        raise ReturnCalculationError("amount must be > 0")
    if asset_price_usd <= 0:
        raise ReturnCalculationError("asset_price_usd must be > 0")
    if horizon_days <= 0:
        raise ReturnCalculationError("horizon_days must be > 0")

    base_gross_apy = resolve_base_gross_apy(
        gross_apy=inputs.gross_apy,
        gross_apr=inputs.gross_apr,
        compounding_periods_per_year=inputs.compounding_periods_per_year,
    )

    incentive_apy = _require_non_negative("incentive_apy", inputs.incentive_apy)
    total_gross_apy = base_gross_apy + incentive_apy

    management_fee_rate = _require_fraction(
        "management_fee_rate",
        inputs.management_fee_rate,
    )
    performance_fee_rate = _require_fraction(
        "performance_fee_rate",
        inputs.performance_fee_rate,
    )
    protocol_fee_rate = _require_fraction(
        "protocol_fee_rate",
        inputs.protocol_fee_rate,
    )
    entry_slippage_rate = _require_fraction(
        "entry_slippage_rate",
        inputs.entry_slippage_rate,
    )
    exit_slippage_rate = _require_fraction(
        "exit_slippage_rate",
        inputs.exit_slippage_rate,
    )

    if inputs.yield_fee_status not in VALID_YIELD_FEE_STATUSES:
        raise ReturnCalculationError(
            f"Invalid yield_fee_status={inputs.yield_fee_status!r}"
        )

    if inputs.yield_fee_status == "UNKNOWN" and protocol_fee_rate > 0:
        raise ReturnCalculationError(
            "protocol_fee_rate is non-zero while yield_fee_status=UNKNOWN; "
            "fee treatment must be resolved before calculating Net Return"
        )

    gas_cost_usd = _require_non_negative("gas_cost_usd", inputs.gas_cost_usd)
    bridge_cost_usd = _require_non_negative(
        "bridge_cost_usd",
        inputs.bridge_cost_usd,
    )
    deposit_cost_usd = _require_non_negative(
        "deposit_cost_usd",
        inputs.deposit_cost_usd,
    )
    withdrawal_cost_usd = _require_non_negative(
        "withdrawal_cost_usd",
        inputs.withdrawal_cost_usd,
    )

    principal_usd = amount * asset_price_usd

    gross_return = gross_horizon_return(total_gross_apy, horizon_days)
    gross_earnings_usd = principal_usd * gross_return

    protocol_fee_usd = 0.0
    if inputs.yield_fee_status == "GROSS_BEFORE_FEES":
        protocol_fee_usd = gross_earnings_usd * protocol_fee_rate

    management_fee_usd = (
        principal_usd * management_fee_rate * horizon_days / 365.0
    )
    performance_fee_usd = gross_earnings_usd * performance_fee_rate

    slippage_cost_usd = principal_usd * (
        entry_slippage_rate + exit_slippage_rate
    )
    fixed_execution_cost_usd = (
        gas_cost_usd
        + bridge_cost_usd
        + deposit_cost_usd
        + withdrawal_cost_usd
    )
    total_execution_cost_usd = slippage_cost_usd + fixed_execution_cost_usd

    net_profit_usd = (
        gross_earnings_usd
        - protocol_fee_usd
        - management_fee_usd
        - performance_fee_usd
        - total_execution_cost_usd
    )
    net_return_horizon = net_profit_usd / principal_usd
    net_apy = annualize_horizon_return(net_return_horizon, horizon_days)

    return ReturnResult(
        principal_usd=principal_usd,
        base_gross_apy=base_gross_apy,
        incentive_apy=incentive_apy,
        total_gross_apy=total_gross_apy,
        gross_horizon_return=gross_return,
        gross_earnings_usd=gross_earnings_usd,
        protocol_fee_usd=protocol_fee_usd,
        management_fee_usd=management_fee_usd,
        performance_fee_usd=performance_fee_usd,
        slippage_cost_usd=slippage_cost_usd,
        fixed_execution_cost_usd=fixed_execution_cost_usd,
        total_execution_cost_usd=total_execution_cost_usd,
        net_profit_usd=net_profit_usd,
        net_return_horizon=net_return_horizon,
        net_apy=net_apy,
    )


def calculate_from_snapshot(
    snapshot: pd.Series | dict[str, Any],
    *,
    amount: float,
    asset_price_usd: float,
    horizon_days: float,
    management_fee_rate: float = 0.0,
    performance_fee_rate: float = 0.0,
    compounding_periods_per_year: int = 365,
) -> ReturnResult:
    """Calculate return directly from one validated strategy snapshot row."""

    get = snapshot.get

    return calculate_net_return(
        ReturnInputs(
            amount=amount,
            asset_price_usd=asset_price_usd,
            horizon_days=horizon_days,
            gross_apr=_optional_float(get("gross_apr")),
            gross_apy=_optional_float(get("gross_apy")),
            incentive_apy=_optional_float(get("incentive_apy")) or 0.0,
            compounding_periods_per_year=compounding_periods_per_year,
            management_fee_rate=management_fee_rate,
            performance_fee_rate=performance_fee_rate,
            protocol_fee_rate=_optional_float(get("protocol_fee_rate")) or 0.0,
            yield_fee_status=str(get("yield_fee_status") or "UNKNOWN"),
            gas_cost_usd=_optional_float(get("gas_cost_usd")) or 0.0,
            bridge_cost_usd=_optional_float(get("bridge_cost_usd")) or 0.0,
            deposit_cost_usd=_optional_float(get("deposit_cost_usd")) or 0.0,
            withdrawal_cost_usd=(
                _optional_float(get("withdrawal_cost_usd")) or 0.0
            ),
            entry_slippage_rate=(
                _optional_float(get("entry_slippage_rate")) or 0.0
            ),
            exit_slippage_rate=(
                _optional_float(get("exit_slippage_rate")) or 0.0
            ),
        )
    )
