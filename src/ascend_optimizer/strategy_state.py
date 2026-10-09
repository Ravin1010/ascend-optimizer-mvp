"""Internal metadata interpretation; legacy labels never decide membership.

NOT_ASSESSED is preserved as unknown, not upgraded to valid evidence. Admission
here authorizes continuation through existing numerical/runtime/profile checks;
it is not execution readiness, gate clearance or live-capital suitability.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from .data_loader import STRATEGY_METADATA_VALUES

STATE_FIELDS = (
    "optimizer_universe", "reconciliation_category", "protocol_availability",
    "integration_status", "allocation_gate", "evidence_readiness",
    "runtime_feasibility", "live_capstone_proof",
)


@dataclass(frozen=True)
class StrategyState:
    optimizer_universe: str
    reconciliation_category: str
    protocol_availability: str
    integration_status: str
    allocation_gate: str
    evidence_readiness: str
    runtime_feasibility: str
    live_capstone_proof: str
    parent_strategy_id: str | None

    @property
    def structural_candidate(self) -> bool:
        return self.optimizer_universe == "TRUE"

    @property
    def admission_reasons(self) -> tuple[str, ...]:
        reasons = []
        if not self.structural_candidate:
            reasons.append("optimizer_universe=FALSE")
        if self.reconciliation_category not in {"INTEGRATED_ALLOCATABLE", "INTEGRATED_GATED"}:
            reasons.append(f"reconciliation_category={self.reconciliation_category}")
        if self.integration_status != "IMPLEMENTED":
            reasons.append(f"integration_status={self.integration_status}")
        if self.protocol_availability != "LIVE":
            reasons.append(f"protocol_availability={self.protocol_availability}")
        if self.allocation_gate != "CONDITIONAL":
            reasons.append(f"allocation_gate={self.allocation_gate}")
        return tuple(reasons)

    @property
    def allocation_admitted(self) -> bool:
        return not self.admission_reasons

    @property
    def legacy_technical_eligibility(self) -> str:
        """Compatibility output derived from dimensions, never read as input."""
        if not self.structural_candidate:
            if self.reconciliation_category == "EMBEDDED_NON_ALLOCATABLE":
                return "EXCLUDED_EMBEDDED"
            return "EXCLUDED_OBSERVED_UNINTEGRATED"
        if not self.allocation_admitted:
            return "EXCLUDED_LIVE_DATA_INCOMPLETE"
        return "ELIGIBLE_WITH_RUNTIME_CONSTRAINTS"

    def reporting_fields(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "structural_candidate": self.structural_candidate,
            "allocation_admitted": self.allocation_admitted,
        }


def strategy_state(row: pd.Series | dict[str, Any]) -> StrategyState:
    values = {}
    for field in STATE_FIELDS:
        value = row.get(field)
        if value is None or pd.isna(value) or str(value) not in STRATEGY_METADATA_VALUES[field]:
            raise ValueError(f"{field} requires authoritative metadata; received {value!r}")
        values[field] = str(value)
    parent = row.get("parent_strategy_id")
    values["parent_strategy_id"] = None if parent is None or pd.isna(parent) else str(parent)
    return StrategyState(**values)
