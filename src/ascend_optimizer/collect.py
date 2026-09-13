"""CLI for collecting live optimizer strategy snapshots.

Each successful run appends timestamped observations to the output CSV. A failed
collector leaves the existing output file untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .collectors.common import CollectionError
from .collectors.gimo import collect_gimo_snapshot
from .collectors.jaine import collect_jaine_snapshot
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

    if collector in {"all", "jaine"}:
        rows.append(collect_jaine_snapshot())

    return rows


def append_snapshot_rows(
    output: Path,
    frame: pd.DataFrame,
    *,
    strategies: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Append new observations and validate the complete time-series file."""

    if output.exists():
        existing = pd.read_csv(
            output,
            dtype="string",
            keep_default_na=True,
        )
        existing = existing.loc[:, list(SNAPSHOT_COLUMNS)]
        combined = pd.concat(
            [existing, frame.astype("string")],
            ignore_index=True,
        )
    else:
        combined = frame.astype("string")

    validated = validate_snapshots(combined, strategies)
    return combined, validated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect live Native 0G / Gimo / Jaine snapshot rows."
    )
    parser.add_argument(
        "--collector",
        choices=("all", "native", "gimo", "jaine"),
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    combined, validated = append_snapshot_rows(
        args.output,
        frame,
        strategies=strategies,
    )

    # Write only after successful validation, so a failed validation cannot
    # corrupt an existing time-series file.
    combined.to_csv(args.output, index=False)

    print(f"Collected {len(frame)} new strategy snapshot row(s).")
    print(f"Validated {len(validated)} total row(s) against the frozen schema.")
    print(f"Wrote: {args.output}")

    for _, row in frame.iterrows():
        print(
            f"- {row['strategy_id']}: "
            f"APR={row['gross_apr']!r}, APY={row['gross_apy']!r}, "
            f"status={row['data_status']}"
        )


if __name__ == "__main__":
    main()
