"""Strategy exposure extraction for the Ascend Optimizer MVP.

The exposure engine deliberately avoids a synthetic 0-100 risk score. It
produces measurable strategy-level quantities that the portfolio optimizer can
constrain directly:

* entry and exit slippage;
* exit time;
* bridge exposure;
* slashing stress loss;
* LP +/-20% price-move stress;
* usable liquidity capacity;
* technical/data eligibility.

Missing measurements are surfaced explicitly rather than silently replaced with
made-up defaults. Only exposures that are structurally not applicable are set
to zero (for example LP stress for a non-LP strategy).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


PENDING_EXECUTION_STATUSES = frozenset({"PENDING"})
EXCLUDED_TECHNICAL_PREFIXES = ("EXCLUDED",)

LP_CATEGORIES = frozenset({"LIQUIDITY_PROVISION"})
SLASHING_CATEGORIES = frozenset(
    {
        "STAKING",
        "ASCEND_STAKING",
        "RESTAKING",
    }
)

# These are the measurements required before the optimizer may allocate capital.
# Some fields can become structurally zero depending on strategy metadata.
OPTIMIZER_REQUIRED_FIELDS = (
    "liquidity_usd",
    "entry_slippage_rate",
    "exit_slippage_rate",
    "exit_time_days",
    "slashing_stress_loss",
    "bridge_fraction",
    "lp_stress_loss_20pct",
)


@dataclass(frozen=True)
class StrategyExposure:
    """Measured exposures and eligibility state for one strategy."""

    strategy_id: str
    category: str
    execution_status: str
    technical_eligibility: str
    data_status: str

    liquidity_usd: float | None
    entry_slippage_rate: float | None
    exit_slippage_rate: float | None
    exit_time_days: float | None
    slashing_stress_loss: float | None
    bridge_fraction: float | None
    lp_stress_loss_20pct: float | None

    technical_eligible: bool
    risk_data_complete: bool
    optimizer_eligible: bool

    missing_exposures: tuple[str, ...]
    eligibility_reasons: tuple[str, ...]

    @property
    def max_entry_exit_slippage(self) -> float | None:
        """Return the worse of entry/exit slippage when both are known."""

        if self.entry_slippage_rate is None or self.exit_slippage_rate is None:
            return None
        return max(self.entry_slippage_rate, self.exit_slippage_rate)


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _required_string(row: pd.Series | dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None or pd.isna(value):
        raise ValueError(f"{key} is required to build a strategy exposure")
    return str(value)


def _resolve_bridge_fraction(
    strategy: pd.Series | dict[str, Any],
    snapshot: pd.Series | dict[str, Any],
) -> float | None:
    """Resolve bridge exposure from dynamic data then static metadata."""

    snapshot_value = _optional_float(snapshot.get("bridge_fraction"))
    if snapshot_value is not None:
        return snapshot_value

    bridge_required = _required_string(strategy, "bridge_required")

    # Structural zero: a route explicitly marked as not using a bridge has no
    # bridge exposure even if the snapshot omits the field.
    if bridge_required == "FALSE":
        return 0.0

    return _optional_float(strategy.get("bridge_fraction"))


def _resolve_slashing_stress(
    category: str,
    snapshot: pd.Series | dict[str, Any],
) -> float | None:
    """Return zero when slashing is structurally not applicable."""

    if category not in SLASHING_CATEGORIES:
        return 0.0
    return _optional_float(snapshot.get("slashing_stress_loss"))


def _resolve_lp_stress(
    category: str,
    snapshot: pd.Series | dict[str, Any],
) -> float | None:
    """Return zero when LP impermanent-loss stress is not applicable."""

    if category not in LP_CATEGORIES:
        return 0.0
    return _optional_float(snapshot.get("lp_stress_loss_20pct"))


def _technical_eligibility(
    execution_status: str,
    technical_eligibility: str,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []

    if execution_status in PENDING_EXECUTION_STATUSES:
        reasons.append(f"execution_status={execution_status}")

    if technical_eligibility.startswith(EXCLUDED_TECHNICAL_PREFIXES):
        reasons.append(f"technical_eligibility={technical_eligibility}")

    return not reasons, tuple(reasons)


def build_strategy_exposure(
    strategy: pd.Series | dict[str, Any],
    snapshot: pd.Series | dict[str, Any],
) -> StrategyExposure:
    """Build one exposure record from validated metadata and snapshot rows."""

    strategy_id = _required_string(strategy, "strategy_id")
    snapshot_strategy_id = _required_string(snapshot, "strategy_id")

    if snapshot_strategy_id != strategy_id:
        raise ValueError(
            "strategy/snapshot mismatch: "
            f"{strategy_id!r} != {snapshot_strategy_id!r}"
        )

    category = _required_string(strategy, "category")
    execution_status = _required_string(strategy, "execution_status")
    technical_eligibility = _required_string(strategy, "technical_eligibility")
    data_status = _required_string(snapshot, "data_status")

    technical_eligible, eligibility_reasons = _technical_eligibility(
        execution_status,
        technical_eligibility,
    )

    values = {
        "liquidity_usd": _optional_float(snapshot.get("liquidity_usd")),
        "entry_slippage_rate": _optional_float(
            snapshot.get("entry_slippage_rate")
        ),
        "exit_slippage_rate": _optional_float(
            snapshot.get("exit_slippage_rate")
        ),
        "exit_time_days": _optional_float(snapshot.get("exit_time_days")),
        "slashing_stress_loss": _resolve_slashing_stress(category, snapshot),
        "bridge_fraction": _resolve_bridge_fraction(strategy, snapshot),
        "lp_stress_loss_20pct": _resolve_lp_stress(category, snapshot),
    }

    missing = tuple(
        field
        for field in OPTIMIZER_REQUIRED_FIELDS
        if values[field] is None
    )
    risk_data_complete = not missing
    optimizer_eligible = technical_eligible and risk_data_complete

    reasons = list(eligibility_reasons)
    if missing:
        reasons.append("missing_exposures=" + ",".join(missing))

    return StrategyExposure(
        strategy_id=strategy_id,
        category=category,
        execution_status=execution_status,
        technical_eligibility=technical_eligibility,
        data_status=data_status,
        liquidity_usd=values["liquidity_usd"],
        entry_slippage_rate=values["entry_slippage_rate"],
        exit_slippage_rate=values["exit_slippage_rate"],
        exit_time_days=values["exit_time_days"],
        slashing_stress_loss=values["slashing_stress_loss"],
        bridge_fraction=values["bridge_fraction"],
        lp_stress_loss_20pct=values["lp_stress_loss_20pct"],
        technical_eligible=technical_eligible,
        risk_data_complete=risk_data_complete,
        optimizer_eligible=optimizer_eligible,
        missing_exposures=missing,
        eligibility_reasons=tuple(reasons),
    )


def latest_snapshot_rows(snapshots: pd.DataFrame) -> pd.DataFrame:
    """Select the latest available snapshot row for each strategy.

    If a strategy has timestamped rows, the newest timestamp wins. If all rows
    for that strategy have a blank timestamp (as in the initial scaffold), the
    final row in file order is used.
    """

    if "strategy_id" not in snapshots.columns or "timestamp" not in snapshots.columns:
        raise ValueError("snapshots must contain strategy_id and timestamp columns")

    selected: list[pd.Series] = []

    for _, group in snapshots.groupby("strategy_id", sort=False):
        timestamped = group[group["timestamp"].notna()]
        if not timestamped.empty:
            index = timestamped["timestamp"].idxmax()
            selected.append(group.loc[index])
        else:
            selected.append(group.iloc[-1])

    if not selected:
        return snapshots.iloc[0:0].copy()

    return pd.DataFrame(selected).reset_index(drop=True)


def build_exposures(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
) -> list[StrategyExposure]:
    """Build exposure records using each strategy's latest snapshot."""

    latest = latest_snapshot_rows(snapshots)
    snapshot_by_id = {
        str(row["strategy_id"]): row
        for _, row in latest.iterrows()
    }

    exposures: list[StrategyExposure] = []

    for _, strategy in strategies.iterrows():
        strategy_id = str(strategy["strategy_id"])
        snapshot = snapshot_by_id.get(strategy_id)

        if snapshot is None:
            # A missing snapshot is an explicit data-gap state, not a reason to
            # fabricate zero risk. Build a synthetic empty snapshot only to
            # surface every required exposure as missing.
            snapshot = {
                "strategy_id": strategy_id,
                "data_status": "MISSING",
                "liquidity_usd": None,
                "entry_slippage_rate": None,
                "exit_slippage_rate": None,
                "exit_time_days": None,
                "slashing_stress_loss": None,
                "bridge_fraction": None,
                "lp_stress_loss_20pct": None,
            }

        exposures.append(build_strategy_exposure(strategy, snapshot))

    return exposures


def build_exposure_table(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
) -> pd.DataFrame:
    """Return optimizer-ready exposure records as a dataframe."""

    rows: list[dict[str, Any]] = []

    for exposure in build_exposures(strategies, snapshots):
        row = asdict(exposure)
        row["max_entry_exit_slippage"] = exposure.max_entry_exit_slippage
        row["missing_exposures"] = "|".join(exposure.missing_exposures)
        row["eligibility_reasons"] = "|".join(exposure.eligibility_reasons)
        rows.append(row)

    return pd.DataFrame(rows)
