"""Live-data readiness report for the Ascend Optimizer MVP.

This command answers a practical question before we add more integrations:
which strategies are already usable by the optimizer, and exactly which live or
modelled inputs are still missing?

It combines the latest live snapshot for each strategy with the Exposure Engine
and reports return readiness separately from risk/exposure readiness.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data_loader import load_snapshots, load_strategies
from .exposure_engine import build_exposure_table, latest_snapshot_rows


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIVE_PATH = PROJECT_ROOT / "data" / "live_strategy_snapshots.csv"


def _has_value(value: object) -> bool:
    return value is not None and not pd.isna(value)


def build_readiness_table(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
) -> pd.DataFrame:
    """Build one latest-state readiness row for every frozen strategy."""

    latest = latest_snapshot_rows(snapshots)
    latest_by_id = {
        str(row["strategy_id"]): row
        for _, row in latest.iterrows()
    }

    exposure = build_exposure_table(strategies, snapshots)
    exposure_by_id = exposure.set_index("strategy_id", drop=False)

    rows: list[dict[str, object]] = []

    for _, strategy in strategies.iterrows():
        strategy_id = str(strategy["strategy_id"])
        snapshot = latest_by_id.get(strategy_id)

        if snapshot is None:
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "execution_status": strategy["execution_status"],
                    "data_status": "MISSING",
                    "gross_apr": pd.NA,
                    "gross_apy": pd.NA,
                    "incentive_apy": pd.NA,
                    "return_ready": False,
                    "optimizer_eligible": False,
                    "missing_exposures": "no_live_snapshot",
                    "next_gap": "collect_or_model_snapshot",
                }
            )
            continue

        exposure_row = exposure_by_id.loc[strategy_id]

        technical_eligibility = str(
            strategy["technical_eligibility"]
        )
        embedded_explanatory = (
            technical_eligibility == "EXCLUDED_EMBEDDED"
        )

        base_yield_ready = (
            not embedded_explanatory
            and (
                _has_value(snapshot.get("gross_apy"))
                or _has_value(snapshot.get("gross_apr"))
            )
        )

        yield_fee_status = str(snapshot.get("yield_fee_status"))
        protocol_fee = snapshot.get("protocol_fee_rate")
        unresolved_fee_basis = (
            yield_fee_status == "UNKNOWN"
            and _has_value(protocol_fee)
            and float(protocol_fee) > 0
        )

        return_ready = base_yield_ready and not unresolved_fee_basis

        missing = str(exposure_row["missing_exposures"] or "")
        if embedded_explanatory:
            next_gap = "technical_eligibility"
        elif not return_ready:
            if not base_yield_ready:
                next_gap = "yield"
            else:
                next_gap = "yield_fee_status"
        elif missing:
            next_gap = missing.split("|", 1)[0]
        elif not bool(exposure_row["technical_eligible"]):
            next_gap = "technical_eligibility"
        else:
            next_gap = "ready"

        rows.append(
            {
                "strategy_id": strategy_id,
                "execution_status": strategy["execution_status"],
                "data_status": snapshot["data_status"],
                "gross_apr": (
                    pd.NA
                    if embedded_explanatory
                    else snapshot.get("gross_apr")
                ),
                "gross_apy": (
                    pd.NA
                    if embedded_explanatory
                    else snapshot.get("gross_apy")
                ),
                "incentive_apy": (
                    pd.NA
                    if embedded_explanatory
                    else snapshot.get("incentive_apy")
                ),
                "return_ready": return_ready,
                "optimizer_eligible": bool(exposure_row["optimizer_eligible"])
                and return_ready,
                "missing_exposures": missing,
                "next_gap": next_gap,
            }
        )

    return pd.DataFrame(rows)


def _format_percent(value: object) -> str:
    if not _has_value(value):
        return "-"
    return f"{float(value):.2%}"


def print_readiness_report(table: pd.DataFrame) -> None:
    """Print a concise terminal report."""

    print("Ascend Optimizer MVP - live readiness report")
    print()

    for _, row in table.iterrows():
        print(
            f"{row['strategy_id']:<24} "
            f"return={'YES' if row['return_ready'] else 'NO ':<3} "
            f"optimizer={'YES' if row['optimizer_eligible'] else 'NO ':<3} "
            f"APR={_format_percent(row['gross_apr']):>8} "
            f"APY={_format_percent(row['gross_apy']):>8} "
            f"incentive={_format_percent(row['incentive_apy']):>8}"
        )
        print(
            f"  data={row['data_status']}; "
            f"next_gap={row['next_gap']}; "
            f"missing={row['missing_exposures'] or '-'}"
        )

    ready_count = int(table["optimizer_eligible"].sum())
    return_ready_count = int(table["return_ready"].sum())

    print()
    print(
        f"Return-ready strategies: {return_ready_count}/{len(table)}; "
        f"optimizer-ready strategies: {ready_count}/{len(table)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show live strategy readiness and remaining data gaps."
    )
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=DEFAULT_LIVE_PATH,
        help="Snapshot CSV to inspect.",
    )
    args = parser.parse_args()

    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")

    if not args.snapshots.exists():
        raise SystemExit(
            f"Live snapshot file not found: {args.snapshots}. "
            "Run the collectors first."
        )

    snapshots = load_snapshots(strategies, args.snapshots)
    table = build_readiness_table(strategies, snapshots)
    print_readiness_report(table)


if __name__ == "__main__":
    main()
