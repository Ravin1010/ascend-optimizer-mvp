"""Section 6.4 evaluation harness for the Ascend Optimizer MVP.

Runs the same user case through Conservative, Balanced, and Aggressive profiles,
records allocations/returns/stress, and independently checks that the solved
portfolio respects the selected profile constraints.

The harness deliberately reuses the live optimizer path so live/modelled scope,
runtime LP quoting, Net Return calculations, and portfolio optimization are
evaluated exactly as a user-facing run would be.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .collectors.native_staking import fetch_0g_price_usd
from .data_loader import load_snapshots, load_strategies
from .live_optimize import LiveOptimizerRun, optimize_live
from .profiles import ProfileName, get_profile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIVE_PATH = PROJECT_ROOT / "data" / "live_strategy_snapshots.csv"


@dataclass(frozen=True)
class ConstraintCheck:
    """Independent post-solve checks against one frozen risk profile."""

    concentration_ok: bool
    bridge_ok: bool
    lp_stress_ok: bool
    slashing_ok: bool

    @property
    def all_ok(self) -> bool:
        return (
            self.concentration_ok
            and self.bridge_ok
            and self.lp_stress_ok
            and self.slashing_ok
        )


@dataclass(frozen=True)
class EvaluationCase:
    """One profile result plus explicit constraint verification."""

    run: LiveOptimizerRun
    constraints: ConstraintCheck


def verify_constraints(run: LiveOptimizerRun) -> ConstraintCheck:
    """Independently verify portfolio-level frozen profile constraints."""

    profile = get_profile(run.profile)
    result = run.pipeline.result
    tolerance = 1e-9

    max_strategy_weight = max(
        result.allocations.values(),
        default=0.0,
    )

    return ConstraintCheck(
        concentration_ok=(
            max_strategy_weight
            <= profile.max_strategy_concentration + tolerance
        ),
        bridge_ok=(
            result.portfolio_bridge_exposure
            <= profile.max_bridge_exposure + tolerance
        ),
        lp_stress_ok=(
            result.portfolio_lp_il_stress
            <= profile.max_portfolio_lp_il_stress + tolerance
        ),
        slashing_ok=(
            result.portfolio_slashing_stress_loss
            <= profile.max_slashing_stress_loss + tolerance
        ),
    )


def evaluate_profiles(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    amount: float,
    horizon_days: float,
    price_usd: float,
    include_modelled: bool = False,
) -> tuple[EvaluationCase, ...]:
    """Run the same case through all three frozen risk profiles."""

    cases: list[EvaluationCase] = []

    for profile_name in ProfileName:
        run = optimize_live(
            strategies,
            snapshots,
            amount=amount,
            horizon_days=horizon_days,
            profile=profile_name.value,
            price_usd=price_usd,
            include_modelled=include_modelled,
        )
        cases.append(
            EvaluationCase(
                run=run,
                constraints=verify_constraints(run),
            )
        )

    return tuple(cases)


def evaluation_table(
    cases: tuple[EvaluationCase, ...],
) -> pd.DataFrame:
    """Return a report-friendly summary table."""

    rows: list[dict[str, object]] = []

    for case in cases:
        run = case.run
        result = run.pipeline.result

        rows.append(
            {
                "profile": run.profile,
                "scope": (
                    "LIVE_PLUS_MODELLED"
                    if run.include_modelled
                    else "LIVE_ONLY"
                ),
                "portfolio_value_usd": run.portfolio_value_usd,
                "expected_net_return_horizon": (
                    result.expected_net_return_horizon
                ),
                "annualized_net_apy": (
                    run.annualized_expected_net_apy
                ),
                "expected_net_profit_usd": (
                    result.expected_net_profit_usd
                ),
                "idle_weight": result.idle_weight,
                "bridge_exposure": (
                    result.portfolio_bridge_exposure
                ),
                "lp_il_stress": result.portfolio_lp_il_stress,
                "slashing_stress": (
                    result.portfolio_slashing_stress_loss
                ),
                "constraints_ok": case.constraints.all_ok,
                "allocations": "|".join(
                    f"{strategy_id}:{weight:.8f}"
                    for strategy_id, weight in sorted(
                        result.allocations.items()
                    )
                ),
            }
        )

    return pd.DataFrame(rows)


def _fmt_pct(value: float) -> str:
    return f"{float(value):.2%}"


def _fmt_usd(value: float) -> str:
    return "$" + f"{float(value):,.2f}"


def print_evaluation(
    cases: tuple[EvaluationCase, ...],
) -> None:
    """Print a concise profile-comparison report."""

    if not cases:
        print("No evaluation cases.")
        return

    first = cases[0].run
    scope = (
        "live + modelled Ascend"
        if first.include_modelled
        else "live routes only"
    )

    print("Ascend Optimizer MVP - profile evaluation")
    print(
        f"Input: {first.amount:,.4f} {first.asset} "
        f"@ {_fmt_usd(first.asset_price_usd)} "
        f"= {_fmt_usd(first.portfolio_value_usd)}"
    )
    print(
        f"Horizon: {first.horizon_days:g} days | Scope: {scope}"
    )
    print()

    for case in cases:
        run = case.run
        result = run.pipeline.result

        print(run.profile)
        if result.allocations:
            for strategy_id, weight in sorted(
                result.allocations.items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                print(
                    f"  {strategy_id:<24} "
                    f"{weight:>7.2%}"
                )
        if result.idle_weight > 1e-10:
            print(f"  {'IDLE':<24} {result.idle_weight:>7.2%}")

        print(
            f"  NetReturn={_fmt_pct(result.expected_net_return_horizon)} | "
            f"NetAPY={_fmt_pct(run.annualized_expected_net_apy)} | "
            f"Profit={_fmt_usd(result.expected_net_profit_usd)}"
        )
        print(
            "  Stress: "
            f"bridge={_fmt_pct(result.portfolio_bridge_exposure)}, "
            f"LP={_fmt_pct(result.portfolio_lp_il_stress)}, "
            f"slash={_fmt_pct(result.portfolio_slashing_stress_loss)}"
        )
        print(
            "  Constraint verification: "
            + ("PASS" if case.constraints.all_ok else "FAIL")
        )
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one optimizer case across Conservative, Balanced, "
            "and Aggressive profiles."
        )
    )
    parser.add_argument("--amount", type=float, default=1000.0)
    parser.add_argument("--horizon-days", type=float, default=90.0)
    parser.add_argument("--price-usd", type=float, default=None)
    parser.add_argument(
        "--include-modelled",
        action="store_true",
        help="Include Ascend MODELLED/PARTIAL_MODELLED routes.",
    )
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=DEFAULT_LIVE_PATH,
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Optional path to write the profile-comparison CSV.",
    )
    args = parser.parse_args()

    if not args.snapshots.exists():
        raise SystemExit(
            f"Snapshot file not found: {args.snapshots}. "
            "Run collectors first."
        )

    strategies = load_strategies(
        PROJECT_ROOT / "data" / "strategies.csv"
    )
    snapshots = load_snapshots(strategies, args.snapshots)

    price_usd = (
        float(args.price_usd)
        if args.price_usd is not None
        else fetch_0g_price_usd()
    )

    cases = evaluate_profiles(
        strategies,
        snapshots,
        amount=args.amount,
        horizon_days=args.horizon_days,
        price_usd=price_usd,
        include_modelled=args.include_modelled,
    )

    print_evaluation(cases)

    if args.csv is not None:
        table = evaluation_table(cases)
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.csv, index=False)
        print(f"Wrote: {args.csv}")


if __name__ == "__main__":
    main()
