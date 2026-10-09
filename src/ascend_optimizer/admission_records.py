"""Strict per-capture admission CSV contract. References are not captures.

Malformed data is rejected; explicit unresolved captures are retained but unusable.
This module validates structure/accounting only, never observation-age expiry.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from pathlib import Path
import re

from .data_loader import DEFAULT_DATA_DIR, MVP_STRATEGY_IDS, SchemaValidationError, load_strategies

DEFAULT_ADMISSION_PATH = DEFAULT_DATA_DIR / "admission_evidence.csv"
ADMISSION_COLUMNS = (
    "evidence_id", "strategy_id", "chain_id", "evidence_type", "admission_status",
    "amount_0g", "amount_usd", "scalar_headroom_0g", "scalar_headroom_usd",
    "source_id", "source_role", "mechanism", "evidence_class", "observation_timestamp",
    "retrieval_timestamp", "block_number", "block_hash", "config_identity", "config_required",
    "tested_amount_0g", "tested_amount_usd", "valuation_price_usd", "capture_status", "notes",
)
EVIDENCE_CLASSES = frozenset({"LIVE_OBSERVED", "LIVE_DERIVED", "HISTORICAL", "MODELLED", "STATIC_CONFIG"})
CAPTURE_STATUSES = frozenset({"CAPTURED", "NO_FRESH_CAPTURE_SUPPLIED", "SOURCE_UNVERIFIED", "CONFIG_UNRESOLVED", "INVALID"})
SOURCE_ROLES = {
    "NATIVE_STAKE_0G": "CONFIGURED_VALIDATOR_ADMISSION",
    "GIMO_STAKE_0G": "GIMO_PROTOCOL_ADMISSION",
    "JAINE_LP_0G_USDC": "REGISTERED_LP_ADMISSION",
    "OKU_LP_0G_USDC": "REGISTERED_LP_ADMISSION",
    "ASCEND_STAKE_A0G": "SOURCECORE_ADMISSION",
}
NUMBER_FIELDS = ("amount_0g", "amount_usd", "scalar_headroom_0g", "scalar_headroom_usd",
                 "tested_amount_0g", "tested_amount_usd", "valuation_price_usd")
TIMESTAMP_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})")


def decimal_value(value: str, field: str) -> Decimal | None:
    if value == "":
        return None
    try:
        result = Decimal(value)
        if not result.is_finite() or not isfinite(float(result)) or result < 0:
            raise ValueError()
    except (InvalidOperation, ValueError, OverflowError):
        raise SchemaValidationError(f"{field}: finite non-negative numeric value required") from None
    return result


def timestamp_value(value: str, field: str) -> datetime | None:
    if not value:
        return None
    if not TIMESTAMP_PATTERN.fullmatch(value):
        raise SchemaValidationError(f"{field}: timezone-qualified ISO timestamp required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SchemaValidationError(f"{field}: malformed timestamp") from None
    if result.utcoffset() is None:
        raise SchemaValidationError(f"{field}: timezone required")
    return result


@dataclass(frozen=True)
class AdmissionRecord:
    # Preserve original timestamps and decimal text rather than synthesizing provenance.
    fields: tuple[tuple[str, str], ...]

    def get(self, field: str) -> str:
        return dict(self.fields)[field]

    def number(self, field: str) -> Decimal | None:
        return decimal_value(self.get(field), field)

    @property
    def usability_gaps(self) -> tuple[str, ...]:
        gaps = []
        if self.get("capture_status") != "CAPTURED":
            gaps.append("CAPTURE_STATUS=" + self.get("capture_status"))
        for field in ("observation_timestamp", "retrieval_timestamp"):
            if not self.get(field):
                gaps.append("MISSING_" + field.upper())
        if self.get("config_required") == "TRUE" and not self.get("config_identity").strip():
            gaps.append("CONFIG_IDENTITY_UNRESOLVED")
        return tuple(gaps)

    def to_dict(self) -> dict:
        data = dict(self.fields)
        for field in NUMBER_FIELDS:
            value = self.number(field)
            data[field] = None if value is None else float(value)
        for field in ("chain_id", "block_number"):
            data[field] = int(data[field]) if data[field] else None
        data["config_required"] = data["config_required"] == "TRUE"
        for field in ("observation_timestamp", "retrieval_timestamp", "block_hash", "config_identity"):
            data[field] = data[field] or None
        return data


def validate_record(row: dict[str, str], chain_by_strategy: dict[str, int]) -> AdmissionRecord:
    sid = row["strategy_id"]
    if sid not in MVP_STRATEGY_IDS or sid not in chain_by_strategy:
        raise SchemaValidationError("strategy_id: independent frozen strategy required")
    if not row["chain_id"].isdigit() or int(row["chain_id"]) != chain_by_strategy[sid]:
        raise SchemaValidationError("chain_id: does not match strategy execution chain")
    for field in ("evidence_id", "source_id", "mechanism"):
        if not row[field].strip() or row[field] != row[field].strip():
            raise SchemaValidationError(f"{field}: nonblank text without surrounding whitespace required")
    if row["source_role"] != SOURCE_ROLES[sid]:
        raise SchemaValidationError("source_role: explicit strategy admission role required, not market/TVL observation")
    for field, values in (("evidence_type", {"EXACT_POINT", "SCALAR_BOUND"}),
                          ("admission_status", {"SUPPORTED", "UNSUPPORTED"}),
                          ("evidence_class", EVIDENCE_CLASSES), ("capture_status", CAPTURE_STATUSES)):
        if row[field] not in values:
            raise SchemaValidationError(f"{field}: unsupported value")
    # All current routes have validator/contract/registered-route context.
    # This does not derive or verify a deployment fingerprint.
    if row["config_required"] != "TRUE":
        raise SchemaValidationError("config_required: current strategy mechanisms require TRUE")
    obs = timestamp_value(row["observation_timestamp"], "observation_timestamp")
    retrieval = timestamp_value(row["retrieval_timestamp"], "retrieval_timestamp")
    if obs is not None and retrieval is not None and retrieval < obs:
        raise SchemaValidationError("retrieval_timestamp precedes observation_timestamp")
    if row["block_number"] and not row["block_number"].isdigit():
        raise SchemaValidationError("block_number: non-negative integer required")
    if row["block_hash"] and not re.fullmatch(r"0x[0-9a-fA-F]{64}", row["block_hash"]):
        raise SchemaValidationError("block_hash: 32-byte hex required")
    numbers = {field: decimal_value(row[field], field) for field in NUMBER_FIELDS}
    for field in ("amount_0g", "tested_amount_0g", "valuation_price_usd"):
        if numbers[field] is not None and numbers[field] <= 0:
            raise SchemaValidationError(f"{field}: positive value required when supplied")
    if row["evidence_type"] == "EXACT_POINT":
        if numbers["amount_0g"] is None:
            raise SchemaValidationError("EXACT_POINT requires amount_0g")
        if any(numbers[f] is not None for f in ("scalar_headroom_0g", "scalar_headroom_usd")):
            raise SchemaValidationError("EXACT_POINT must not imply a scalar bound")
    else:
        if all(numbers[f] is None for f in ("scalar_headroom_0g", "scalar_headroom_usd")):
            raise SchemaValidationError("SCALAR_BOUND requires explicit headroom")
    if numbers["tested_amount_0g"] is not None:
        if numbers["amount_0g"] is None or numbers["tested_amount_0g"] != numbers["amount_0g"]:
            raise SchemaValidationError("tested_amount_0g does not match amount_0g")
    for usd_field, native_field in (("amount_usd", "amount_0g"), ("tested_amount_usd", "tested_amount_0g"),
                                    ("scalar_headroom_usd", "scalar_headroom_0g")):
        if numbers[usd_field] is not None:
            price = numbers["valuation_price_usd"]
            if price is None:
                raise SchemaValidationError(f"{usd_field}: explicit valuation_price_usd required")
            if usd_field != "scalar_headroom_usd" and numbers[native_field] is None:
                raise SchemaValidationError(f"{usd_field}: corresponding native amount required")
            if numbers[native_field] is not None and numbers[native_field] * price != numbers[usd_field]:
                raise SchemaValidationError(f"{usd_field}: contradictory valuation/units")
    if row["evidence_type"] == "SCALAR_BOUND" and numbers["amount_0g"] is not None and row["admission_status"] == "SUPPORTED":
        bound = numbers["scalar_headroom_0g"]
        if bound is None:
            bound = numbers["scalar_headroom_usd"] / numbers["valuation_price_usd"]
        if numbers["amount_0g"] > bound:
            raise SchemaValidationError("supported capture amount exceeds scalar headroom")
    return AdmissionRecord(tuple((field, row[field]) for field in ADMISSION_COLUMNS))


def load_admission_records(path: str | Path = DEFAULT_ADMISSION_PATH, *, strategies=None) -> tuple[AdmissionRecord, ...]:
    metadata = load_strategies() if strategies is None else strategies
    chains = {str(row.strategy_id): int(row.execution_chain_id) for _, row in metadata.iterrows() if str(row.strategy_id) in MVP_STRATEGY_IDS}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(ADMISSION_COLUMNS):
            raise SchemaValidationError("admission evidence columns/order do not match canonical contract")
        records, seen = [], set()
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise SchemaValidationError(f"line {line}: malformed CSV width")
            record = validate_record(row, chains)
            identity = record.get("evidence_id")
            if identity in seen:
                raise SchemaValidationError(f"duplicate evidence_id: {identity}")
            seen.add(identity)
            records.append(record)
    return tuple(records)
