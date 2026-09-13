"""Constrained portfolio optimization for the Ascend Optimizer MVP.

The optimizer implements the frozen capstone formulation:

    maximize sum_i x_i * NetReturn_i,H

subject to:

    sum_i x_i + x_idle = 1
    x_i >= 0, x_idle >= 0
    x_i <= profile concentration cap
    sum_i x_i * bridge_i <= profile bridge cap
    sum_i x_i * LPStress_i <= profile LP stress cap
    x_i * portfolio_value_usd <= liquidity_i
    x_i = 0 when exit_time_i exceeds the profile limit
    x_i = 0 when entry/exit slippage exceeds the profile limit
    sum_i x_i * SlashStress_i <= profile slashing-stress cap

The idle allocation has zero modeled return and zero measured exposure. Keeping it
as an explicit decision variable makes the problem feasible even when every
strategy is ineligible or when all eligible strategies have negative returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from .profiles import ProfileName, RiskProfile, get_profile


REQUIRED_CANDIDATE_COLUMNS = (
    "strategy_id",
    "net_return_horizon",
    "optimizer_eligible",
    "liquidity_usd",
    "bridge_fraction",
    "lp_stress_loss_20pct",
    "exit_time_days",
    "slashing_stress_loss",
    "max_entry_exit_slippage",
)


class OptimizationError(ValueError):
    """Raised when optimizer inputs are invalid or the solver fails."""


@dataclass(frozen=True)
class PortfolioResult:
    """Portfolio allocation and constraint diagnostics."""

    profile: str
    portfolio_value_usd: float
    allocations: dict[str, float]
    idle_weight: float

    expected_net_return_horizon: float
    expected_net_profit_usd: float

    portfolio_bridge_exposure: float
    portfolio_lp_il_stress: float
    portfolio_slashing_stress_loss: float

    excluded_strategies: dict[str, tuple[str, ...]]

    solver_status: int
    solver_message: str

    @property
    def deployed_weight(self) -> float:
        """Total weight allocated to strategies rather than idle capital."""

        return float(sum(self.allocations.values()))

    def allocation_table(self) -> pd.DataFrame:
        """Return the portfolio weights in a dashboard-friendly table."""

        rows = [
            {"strategy_id": strategy_id, "weight": weight}
            for strategy_id, weight in self.allocations.items()
        ]
        rows.append({"strategy_id": "IDLE", "weight": self.idle_weight})
        return pd.DataFrame(rows)


def _require_positive_finite(name: str, value: float) -> float:
    value = float(value)
    if not isfinite(value) or value <= 0:
        raise OptimizationError(f"{name} must be finite and > 0")
    return value


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False

    if value in (0, 1):
        return bool(value)

    raise OptimizationError(
        f"optimizer_eligible must be boolean-like, received {value!r}"
    )


def _optional_finite_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None

    converted = float(value)
    if not isfinite(converted):
        return None
    return converted


def _validate_candidate_columns(candidates: pd.DataFrame) -> pd.DataFrame:
    missing = [
        column
        for column in REQUIRED_CANDIDATE_COLUMNS
        if column not in candidates.columns
    ]
    if missing:
        raise OptimizationError(
            f"candidate table missing required columns: {missing}"
        )

    result = candidates.copy()

    if result["strategy_id"].isna().any():
        raise OptimizationError("strategy_id must not be blank")

    result["strategy_id"] = result["strategy_id"].astype(str)

    duplicates = result["strategy_id"].duplicated(keep=False)
    if duplicates.any():
        duplicate_ids = sorted(result.loc[duplicates, "strategy_id"].unique())
        raise OptimizationError(
            f"strategy_id must be unique in optimizer candidates: {duplicate_ids}"
        )

    return result.reset_index(drop=True)


def _row_eligibility(
    row: pd.Series,
    profile: RiskProfile,
    portfolio_value_usd: float,
) -> tuple[float, tuple[str, ...], dict[str, float]]:
    """Return the strategy upper bound, exclusion reasons, and safe exposures."""

    reasons: list[str] = []

    try:
        optimizer_eligible = _coerce_bool(row["optimizer_eligible"])
    except OptimizationError as exc:
        reasons.append(str(exc))
        optimizer_eligible = False

    if not optimizer_eligible:
        reasons.append("optimizer_eligible=False")

    net_return = _optional_finite_float(row["net_return_horizon"])
    if net_return is None:
        reasons.append("missing_net_return_horizon")

    exposure_values: dict[str, float] = {}

    for field in (
        "liquidity_usd",
        "bridge_fraction",
        "lp_stress_loss_20pct",
        "exit_time_days",
        "slashing_stress_loss",
        "max_entry_exit_slippage",
    ):
        value = _optional_finite_float(row[field])
        if value is None:
            reasons.append(f"missing_{field}")
        else:
            exposure_values[field] = value

    if reasons:
        return 0.0, tuple(dict.fromkeys(reasons)), exposure_values

    liquidity_usd = exposure_values["liquidity_usd"]
    bridge_fraction = exposure_values["bridge_fraction"]
    lp_stress = exposure_values["lp_stress_loss_20pct"]
    exit_time_days = exposure_values["exit_time_days"]
    slashing_stress = exposure_values["slashing_stress_loss"]
    max_slippage = exposure_values["max_entry_exit_slippage"]

    if liquidity_usd < 0:
        reasons.append("liquidity_usd<0")

    for field, value in (
        ("bridge_fraction", bridge_fraction),
        ("lp_stress_loss_20pct", lp_stress),
        ("slashing_stress_loss", slashing_stress),
        ("max_entry_exit_slippage", max_slippage),
    ):
        if value < 0 or value > 1:
            reasons.append(f"{field}_outside_0_1")

    if exit_time_days < 0:
        reasons.append("exit_time_days<0")

    if max_slippage > profile.max_entry_exit_slippage:
        reasons.append(
            "slippage_exceeds_profile_limit"
        )

    if exit_time_days > profile.max_exit_time_days:
        reasons.append(
            "exit_time_exceeds_profile_limit"
        )

    if reasons:
        return 0.0, tuple(dict.fromkeys(reasons)), exposure_values

    liquidity_cap = liquidity_usd / portfolio_value_usd
    upper_bound = min(
        profile.max_strategy_concentration,
        liquidity_cap,
        1.0,
    )

    if upper_bound <= 0:
        reasons.append("no_usable_liquidity")
        upper_bound = 0.0

    return upper_bound, tuple(reasons), exposure_values


def optimize_portfolio(
    candidates: pd.DataFrame,
    *,
    portfolio_value_usd: float,
    profile: RiskProfile | ProfileName | str,
) -> PortfolioResult:
    """Solve the frozen linear portfolio-allocation problem.

    Parameters
    ----------
    candidates:
        One row per strategy. This is normally built by joining Net Return
        Engine results with the Exposure Engine table.
    portfolio_value_usd:
        USD value of the user's capital V.
    profile:
        Conservative, Balanced, Aggressive, or an explicit RiskProfile.
    """

    portfolio_value_usd = _require_positive_finite(
        "portfolio_value_usd",
        portfolio_value_usd,
    )

    if isinstance(profile, RiskProfile):
        risk_profile = profile
    else:
        risk_profile = get_profile(profile)

    table = _validate_candidate_columns(candidates)
    strategy_ids = table["strategy_id"].tolist()
    n = len(table)

    # Variable order: strategy weights followed by x_idle.
    returns = np.zeros(n + 1, dtype=float)
    bridge = np.zeros(n + 1, dtype=float)
    lp_stress = np.zeros(n + 1, dtype=float)
    slash_stress = np.zeros(n + 1, dtype=float)

    bounds: list[tuple[float, float]] = []
    excluded: dict[str, tuple[str, ...]] = {}

    for index, row in table.iterrows():
        strategy_id = str(row["strategy_id"])
        upper_bound, reasons, exposures = _row_eligibility(
            row,
            risk_profile,
            portfolio_value_usd,
        )

        net_return = _optional_finite_float(row["net_return_horizon"])
        returns[index] = 0.0 if net_return is None else net_return

        # Excluded rows have an upper bound of zero. Their coefficients can be
        # zeroed safely because they cannot enter the solution.
        if upper_bound > 0:
            bridge[index] = exposures["bridge_fraction"]
            lp_stress[index] = exposures["lp_stress_loss_20pct"]
            slash_stress[index] = exposures["slashing_stress_loss"]
        else:
            excluded[strategy_id] = reasons

        bounds.append((0.0, upper_bound))

    # Idle capital is always available and has zero expected return/exposure.
    bounds.append((0.0, 1.0))

    # scipy.optimize.linprog minimizes, so negate strategy returns.
    objective = -returns

    a_ub = np.vstack(
        [
            bridge,
            lp_stress,
            slash_stress,
        ]
    )
    b_ub = np.array(
        [
            risk_profile.max_bridge_exposure,
            risk_profile.max_portfolio_lp_il_stress,
            risk_profile.max_slashing_stress_loss,
        ],
        dtype=float,
    )

    a_eq = np.ones((1, n + 1), dtype=float)
    b_eq = np.array([1.0], dtype=float)

    solution = linprog(
        c=objective,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not solution.success or solution.x is None:
        raise OptimizationError(
            "Portfolio optimization failed: "
            f"status={solution.status}, message={solution.message}"
        )

    weights = np.asarray(solution.x[:n], dtype=float)
    idle_weight = float(solution.x[n])

    # Remove numerical solver dust from user-facing allocations.
    tolerance = 1e-10
    weights[np.abs(weights) < tolerance] = 0.0
    if abs(idle_weight) < tolerance:
        idle_weight = 0.0

    allocations = {
        strategy_id: float(weight)
        for strategy_id, weight in zip(strategy_ids, weights)
        if weight > tolerance
    }

    expected_net_return = float(np.dot(weights, returns[:n]))

    return PortfolioResult(
        profile=risk_profile.name.value,
        portfolio_value_usd=portfolio_value_usd,
        allocations=allocations,
        idle_weight=idle_weight,
        expected_net_return_horizon=expected_net_return,
        expected_net_profit_usd=portfolio_value_usd * expected_net_return,
        portfolio_bridge_exposure=float(np.dot(weights, bridge[:n])),
        portfolio_lp_il_stress=float(np.dot(weights, lp_stress[:n])),
        portfolio_slashing_stress_loss=float(
            np.dot(weights, slash_stress[:n])
        ),
        excluded_strategies=excluded,
        solver_status=int(solution.status),
        solver_message=str(solution.message),
    )
