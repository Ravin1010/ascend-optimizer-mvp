"""Dataset loading and schema validation for the Ascend Optimizer MVP.

The module keeps the optimizer's two input datasets deliberately separate:

* strategies.csv stores relatively static strategy metadata.
* strategy_snapshots.csv stores timestamped or staged observations used by
  the return and exposure engines.

Unknown values are allowed where the capstone has not yet collected or verified
live data, but malformed values and schema drift fail fast with a clear error.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


class SchemaValidationError(ValueError):
    """Raised when an optimizer input dataset violates its frozen schema."""


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

STRATEGY_COLUMNS = (
    "strategy_id",
    "strategy_name",
    "category",
    "protocol",
    "network",
    "chain_id",
    "input_asset",
    "output_asset",
    "execution_status",
    "contract_or_pool_id",
    "bridge_required",
    "bridge_fraction",
    "reward_model",
    "exit_model",
    "data_source",
    "technical_eligibility",
    "notes",
)

SNAPSHOT_COLUMNS = (
    "timestamp",
    "strategy_id",
    "gross_apr",
    "gross_apy",
    "incentive_apy",
    "yield_fee_status",
    "tvl_usd",
    "liquidity_usd",
    "volume_24h_usd",
    "protocol_fee_rate",
    "gas_cost_usd",
    "bridge_cost_usd",
    "deposit_cost_usd",
    "withdrawal_cost_usd",
    "entry_slippage_rate",
    "exit_slippage_rate",
    "exit_time_days",
    "slashing_stress_loss",
    "bridge_fraction",
    "lp_stress_loss_20pct",
    "data_status",
    "source",
    "notes",
)

STRATEGY_EXECUTION_STATUSES = frozenset(
    {
        "LIVE",
        "LIVE_INCOMPLETE",
        "MODELLED",
        "PARTIAL_MODELLED",
        "PENDING",
    }
)

BRIDGE_REQUIRED_VALUES = frozenset({"TRUE", "FALSE", "UNKNOWN"})

YIELD_FEE_STATUSES = frozenset(
    {
        "GROSS_BEFORE_FEES",
        "NET_OF_PROTOCOL_FEES",
        "UNKNOWN",
    }
)

SNAPSHOT_DATA_STATUSES = frozenset(
    {
        "LIVE",
        "LIVE_NOT_COLLECTED",
        "LIVE_INCOMPLETE",
        "MODELLED",
        "PARTIAL_MODELLED",
        "PENDING",
    }
)

STRATEGY_NUMERIC_COLUMNS = ("bridge_fraction",)

SNAPSHOT_NUMERIC_COLUMNS = (
    "gross_apr",
    "gross_apy",
    "incentive_apy",
    "tvl_usd",
    "liquidity_usd",
    "volume_24h_usd",
    "protocol_fee_rate",
    "gas_cost_usd",
    "bridge_cost_usd",
    "deposit_cost_usd",
    "withdrawal_cost_usd",
    "entry_slippage_rate",
    "exit_slippage_rate",
    "exit_time_days",
    "slashing_stress_loss",
    "bridge_fraction",
    "lp_stress_loss_20pct",
)

NON_NEGATIVE_SNAPSHOT_COLUMNS = (
    "gross_apr",
    "gross_apy",
    "incentive_apy",
    "tvl_usd",
    "liquidity_usd",
    "volume_24h_usd",
    "gas_cost_usd",
    "bridge_cost_usd",
    "deposit_cost_usd",
    "withdrawal_cost_usd",
    "exit_time_days",
)

FRACTION_COLUMNS = (
    "protocol_fee_rate",
    "entry_slippage_rate",
    "exit_slippage_rate",
    "slashing_stress_loss",
    "bridge_fraction",
    "lp_stress_loss_20pct",
)


@dataclass(frozen=True)
class DatasetBundle:
    """Validated optimizer datasets ready for downstream engines."""

    strategies: pd.DataFrame
    snapshots: pd.DataFrame

    @property
    def strategy_count(self) -> int:
        return len(self.strategies)

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)


def _read_csv(path: Path, dataset_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{dataset_name} dataset not found: {path}")

    try:
        # String-first loading prevents pandas from silently changing IDs or
        # categorical values before validation. Numeric parsing happens below.
        return pd.read_csv(path, dtype="string", keep_default_na=True)
    except pd.errors.EmptyDataError as exc:
        raise SchemaValidationError(f"{dataset_name} is empty: {path}") from exc
    except pd.errors.ParserError as exc:
        raise SchemaValidationError(
            f"{dataset_name} is not valid CSV: {path}"
        ) from exc


def _validate_columns(
    df: pd.DataFrame,
    expected: Iterable[str],
    dataset_name: str,
) -> pd.DataFrame:
    expected_list = list(expected)
    actual = list(df.columns)

    missing = [column for column in expected_list if column not in actual]
    extra = [column for column in actual if column not in expected_list]

    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"missing columns={missing}")
        if extra:
            parts.append(f"unexpected columns={extra}")
        raise SchemaValidationError(f"{dataset_name} schema mismatch: " + "; ".join(parts))

    # Return a deterministic column order even if a CSV was manually reordered.
    return df.loc[:, expected_list].copy()


def _strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in result.columns:
        if pd.api.types.is_string_dtype(result[column].dtype):
            result[column] = result[column].str.strip()
            result[column] = result[column].mask(result[column].eq(""), pd.NA)
    return result


def _require_non_null(
    df: pd.DataFrame,
    columns: Iterable[str],
    dataset_name: str,
) -> None:
    for column in columns:
        mask = df[column].isna()
        if mask.any():
            rows = [int(index) + 2 for index in df.index[mask]]
            raise SchemaValidationError(
                f"{dataset_name}.{column} is required; blank at CSV row(s) {rows}"
            )


def _validate_allowed_values(
    df: pd.DataFrame,
    column: str,
    allowed: frozenset[str],
    dataset_name: str,
    *,
    allow_null: bool = False,
) -> None:
    series = df[column]
    if not allow_null and series.isna().any():
        rows = [int(index) + 2 for index in df.index[series.isna()]]
        raise SchemaValidationError(
            f"{dataset_name}.{column} is required; blank at CSV row(s) {rows}"
        )

    invalid_mask = series.notna() & ~series.isin(allowed)
    if invalid_mask.any():
        invalid = sorted(series[invalid_mask].astype(str).unique().tolist())
        rows = [int(index) + 2 for index in df.index[invalid_mask]]
        raise SchemaValidationError(
            f"{dataset_name}.{column} contains invalid value(s) {invalid} "
            f"at CSV row(s) {rows}; allowed={sorted(allowed)}"
        )


def _coerce_numeric(
    df: pd.DataFrame,
    columns: Iterable[str],
    dataset_name: str,
) -> pd.DataFrame:
    result = df.copy()

    for column in columns:
        original = result[column]
        converted = pd.to_numeric(original, errors="coerce")

        invalid_mask = original.notna() & converted.isna()
        if invalid_mask.any():
            values = sorted(original[invalid_mask].astype(str).unique().tolist())
            rows = [int(index) + 2 for index in result.index[invalid_mask]]
            raise SchemaValidationError(
                f"{dataset_name}.{column} must be numeric when provided; "
                f"invalid value(s) {values} at CSV row(s) {rows}"
            )

        result[column] = converted.astype("Float64")

    return result


def _validate_non_negative(
    df: pd.DataFrame,
    columns: Iterable[str],
    dataset_name: str,
) -> None:
    for column in columns:
        invalid_mask = df[column].notna() & (df[column] < 0)
        if invalid_mask.any():
            rows = [int(index) + 2 for index in df.index[invalid_mask]]
            raise SchemaValidationError(
                f"{dataset_name}.{column} must be >= 0 at CSV row(s) {rows}"
            )


def _validate_fraction(
    df: pd.DataFrame,
    column: str,
    dataset_name: str,
) -> None:
    invalid_mask = df[column].notna() & ((df[column] < 0) | (df[column] > 1))
    if invalid_mask.any():
        rows = [int(index) + 2 for index in df.index[invalid_mask]]
        raise SchemaValidationError(
            f"{dataset_name}.{column} must be between 0 and 1 "
            f"at CSV row(s) {rows}"
        )


def _validate_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    original = result["timestamp"]

    # Blank timestamps are intentionally allowed while a strategy is only a
    # scaffold/model row. Any timestamp that is supplied must be parseable.
    parsed = pd.to_datetime(original, errors="coerce", utc=True)
    invalid_mask = original.notna() & parsed.isna()

    if invalid_mask.any():
        values = sorted(original[invalid_mask].astype(str).unique().tolist())
        rows = [int(index) + 2 for index in result.index[invalid_mask]]
        raise SchemaValidationError(
            "strategy_snapshots.timestamp contains unparseable value(s) "
            f"{values} at CSV row(s) {rows}"
        )

    result["timestamp"] = parsed
    return result


def validate_strategies(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the static strategy metadata dataset."""

    result = _validate_columns(df, STRATEGY_COLUMNS, "strategies")
    result = _strip_strings(result)

    _require_non_null(
        result,
        (
            "strategy_id",
            "strategy_name",
            "category",
            "protocol",
            "network",
            "input_asset",
            "output_asset",
            "execution_status",
            "bridge_required",
            "reward_model",
            "exit_model",
            "data_source",
            "technical_eligibility",
        ),
        "strategies",
    )

    duplicate_mask = result["strategy_id"].duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_ids = sorted(
            result.loc[duplicate_mask, "strategy_id"].astype(str).unique().tolist()
        )
        raise SchemaValidationError(
            f"strategies.strategy_id must be unique; duplicates={duplicate_ids}"
        )

    _validate_allowed_values(
        result,
        "execution_status",
        STRATEGY_EXECUTION_STATUSES,
        "strategies",
    )
    _validate_allowed_values(
        result,
        "bridge_required",
        BRIDGE_REQUIRED_VALUES,
        "strategies",
    )

    result = _coerce_numeric(result, STRATEGY_NUMERIC_COLUMNS, "strategies")
    _validate_fraction(result, "bridge_fraction", "strategies")

    # A route explicitly marked as not requiring a bridge must not carry
    # non-zero bridge exposure in its static metadata.
    no_bridge = result["bridge_required"].eq("FALSE")
    inconsistent = (
        no_bridge
        & result["bridge_fraction"].notna()
        & result["bridge_fraction"].ne(0)
    )
    if inconsistent.any():
        rows = [int(index) + 2 for index in result.index[inconsistent]]
        raise SchemaValidationError(
            "strategies.bridge_fraction must be 0 when bridge_required=FALSE "
            f"at CSV row(s) {rows}"
        )

    return result


def validate_snapshots(
    df: pd.DataFrame,
    strategies: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and normalize the dynamic strategy snapshot dataset."""

    result = _validate_columns(df, SNAPSHOT_COLUMNS, "strategy_snapshots")
    result = _strip_strings(result)

    _require_non_null(
        result,
        ("strategy_id", "yield_fee_status", "data_status", "source"),
        "strategy_snapshots",
    )

    _validate_allowed_values(
        result,
        "yield_fee_status",
        YIELD_FEE_STATUSES,
        "strategy_snapshots",
    )
    _validate_allowed_values(
        result,
        "data_status",
        SNAPSHOT_DATA_STATUSES,
        "strategy_snapshots",
    )

    known_strategy_ids = set(strategies["strategy_id"].dropna().astype(str))
    snapshot_strategy_ids = set(result["strategy_id"].dropna().astype(str))
    unknown_ids = sorted(snapshot_strategy_ids - known_strategy_ids)
    if unknown_ids:
        raise SchemaValidationError(
            "strategy_snapshots contains strategy_id values not present in "
            f"strategies.csv: {unknown_ids}"
        )

    result = _coerce_numeric(
        result,
        SNAPSHOT_NUMERIC_COLUMNS,
        "strategy_snapshots",
    )
    result = _validate_timestamp(result)

    _validate_non_negative(
        result,
        NON_NEGATIVE_SNAPSHOT_COLUMNS,
        "strategy_snapshots",
    )

    for column in FRACTION_COLUMNS:
        _validate_fraction(result, column, "strategy_snapshots")

    return result


def load_strategies(path: Path | str | None = None) -> pd.DataFrame:
    """Load, validate, and normalize strategies.csv."""

    resolved_path = Path(path) if path is not None else DEFAULT_DATA_DIR / "strategies.csv"
    return validate_strategies(_read_csv(resolved_path, "strategies"))


def load_snapshots(
    strategies: pd.DataFrame,
    path: Path | str | None = None,
) -> pd.DataFrame:
    """Load, validate, and normalize strategy_snapshots.csv."""

    resolved_path = (
        Path(path)
        if path is not None
        else DEFAULT_DATA_DIR / "strategy_snapshots.csv"
    )
    return validate_snapshots(
        _read_csv(resolved_path, "strategy_snapshots"),
        strategies,
    )


def load_datasets(data_dir: Path | str | None = None) -> DatasetBundle:
    """Load and validate both frozen optimizer datasets.

    Parameters
    ----------
    data_dir:
        Directory containing strategies.csv and strategy_snapshots.csv.
        Defaults to the repository data directory.
    """

    directory = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    strategies = load_strategies(directory / "strategies.csv")
    snapshots = load_snapshots(
        strategies,
        directory / "strategy_snapshots.csv",
    )
    return DatasetBundle(strategies=strategies, snapshots=snapshots)
