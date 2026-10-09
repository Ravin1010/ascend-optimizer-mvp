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


# Iteration 10 metadata dimensions; legacy engine columns above remain intact.
STRATEGY_METADATA_VALUES = {
    "record_role": frozenset({"INDEPENDENT_STRATEGY", "EMBEDDED_DEPENDENCY", "OBSERVED_OPPORTUNITY"}),
    "reconciliation_category": frozenset({"INTEGRATED_ALLOCATABLE", "INTEGRATED_GATED", "EMBEDDED_NON_ALLOCATABLE", "OBSERVED_EXCLUDED"}),
    "protocol_availability": frozenset({"LIVE", "DEPLOYED_MARKET_UNRESOLVED"}),
    "integration_status": frozenset({"IMPLEMENTED", "EMBEDDED", "NOT_INTEGRATED"}),
    "optimizer_universe": frozenset({"TRUE", "FALSE"}),
    "allocation_gate": frozenset({"CONDITIONAL", "CLOSED", "NOT_APPLICABLE"}),
    "evidence_readiness": frozenset({"NOT_ASSESSED", "INCOMPLETE", "NOT_APPLICABLE"}),
    "runtime_feasibility": frozenset({"NOT_ASSESSED", "NOT_APPLICABLE"}),
    "live_capstone_proof": frozenset({"NOT_ESTABLISHED", "NOT_APPLICABLE"}),
    "user_bridge_required": frozenset({"TRUE", "FALSE", "UNKNOWN"}),
    "protocol_managed_remote_exposure": frozenset({"TRUE", "FALSE", "UNKNOWN"}),
}
STRATEGY_COLUMNS += (
    "record_role", "reconciliation_category", "protocol_availability",
    "integration_status", "optimizer_universe", "allocation_gate",
    "gate_requirements", "evidence_readiness", "runtime_feasibility",
    "live_capstone_proof", "execution_chain_id", "dependency_chain_ids",
    "parent_strategy_id", "internal_assets", "position_asset",
    "user_bridge_required", "protocol_managed_remote_exposure",
    "legacy_liquidity_meaning", "capital_path",
)
MVP_STRATEGY_IDS = frozenset({
    "NATIVE_STAKE_0G", "GIMO_STAKE_0G", "JAINE_LP_0G_USDC",
    "OKU_LP_0G_USDC", "ASCEND_STAKE_A0G",
})
SOURCE_REGISTRY_COLUMNS = (
    "source_id", "strategy_id", "field_group", "source_type", "source_url",
    "retrieval_method", "authority", "confidence", "last_verified_utc", "notes",
    "chain_ids", "source_role", "mechanism_evidence_class", "freshness_class",
    "amount_specific", "config_specific", "history_required", "capture_status",
)
TRACKED_RECORD_COLUMNS = (
    "record_id", "record_name", "reconciliation_category", "protocol_availability",
    "integration_status", "optimizer_universe", "allocation_gate",
    "parent_strategy_id", "chain_role", "chain_ids", "asset_role",
    "source_coverage", "notes",
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

    _validate_strategy_metadata(result)
    return result


def _validate_strategy_metadata(result: pd.DataFrame) -> None:
    for column, values in STRATEGY_METADATA_VALUES.items():
        _validate_allowed_values(result, column, values, "strategies")
    _require_non_null(result, (
        "gate_requirements", "position_asset", "legacy_liquidity_meaning", "capital_path",
    ), "strategies")
    members = result["optimizer_universe"].eq("TRUE")
    if set(result.loc[members, "strategy_id"]) != MVP_STRATEGY_IDS:
        raise SchemaValidationError("strategies must retain exactly the five MVP optimizer-universe IDs")
    if not result.loc[members, "record_role"].eq("INDEPENDENT_STRATEGY").all():
        raise SchemaValidationError("optimizer-universe members must be independent strategies")
    if not result.loc[members, "integration_status"].eq("IMPLEMENTED").all():
        raise SchemaValidationError("MVP strategies must be implemented")
    if not result.loc[members, "execution_chain_id"].eq("16661").all():
        raise SchemaValidationError("MVP execution chain must be 16661")
    if not result.loc[members, "input_asset"].eq("0G").all():
        raise SchemaValidationError("configured MVP input must remain native 0G")
    for _, row in result.iterrows():
        sid = str(row["strategy_id"])
        expected_category = (
            "INTEGRATED_GATED" if sid == "ASCEND_STAKE_A0G" else
            "INTEGRATED_ALLOCATABLE" if sid in MVP_STRATEGY_IDS else
            "EMBEDDED_NON_ALLOCATABLE" if row["record_role"] == "EMBEDDED_DEPENDENCY" else
            "OBSERVED_EXCLUDED"
        )
        expected_gate = "CLOSED" if sid == "ASCEND_STAKE_A0G" else "CONDITIONAL" if sid in MVP_STRATEGY_IDS else "NOT_APPLICABLE"
        if row["reconciliation_category"] != expected_category or row["allocation_gate"] != expected_gate:
            raise SchemaValidationError(f"strategies.{sid} category/gate contradicts frozen universe")
        # Legacy labels are compatibility inputs, not authority over gates.
        if row["record_role"] == "EMBEDDED_DEPENDENCY":
            if pd.isna(row["parent_strategy_id"]) or row["parent_strategy_id"] not in MVP_STRATEGY_IDS:
                raise SchemaValidationError("embedded dependency requires an MVP parent_strategy_id")
        for field in ("execution_chain_id", "dependency_chain_ids"):
            if pd.notna(row[field]) and not all(part.isdigit() and int(part) > 0 for part in str(row[field]).split("|")):
                raise SchemaValidationError(f"strategies.{field} must contain positive chain IDs")


def _validate_reference_ids(df: pd.DataFrame, column: str, known_ids: set[str], name: str) -> None:
    for value in df[column].dropna():
        if not set(str(value).split("|")) <= known_ids:
            raise SchemaValidationError(f"{name}.{column} contains unknown reference: {value}")


def load_tracked_records(path: Path | str | None = None, *, strategies: pd.DataFrame | None = None) -> pd.DataFrame:
    """Load non-candidate inventory separately; never append it to optimizer datasets."""
    result = _strip_strings(_validate_columns(
        _read_csv(Path(path) if path is not None else DEFAULT_DATA_DIR / "tracked_records.csv", "tracked_records"),
        TRACKED_RECORD_COLUMNS, "tracked_records",
    ))
    _require_non_null(result, [c for c in TRACKED_RECORD_COLUMNS if c not in {"parent_strategy_id", "chain_ids"}], "tracked_records")
    if result["record_id"].duplicated().any():
        raise SchemaValidationError("tracked_records.record_id must be unique")
    for column, values in {
        "reconciliation_category": {"OBSERVED_EXCLUDED", "AUXILIARY_NOT_STRATEGY", "KIV_FUTURE"},
        "protocol_availability": {"LIVE", "OBSERVED", "UNKNOWN", "NOT_APPLICABLE"},
        "integration_status": {"NOT_INTEGRATED", "EXECUTION_HELPER", "REFERENCE_ONLY"},
        "optimizer_universe": {"FALSE"}, "allocation_gate": {"NOT_APPLICABLE"},
        "source_coverage": {"GAP", "EXISTING_REPOSITORY_REFERENCE"},
    }.items():
        _validate_allowed_values(result, column, frozenset(values), "tracked_records")
    known = set((load_strategies() if strategies is None else strategies)["strategy_id"])
    if set(result["record_id"]) & known:
        raise SchemaValidationError("tracked_records IDs must not duplicate strategy IDs")
    _validate_reference_ids(result, "parent_strategy_id", known, "tracked_records")
    for value in result["chain_ids"].dropna():
        if not all(part.isdigit() and int(part) > 0 for part in str(value).split("|")):
            raise SchemaValidationError("tracked_records.chain_ids must contain positive chain IDs")
    return result


def load_source_registry(path: Path | str | None = None, *, strategies: pd.DataFrame | None = None) -> pd.DataFrame:
    """Validate mechanism provenance without asserting freshness of any capture."""
    result = _strip_strings(_validate_columns(
        _read_csv(Path(path) if path is not None else DEFAULT_DATA_DIR / "source_registry.csv", "source_registry"),
        SOURCE_REGISTRY_COLUMNS, "source_registry",
    ))
    _require_non_null(result, [c for c in SOURCE_REGISTRY_COLUMNS if c != "last_verified_utc"], "source_registry")
    if result["source_id"].duplicated().any():
        raise SchemaValidationError("source_registry.source_id must be unique")
    known = set((load_strategies() if strategies is None else strategies)["strategy_id"])
    _validate_reference_ids(result, "strategy_id", known, "source_registry")
    for column, values in {
        "mechanism_evidence_class": {"LIVE_OBSERVED", "LIVE_DERIVED", "HISTORICAL", "MODELLED", "STATIC_CONFIG", "MISSING/UNRESOLVED"},
        "freshness_class": {"RUN_TIME_FRESH", "PERIODICALLY_FRESH", "TIME_SERIES_REQUIRED", "DEPLOYMENT_CONFIG_STATIC", "PROTOCOL_STATIC", "MODEL_ASSUMPTION"},
        "amount_specific": {"TRUE", "FALSE"}, "config_specific": {"TRUE", "FALSE"},
        "history_required": {"TRUE", "FALSE"}, "capture_status": {"NO_FRESH_CAPTURE_SUPPLIED"},
        "confidence": {"HIGH", "MEDIUM", "LOW"},
        "source_role": {"PROTOCOL_REFERENCE", "MARKET_OBSERVATION", "RETURN_HISTORY", "EXECUTION_QUOTE", "WITHDRAWAL_STATE", "INCENTIVE_OBSERVATION", "DEPENDENCY_REFERENCE", "MODEL_ASSUMPTION"},
    }.items():
        _validate_allowed_values(result, column, frozenset(values), "source_registry")
    for value in result["chain_ids"]:
        if not all(part.isdigit() and int(part) > 0 for part in str(value).split("|")):
            raise SchemaValidationError("source_registry.chain_ids must contain positive chain IDs")
    dates = pd.to_datetime(result["last_verified_utc"], format="ISO8601", errors="coerce", utc=True)
    if (result["last_verified_utc"].notna() & dates.isna()).any():
        raise SchemaValidationError("source_registry.last_verified_utc must be parseable when supplied")
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
