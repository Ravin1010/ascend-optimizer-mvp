"""Legacy reference model for the pre-launch Ascend design.

Ascend a0G is now a live external protocol and this module MUST NOT be treated
as a source of live Ascend optimizer data. The functions are retained only so
earlier capstone experiments remain reproducible. Production/live optimizer
inputs must come from the live Ascend collector instead.

ASCEND_STAKE_A0G:
* base gross APY inherits the latest Native 0G staking benchmark;
* liquidity/capacity, exit delay, and slashing stress inherit the same underlying
  Native 0G exposure observations;
* Ascend-specific protocol fee and mint/redeem slippage come from the editable
  model-assumption CSV.

ASCEND_RESTAKE:
* base gross APY inherits the modelled Ascend staking APY;
* incremental cash APY defaults to zero until a verified reward distribution is
  available;
* Symbiotic points are deliberately excluded from Net APY;
* route-specific bridge exposure, withdrawal time, and additional restaking
  slashing stress remain unresolved rather than guessed.

The generated rows are appended to the same local snapshot time series so the
existing readiness and optimizer pipeline can inspect them.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .collect import append_snapshot_rows
from .data_loader import (
    SNAPSHOT_COLUMNS,
    load_snapshots,
    load_strategies,
)
from .exposure_engine import latest_snapshot_rows
from .net_return_engine import resolve_base_gross_apy
from .collectors.common import utc_now_iso


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIVE_PATH = PROJECT_ROOT / "data" / "live_strategy_snapshots.csv"
DEFAULT_ASSUMPTIONS_PATH = (
    PROJECT_ROOT / "data" / "ascend_model_assumptions.csv"
)

REQUIRED_ASSUMPTIONS = {
    "ASCEND_STAKE_A0G": {
        "protocol_fee_rate",
        "entry_slippage_rate",
        "exit_slippage_rate",
    },
    "ASCEND_RESTAKE": {
        "incentive_apy",
        "protocol_fee_rate",
        "entry_slippage_rate",
        "exit_slippage_rate",
    },
}


class AscendModelError(ValueError):
    """Raised when Ascend model inputs are missing or inconsistent."""


def load_model_assumptions(path: Path) -> dict[str, dict[str, float]]:
    """Load and validate the editable numeric Ascend model assumptions."""

    frame = pd.read_csv(path, dtype="string")

    required_columns = {
        "strategy_id",
        "parameter",
        "value",
        "status",
    }
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        raise AscendModelError(
            "Assumption file missing columns: "
            + ", ".join(sorted(missing_columns))
        )

    assumptions: dict[str, dict[str, float]] = {}

    for _, row in frame.iterrows():
        strategy_id = str(row["strategy_id"])
        parameter = str(row["parameter"])
        raw_value = row["value"]

        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise AscendModelError(
                f"Invalid numeric assumption {strategy_id}.{parameter}="
                f"{raw_value!r}"
            ) from exc

        if value < 0 or value > 1:
            raise AscendModelError(
                f"Assumption {strategy_id}.{parameter} must be in [0, 1]"
            )

        strategy_values = assumptions.setdefault(strategy_id, {})
        if parameter in strategy_values:
            raise AscendModelError(
                f"Duplicate assumption {strategy_id}.{parameter}"
            )
        strategy_values[parameter] = value

    for strategy_id, required in REQUIRED_ASSUMPTIONS.items():
        actual = set(assumptions.get(strategy_id, {}))
        missing = required.difference(actual)
        if missing:
            raise AscendModelError(
                f"Missing assumptions for {strategy_id}: "
                + ", ".join(sorted(missing))
            )

    return assumptions


def _latest_by_id(snapshots: pd.DataFrame) -> dict[str, pd.Series]:
    latest = latest_snapshot_rows(snapshots)
    return {
        str(row["strategy_id"]): row
        for _, row in latest.iterrows()
    }


def _required_float(row: pd.Series, field: str, strategy_id: str) -> float:
    value = row.get(field)
    if value is None or pd.isna(value):
        raise AscendModelError(
            f"{strategy_id} requires underlying {field!r} before modelling"
        )
    return float(value)


def build_ascend_stake_snapshot(
    native: pd.Series,
    assumptions: dict[str, dict[str, float]],
    *,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build the a0G staking model from the latest Native 0G benchmark."""

    gross_apy = resolve_base_gross_apy(
        gross_apy=(
            None
            if native.get("gross_apy") is None
            or pd.isna(native.get("gross_apy"))
            else float(native.get("gross_apy"))
        ),
        gross_apr=(
            None
            if native.get("gross_apr") is None
            or pd.isna(native.get("gross_apr"))
            else float(native.get("gross_apr"))
        ),
    )

    model = assumptions["ASCEND_STAKE_A0G"]

    liquidity_usd = _required_float(
        native,
        "liquidity_usd",
        "ASCEND_STAKE_A0G",
    )
    exit_time_days = _required_float(
        native,
        "exit_time_days",
        "ASCEND_STAKE_A0G",
    )
    slashing_stress_loss = _required_float(
        native,
        "slashing_stress_loss",
        "ASCEND_STAKE_A0G",
    )

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": "ASCEND_STAKE_A0G",
        "gross_apr": None,
        "gross_apy": gross_apy,
        "incentive_apy": 0.0,
        "yield_fee_status": "GROSS_BEFORE_FEES",
        # Capacity proxy inherits the same sampled underlying delegation depth.
        "tvl_usd": liquidity_usd,
        "liquidity_usd": liquidity_usd,
        "volume_24h_usd": None,
        "protocol_fee_rate": model["protocol_fee_rate"],
        "gas_cost_usd": 0.0,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": 0.0,
        "withdrawal_cost_usd": 0.0,
        "entry_slippage_rate": model["entry_slippage_rate"],
        "exit_slippage_rate": model["exit_slippage_rate"],
        "exit_time_days": exit_time_days,
        "slashing_stress_loss": slashing_stress_loss,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": "MODELLED",
        "source": "ASCEND_MODEL_FROM_NATIVE_0G",
        "notes": (
            "a0G is the Ascend LST capstone concept and is not A0GI; "
            "base APY and underlying exposure inherit latest Native 0G "
            "observations; Ascend fee/mint/redeem inputs come from "
            "data/ascend_model_assumptions.csv; zero-cost values are model "
            "baselines rather than live protocol measurements"
        ),
    }


def build_ascend_restake_snapshot(
    ascend_stake: dict[str, object],
    assumptions: dict[str, dict[str, float]],
    *,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build partial restaking model without inventing unresolved route risk."""

    model = assumptions["ASCEND_RESTAKE"]

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": "ASCEND_RESTAKE",
        "gross_apr": None,
        "gross_apy": float(ascend_stake["gross_apy"]),
        # Cash-only incremental reward assumption; Symbiotic points excluded.
        "incentive_apy": model["incentive_apy"],
        "yield_fee_status": "GROSS_BEFORE_FEES",
        "tvl_usd": float(ascend_stake["tvl_usd"]),
        "liquidity_usd": float(ascend_stake["liquidity_usd"]),
        "volume_24h_usd": None,
        "protocol_fee_rate": model["protocol_fee_rate"],
        "gas_cost_usd": 0.0,
        "bridge_cost_usd": None,
        "deposit_cost_usd": 0.0,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": model["entry_slippage_rate"],
        "exit_slippage_rate": model["exit_slippage_rate"],
        # Intentionally unresolved until the exact Symbiotic vault/route is
        # fixed. Epoch/delay and slashing conditions are route-specific.
        "exit_time_days": None,
        "slashing_stress_loss": None,
        "bridge_fraction": None,
        "lp_stress_loss_20pct": None,
        "data_status": "PARTIAL_MODELLED",
        "source": "ASCEND_SYMBIOTIC_PARTIAL_MODEL",
        "notes": (
            "Base APY inherits modelled Ascend a0G staking; incremental cash "
            "APY comes from explicit model assumptions and defaults to zero; "
            "Symbiotic points are excluded from Net APY; exact vault route, "
            "bridge fraction, withdrawal delay, and additional restaking "
            "slashing stress remain unresolved rather than guessed"
        ),
    }


def build_ascend_model_rows(
    snapshots: pd.DataFrame,
    assumptions: dict[str, dict[str, float]],
    *,
    timestamp: str | None = None,
) -> list[dict[str, object]]:
    """Build the two Ascend model rows from the latest underlying live state."""

    by_id = _latest_by_id(snapshots)
    native = by_id.get("NATIVE_STAKE_0G")
    if native is None:
        raise AscendModelError(
            "Native 0G snapshot is required before modelling Ascend"
        )

    shared_timestamp = timestamp or utc_now_iso()
    ascend_stake = build_ascend_stake_snapshot(
        native,
        assumptions,
        timestamp=shared_timestamp,
    )
    restake = build_ascend_restake_snapshot(
        ascend_stake,
        assumptions,
        timestamp=shared_timestamp,
    )

    return [ascend_stake, restake]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Legacy pre-launch Ascend model; not valid live input."
    )
    parser.add_argument(
        "--snapshots",
        type=Path,
        default=DEFAULT_LIVE_PATH,
    )
    parser.add_argument(
        "--assumptions",
        type=Path,
        default=DEFAULT_ASSUMPTIONS_PATH,
    )
    args = parser.parse_args()

    raise SystemExit(
        "Ascend a0G is now live. Do not append the legacy model to live "
        "optimizer data; use the live Ascend collector instead."
    )

    if not args.snapshots.exists():
        raise SystemExit(
            f"Snapshot file not found: {args.snapshots}. "
            "Collect Native 0G first."
        )

    strategies = load_strategies(
        PROJECT_ROOT / "data" / "strategies.csv"
    )
    snapshots = load_snapshots(strategies, args.snapshots)

    try:
        assumptions = load_model_assumptions(args.assumptions)
        rows = build_ascend_model_rows(snapshots, assumptions)
    except AscendModelError as exc:
        raise SystemExit(f"Ascend model failed: {exc}") from exc

    frame = pd.DataFrame(rows, columns=SNAPSHOT_COLUMNS)
    combined, validated = append_snapshot_rows(
        args.snapshots,
        frame,
        strategies=strategies,
    )
    combined.to_csv(args.snapshots, index=False)

    print(f"Appended {len(frame)} Ascend model snapshot row(s).")
    print(f"Validated {len(validated)} total row(s) against the frozen schema.")
    print(f"Wrote: {args.snapshots}")

    for _, row in frame.iterrows():
        print(
            f"- {row['strategy_id']}: "
            f"APY={row['gross_apy']!r}, "
            f"incentive_APY={row['incentive_apy']!r}, "
            f"status={row['data_status']}"
        )


if __name__ == "__main__":
    main()
