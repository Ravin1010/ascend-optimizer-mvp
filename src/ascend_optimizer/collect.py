"""CLI for collecting the first live optimizer strategy snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .collectors.common import CollectionError
from .collectors.gimo import collect_gimo_snapshot
from .collectors.native_staking import collect_native_staking_snapshot
from .data_loader import SNAPSHOT_COLUMNS, load_strategies, validate_snapshots


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def collect_rows(collector: str = "all") -> list[dict[str, object]]:
    """Run selected live collectors."""

    rows: list[dict[str, object]] = []

    if collector in {"all", "native"}:
        rows.append(collect_native_staking_snapshot())

    if collector in {"all", "gimo"}:
        rows.append(collect_gimo_snapshot())

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect live Native 0G / Gimo snapshot rows."
    )
    parser.add_argument(
        "--collector",
        choices=("all", "native", "gimo"),
        default="all",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "live_strategy_snapshots.csv",
    )
    args = parser.parse_args()

    try:
        rows = collect_rows(args.collector)
    except CollectionError as exc:
        raise SystemExit(f"Collection failed: {exc}") from exc

    frame = pd.DataFrame(rows, columns=SNAPSHOT_COLUMNS)

    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    validated = validate_snapshots(frame.astype("string"), strategies)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Preserve the human-readable raw values rather than pandas extension dtypes.
    frame.to_csv(args.output, index=False)

    print(f"Collected {len(frame)} strategy snapshot row(s).")
    print(f"Validated {len(validated)} row(s) against the frozen schema.")
    print(f"Wrote: {args.output}")

    for _, row in frame.iterrows():
        print(
            f"- {row['strategy_id']}: "
            f"APR={row['gross_apr']!r}, APY={row['gross_apy']!r}, "
            f"status={row['data_status']}"
        )


if __name__ == "__main__":
    main()
