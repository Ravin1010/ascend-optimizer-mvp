"""CLI for personalized optimization using locally collected live snapshots.

The static readiness report only inspects values stored in snapshots. This CLI
also resolves amount-dependent LP slippage at runtime for the actual user amount.

The MVP currently accepts 0G as the input asset. a0G remains a distinct,
modelled Ascend asset and is never treated as an alias for 0G.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Callable

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

    @property
    def portfolio_value_usd(self) -> float:
        return self.amount * self.asset_price_usd

    @property
    def annualized_expected_net_apy(self) -> float:
        horizon_return = self.pipeline.result.expected_net_return_horizon
        if horizon_return <= -1:
            return -1.0
        return (1.0 + horizon_return) ** (365.0 / self.horizon_days) - 1.0


def _positive_finite(name: str, value: float) -> float:
    converted = float(value)
    if not isfinite(converted) or converted <= 0:
        raise ValueError(f"{name} must be finite and > 0")
    return converted


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
) -> LiveOptimizerRun:
    """Run one personalized optimizer solve from validated live datasets."""

    normalized_asset = str(asset).strip()
    if normalized_asset != "0G":
        raise ValueError(
            "Live MVP currently supports input asset '0G' only; "
            "a0G remains a separate Ascend-modelled asset."
        )

    amount = _positive_finite("amount", amount)
    horizon_days = _positive_finite("horizon_days", horizon_days)
    risk_profile = get_profile(profile)

    if price_usd is None:
        resolved_price = _positive_finite("live 0G price", price_fn())
    else:
        resolved_price = _positive_finite("price_usd", price_usd)

    pipeline = run_optimizer_pipeline(
        strategies,
        snapshots,
        amount=amount,
        asset_price_usd=resolved_price,
        horizon_days=horizon_days,
        profile=risk_profile,
        management_fee_rate=management_fee_rate,
        performance_fee_rate=performance_fee_rate,
    )

    return LiveOptimizerRun(
        asset=normalized_asset,
        amount=amount,
        asset_price_usd=resolved_price,
        horizon_days=horizon_days,
        profile=risk_profile.name.value,
        pipeline=pipeline,
    )


def _fmt_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):.2%}"


def _fmt_usd(value: object) -> str:
    if value is None or pd.isna(value):
        return "-"
    return "$" + f"{float(value):,.2f}"


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
    print(f"Horizon: {run.horizon_days:g} days | Profile: {run.profile}")
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
            profile_eligible = bool(row.get("profile_eligible", False))
            reasons = row.get("profile_exclusion_reasons")
            reasons = (
                ""
                if reasons is None or pd.isna(reasons)
                else str(reasons)
            )

            if profile_eligible:
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
        "--snapshots",
        type=Path,
        default=DEFAULT_LIVE_PATH,
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
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print_live_run(run)


if __name__ == "__main__":
    main()
