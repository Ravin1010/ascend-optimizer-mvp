"""CLI for personalized optimization using locally collected live snapshots.

The static readiness report only inspects values stored in snapshots. This CLI
also resolves amount-dependent LP slippage at runtime for the actual user amount.

The MVP currently accepts native 0G as the user input asset. a0G is a distinct
live external yield-bearing asset and is never treated as an alias for 0G.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .collectors.native_staking import fetch_0g_price_usd
from .data_loader import load_snapshots, load_strategies
from .pipeline import PipelineRun, run_optimizer_pipeline
from .profiles import get_profile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIVE_PATH = PROJECT_ROOT / "data" / "live_strategy_snapshots.csv"

PriceFn = Callable[[], float]


@dataclass(frozen=True)
class LiveOptimizerRun:
    """Resolved live inputs plus one solved personalized portfolio."""

    asset: str
    amount: float
    asset_price_usd: float
    horizon_days: float
    profile: str
    pipeline: PipelineRun
    include_modelled: bool

    @property
    def portfolio_value_usd(self) -> float:
        return self.amount * self.asset_price_usd

    @property
    def annualized_expected_net_apy(self) -> float:
        horizon_return = self.pipeline.result.expected_net_return_horizon
        if horizon_return <= -1:
            return -1.0
        return (1.0 + horizon_return) ** (365.0 / self.horizon_days) - 1.0


    def to_dict(self) -> dict[str, object]:
        """Return a stable, JSON-safe frontend contract for this optimizer run."""

        result = self.pipeline.result
        candidates = self.pipeline.candidates.copy()
        risk_profile = get_profile(self.profile)

        allocations = [
            {
                "strategy_id": strategy_id,
                "weight": float(weight),
                "amount_usd": float(
                    weight * self.portfolio_value_usd
                ),
            }
            for strategy_id, weight in sorted(
                result.allocations.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        strategy_rows: list[dict[str, object]] = []

        ranked = candidates.sort_values(
            "net_return_horizon",
            ascending=False,
            na_position="last",
        )

        for _, row in ranked.iterrows():
            strategy_id = str(row["strategy_id"])
            allocation_weight = float(
                result.allocations.get(strategy_id, 0.0)
            )

            scope_eligible = _json_bool(
                row.get("scope_eligible"),
                default=True,
            )
            profile_eligible = _json_bool(
                row.get("profile_eligible"),
                default=False,
            )
            optimizer_eligible = _json_bool(
                row.get("optimizer_eligible"),
                default=False,
            )

            profile_reasons = _split_reasons(
                row.get("profile_exclusion_reasons")
            )
            scope_reasons = _split_reasons(
                row.get("scope_exclusion_reason")
            )

            status = "PROFILE_ELIGIBLE"
            if not scope_eligible:
                status = "SCOPE_EXCLUDED"
            elif not profile_eligible:
                status = "PROFILE_EXCLUDED"

            strategy_rows.append(
                {
                    "strategy_id": strategy_id,
                    "status": status,
                    "optimizer_eligible": optimizer_eligible,
                    "profile_eligible": profile_eligible,
                    "scope_eligible": scope_eligible,
                    "exclusion_reasons": list(
                        dict.fromkeys(
                            scope_reasons + profile_reasons
                        )
                    ),
                    "technical_eligibility": _json_value(
                        row.get("technical_eligibility")
                    ),
                    "data_status": _json_value(
                        row.get("data_status")
                    ),
                    "net_apy": _json_value(
                        row.get("net_apy")
                    ),
                    "net_return_horizon": _json_value(
                        row.get("net_return_horizon")
                    ),
                    "net_profit_usd": _json_value(
                        row.get("net_profit_usd")
                    ),
                    "gross_apy_used": _json_value(
                        row.get("gross_apy_used")
                    ),
                    "liquidity_usd": _json_value(
                        row.get("liquidity_usd")
                    ),
                    "max_entry_exit_slippage": _json_value(
                        row.get("max_entry_exit_slippage")
                    ),
                    "exit_time_days": _json_value(
                        row.get("exit_time_days")
                    ),
                    "bridge_fraction": _json_value(
                        row.get("bridge_fraction")
                    ),
                    "slashing_stress_loss": _json_value(
                        row.get("slashing_stress_loss")
                    ),
                    "lp_stress_loss_20pct": _json_value(
                        row.get("lp_stress_loss_20pct")
                    ),
                    "allocation_weight": allocation_weight,
                    "allocation_usd": (
                        allocation_weight
                        * self.portfolio_value_usd
                    ),
                    "return_error": _json_value(
                        row.get("return_error")
                    ),
                    "runtime_exposure_error": _json_value(
                        row.get("runtime_exposure_error")
                    ),
                    "constraint_diagnostics": {
                        "strategy_concentration": _constraint_diagnostic(
                            allocation_weight,
                            risk_profile.max_strategy_concentration,
                        ),
                        "slippage": _constraint_diagnostic(
                            row.get("max_entry_exit_slippage"),
                            risk_profile.max_entry_exit_slippage,
                        ),
                        "exit_time": _constraint_diagnostic(
                            row.get("exit_time_days"),
                            risk_profile.max_exit_time_days,
                        ),
                        "bridge": _constraint_diagnostic(
                            row.get("bridge_fraction"),
                            risk_profile.max_bridge_exposure,
                        ),
                        "slashing": _constraint_diagnostic(
                            row.get("slashing_stress_loss"),
                            risk_profile.max_slashing_stress_loss,
                        ),
                        "lp_stress": _constraint_diagnostic(
                            row.get("lp_stress_loss_20pct"),
                            risk_profile.max_portfolio_lp_il_stress,
                        ),
                    },
                }
            )

        max_allocated_weight = max(
            [float(weight) for weight in result.allocations.values()],
            default=0.0,
        )
        allocated_ids = set(result.allocations)

        allocated_candidates = candidates[
            candidates["strategy_id"].astype(str).isin(allocated_ids)
        ].copy()

        max_allocated_slippage = 0.0
        max_allocated_exit_days = 0.0

        if not allocated_candidates.empty:
            slippage_values = pd.to_numeric(
                allocated_candidates["max_entry_exit_slippage"],
                errors="coerce",
            ).dropna()
            exit_values = pd.to_numeric(
                allocated_candidates["exit_time_days"],
                errors="coerce",
            ).dropna()

            if not slippage_values.empty:
                max_allocated_slippage = float(slippage_values.max())
            if not exit_values.empty:
                max_allocated_exit_days = float(exit_values.max())

        tolerance = 1e-9
        at_limit_constraints: list[str] = []

        if abs(
            max_allocated_weight
            - risk_profile.max_strategy_concentration
        ) <= tolerance:
            at_limit_constraints.append("max_strategy_concentration")

        if abs(
            result.portfolio_bridge_exposure
            - risk_profile.max_bridge_exposure
        ) <= tolerance:
            at_limit_constraints.append("max_bridge_exposure")

        if abs(
            result.portfolio_lp_il_stress
            - risk_profile.max_portfolio_lp_il_stress
        ) <= tolerance:
            at_limit_constraints.append("max_portfolio_lp_il_stress")

        if abs(
            result.portfolio_slashing_stress_loss
            - risk_profile.max_slashing_stress_loss
        ) <= tolerance:
            at_limit_constraints.append("max_slashing_stress_loss")

        if abs(
            max_allocated_slippage
            - risk_profile.max_entry_exit_slippage
        ) <= tolerance:
            at_limit_constraints.append("max_entry_exit_slippage")

        if abs(
            max_allocated_exit_days
            - risk_profile.max_exit_time_days
        ) <= tolerance:
            at_limit_constraints.append("max_exit_time_days")

        triggered_constraints: list[str] = []
        exclusion_text = "|".join(
            str(value)
            for value in candidates.get(
                "profile_exclusion_reasons",
                pd.Series(dtype="string"),
            ).fillna("")
        )

        if "slippage_exceeds_profile_limit" in exclusion_text:
            triggered_constraints.append("max_entry_exit_slippage")
        if "exit_time_exceeds_profile_limit" in exclusion_text:
            triggered_constraints.append("max_exit_time_days")

        return {
            "schema_version": "1.2",
            "input": {
                "asset": self.asset,
                "amount": float(self.amount),
                "asset_price_usd": float(self.asset_price_usd),
                "portfolio_value_usd": float(
                    self.portfolio_value_usd
                ),
                "horizon_days": float(self.horizon_days),
                "profile": self.profile,
                "include_modelled": bool(self.include_modelled),
            },
            "profile_constraints": {
                "max_strategy_concentration": float(
                    risk_profile.max_strategy_concentration
                ),
                "max_bridge_exposure": float(
                    risk_profile.max_bridge_exposure
                ),
                "max_entry_exit_slippage": float(
                    risk_profile.max_entry_exit_slippage
                ),
                "max_portfolio_lp_il_stress": float(
                    risk_profile.max_portfolio_lp_il_stress
                ),
                "max_exit_time_days": float(
                    risk_profile.max_exit_time_days
                ),
                "max_slashing_stress_loss": float(
                    risk_profile.max_slashing_stress_loss
                ),
                "at_limit_constraints": at_limit_constraints,
                "triggered_constraints": triggered_constraints,
                "observed": {
                    "max_allocated_strategy_weight": max_allocated_weight,
                    "max_allocated_slippage": max_allocated_slippage,
                    "max_allocated_exit_time_days": max_allocated_exit_days,
                    "portfolio_bridge_exposure": float(
                        result.portfolio_bridge_exposure
                    ),
                    "portfolio_lp_il_stress": float(
                        result.portfolio_lp_il_stress
                    ),
                    "portfolio_slashing_stress_loss": float(
                        result.portfolio_slashing_stress_loss
                    ),
                },
            },
            "portfolio": {
                "allocations": allocations,
                "idle": {
                    "weight": float(result.idle_weight),
                    "amount_usd": float(
                        result.idle_weight
                        * self.portfolio_value_usd
                    ),
                },
                "deployed_weight": float(
                    result.deployed_weight
                ),
                "expected_net_return_horizon": float(
                    result.expected_net_return_horizon
                ),
                "annualized_expected_net_apy": float(
                    self.annualized_expected_net_apy
                ),
                "expected_net_profit_usd": float(
                    result.expected_net_profit_usd
                ),
                "stress": {
                    "bridge_exposure": float(
                        result.portfolio_bridge_exposure
                    ),
                    "lp_il": float(
                        result.portfolio_lp_il_stress
                    ),
                    "slashing": float(
                        result.portfolio_slashing_stress_loss
                    ),
                },
            },
            "strategies": strategy_rows,
            "solver": {
                "status": int(result.solver_status),
                "message": str(result.solver_message),
            },
        }


def _constraint_diagnostic(
    value: object,
    limit: float,
    *,
    near_ratio: float = 0.90,
    tolerance: float = 1e-9,
) -> dict[str, object]:
    """Describe one measured constraint against its active profile limit."""

    json_value = _json_value(value)
    numeric_value = (
        None
        if json_value is None
        else float(json_value)
    )
    numeric_limit = float(limit)

    if numeric_value is None:
        return {
            "value": None,
            "limit": numeric_limit,
            "headroom": None,
            "utilization": None,
            "state": "UNAVAILABLE",
        }

    headroom = numeric_limit - numeric_value
    utilization = (
        numeric_value / numeric_limit
        if numeric_limit > 0
        else None
    )

    if numeric_value > numeric_limit + tolerance:
        state = "EXCEEDED"
    elif abs(numeric_value - numeric_limit) <= tolerance:
        state = "AT_LIMIT"
    elif utilization is not None and utilization >= near_ratio:
        state = "NEAR_LIMIT"
    else:
        state = "WITHIN_LIMIT"

    return {
        "value": numeric_value,
        "limit": numeric_limit,
        "headroom": headroom,
        "utilization": utilization,
        "state": state,
    }


def _json_value(value: Any) -> object:
    """Convert pandas/numpy scalar values into strict JSON-safe primitives."""

    if value is None or pd.isna(value):
        return None

    if isinstance(value, (bool, str)):
        return value

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, (int, float)):
        converted = float(value)
        if not isfinite(converted):
            return None
        if isinstance(value, int):
            return int(value)
        return converted

    return str(value)


def _json_bool(value: Any, *, default: bool) -> bool:
    if value is None or pd.isna(value):
        return default
    return bool(value)


def _split_reasons(value: Any) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [
        reason
        for reason in str(value).split("|")
        if reason
    ]


def _positive_finite(name: str, value: float) -> float:
    converted = float(value)
    if not isfinite(converted) or converted <= 0:
        raise ValueError(f"{name} must be finite and > 0")
    return converted


def _apply_live_scope(
    strategies: pd.DataFrame,
    *,
    include_modelled: bool,
) -> tuple[pd.DataFrame, set[str]]:
    """Retain the public flag without letting legacy statuses change membership.

    The frozen universe has only integrated routes. Modelled snapshot components
    remain governed by the existing checks; the flag cannot open a CLOSED gate
    or promote a tracked opportunity. No evidence-validity claim is added here.
    """
    return strategies.copy(), set()


def optimize_live(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    amount: float,
    horizon_days: float,
    profile: str,
    asset: str = "0G",
    price_usd: float | None = None,
    price_fn: PriceFn = fetch_0g_price_usd,
    management_fee_rate: float = 0.0,
    performance_fee_rate: float = 0.0,
    include_modelled: bool = False,
) -> LiveOptimizerRun:
    """Run one personalized optimizer solve from validated live datasets."""

    normalized_asset = str(asset).strip()
    if normalized_asset != "0G":
        raise ValueError(
            "Live MVP currently supports input asset '0G' only; "
            "a0G is a separate live external yield-bearing asset."
        )

    amount = _positive_finite("amount", amount)
    horizon_days = _positive_finite("horizon_days", horizon_days)
    risk_profile = get_profile(profile)

    if price_usd is None:
        resolved_price = _positive_finite("live 0G price", price_fn())
    else:
        resolved_price = _positive_finite("price_usd", price_usd)

    scoped_strategies, scope_excluded_ids = _apply_live_scope(
        strategies,
        include_modelled=include_modelled,
    )

    pipeline = run_optimizer_pipeline(
        scoped_strategies,
        snapshots,
        amount=amount,
        asset_price_usd=resolved_price,
        horizon_days=horizon_days,
        profile=risk_profile,
        management_fee_rate=management_fee_rate,
        performance_fee_rate=performance_fee_rate,
    )

    annotated = pipeline.candidates.copy()
    annotated["scope_eligible"] = ~annotated["strategy_id"].astype(str).isin(
        scope_excluded_ids
    )
    annotated["scope_exclusion_reason"] = annotated["strategy_id"].map(
        lambda strategy_id: (
            "modelled_strategy_excluded_by_default"
            if str(strategy_id) in scope_excluded_ids
            else ""
        )
    )
    pipeline = PipelineRun(
        candidates=annotated,
        result=pipeline.result,
    )

    return LiveOptimizerRun(
        asset=normalized_asset,
        amount=amount,
        asset_price_usd=resolved_price,
        horizon_days=horizon_days,
        profile=risk_profile.name.value,
        pipeline=pipeline,
        include_modelled=include_modelled,
    )


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.2%}"


def _fmt_usd(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return "$" + f"{float(value):,.2f}"


def print_live_json(run: LiveOptimizerRun) -> None:
    """Print strict machine-readable JSON with no NaN extensions."""

    print(
        json.dumps(
            run.to_dict(),
            indent=2,
            sort_keys=False,
            allow_nan=False,
        )
    )


def print_live_run(run: LiveOptimizerRun) -> None:
    """Print a concise dashboard-style terminal result."""

    result = run.pipeline.result
    candidates = run.pipeline.candidates.copy()

    print("Ascend Optimizer MVP - LIVE personalized portfolio")
    print(
        f"Input: {run.amount:,.4f} {run.asset} "
        f"@ {_fmt_usd(run.asset_price_usd)} "
        f"= {_fmt_usd(run.portfolio_value_usd)}"
    )
    scope_label = (
        "live + explicitly modelled routes"
        if run.include_modelled
        else "live routes only"
    )
    print(
        f"Horizon: {run.horizon_days:g} days | "
        f"Profile: {run.profile} | Scope: {scope_label}"
    )
    print()

    print("Strategy ranking")
    ranked = candidates[
        candidates["net_return_horizon"].notna()
    ].sort_values("net_return_horizon", ascending=False)

    if ranked.empty:
        print("  No strategy currently has a usable Net Return.")
    else:
        for _, row in ranked.iterrows():
            runtime_error = row.get("runtime_exposure_error")
            runtime_error = (
                ""
                if runtime_error is None or pd.isna(runtime_error)
                else str(runtime_error)
            )
            scope_eligible = bool(row.get("scope_eligible", True))
            scope_reason = row.get("scope_exclusion_reason")
            scope_reason = (
                ""
                if scope_reason is None or pd.isna(scope_reason)
                else str(scope_reason)
            )

            profile_eligible = bool(row.get("profile_eligible", False))
            reasons = row.get("profile_exclusion_reasons")
            reasons = (
                ""
                if reasons is None or pd.isna(reasons)
                else str(reasons)
            )

            if not scope_eligible:
                status = "SCOPE_EXCLUDED"
                if scope_reason:
                    status += f" ({scope_reason})"
            elif profile_eligible:
                status = "PROFILE_ELIGIBLE"
            else:
                status = "PROFILE_EXCLUDED"
                if reasons:
                    status += f" ({reasons})"

            if runtime_error and runtime_error not in reasons:
                status += f" ({runtime_error})"

            print(
                f"  {row['strategy_id']:<24} "
                f"NetAPY={_fmt_pct(row['net_apy']):>8} "
                f"H-return={_fmt_pct(row['net_return_horizon']):>8} "
                f"slip={_fmt_pct(row['max_entry_exit_slippage']):>8} "
                f"LPstress={_fmt_pct(row['lp_stress_loss_20pct']):>8} "
                f"{status}"
            )

    print()
    print("Recommended allocation")

    if result.allocations:
        for strategy_id, weight in sorted(
            result.allocations.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(
                f"  {strategy_id:<24} "
                f"{weight:>7.2%} "
                f"({_fmt_usd(weight * run.portfolio_value_usd)})"
            )
    else:
        print("  No strategy allocation.")

    if result.idle_weight > 1e-10:
        print(
            f"  {'IDLE':<24} "
            f"{result.idle_weight:>7.2%} "
            f"({_fmt_usd(result.idle_weight * run.portfolio_value_usd)})"
        )

    print()
    print(
        f"Expected {run.horizon_days:g}d Net Return: "
        f"{result.expected_net_return_horizon:.2%}"
    )
    print(
        "Annualized portfolio Net APY: "
        f"{run.annualized_expected_net_apy:.2%}"
    )
    print(f"Expected Net Profit: {_fmt_usd(result.expected_net_profit_usd)}")
    print(
        "Portfolio stress: "
        f"bridge={result.portfolio_bridge_exposure:.2%}, "
        f"LP_IL={result.portfolio_lp_il_stress:.2%}, "
        f"slashing={result.portfolio_slashing_stress_loss:.2%}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a personalized live 0G allocation using local snapshots "
            "and runtime LP quotes."
        )
    )
    parser.add_argument("--amount", type=float, required=True)
    parser.add_argument("--horizon-days", type=float, default=90.0)
    parser.add_argument("--profile", default="Balanced")
    parser.add_argument("--asset", default="0G")
    parser.add_argument("--price-usd", type=float, default=None)
    parser.add_argument("--management-fee-rate", type=float, default=0.0)
    parser.add_argument("--performance-fee-rate", type=float, default=0.0)
    parser.add_argument(
        "--include-modelled",
        action="store_true",
        help=(
            "Include MODELLED/PARTIAL_MODELLED Ascend routes in allocation. "
            "By default, the LIVE optimizer excludes them."
        ),
    )
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=DEFAULT_LIVE_PATH,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print the optimizer result as structured JSON instead of "
            "the terminal dashboard."
        ),
    )
    args = parser.parse_args()

    if not args.snapshots.exists():
        raise SystemExit(
            f"Live snapshot file not found: {args.snapshots}. "
            "Run the collectors first."
        )

    strategies = load_strategies(
        PROJECT_ROOT / "data" / "strategies.csv"
    )
    snapshots = load_snapshots(strategies, args.snapshots)

    try:
        run = optimize_live(
            strategies,
            snapshots,
            amount=args.amount,
            horizon_days=args.horizon_days,
            profile=args.profile,
            asset=args.asset,
            price_usd=args.price_usd,
            management_fee_rate=args.management_fee_rate,
            performance_fee_rate=args.performance_fee_rate,
            include_modelled=args.include_modelled,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.json:
        print_live_json(run)
    else:
        print_live_run(run)


if __name__ == "__main__":
    main()
