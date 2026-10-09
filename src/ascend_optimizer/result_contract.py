"""Schema 1.3 reporting helpers. No admission or optimization decisions here."""
from __future__ import annotations

from typing import Any

import pandas as pd

from .strategy_state import strategy_state

SCHEMA_VERSION = "1.3"


def strategy_contract(row: pd.Series, *, weight: float, profile_eligible: bool,
                      optimizer_eligible: bool, legacy_reasons: list[str]) -> dict[str, Any]:
    state = strategy_state(row)
    if not state.structural_candidate:
        allocation_result = "NOT_CANDIDATE"
    elif state.allocation_gate == "CLOSED":
        allocation_result = "GATED"
    elif not profile_eligible:
        allocation_result = "EXCLUDED"
    elif weight > 0:
        allocation_result = "ALLOCATED_POSITIVE"
    else:
        allocation_result = "ELIGIBLE_ZERO"

    reasons: list[dict[str, Any]] = []

    def add(code: str, kind: str, detail: str, fields: list[str] | None = None) -> None:
        item = {"code": code, "kind": kind, "detail": detail, "fields": fields or []}
        if item not in reasons:
            reasons.append(item)

    if not state.structural_candidate:
        add("NOT_IN_OPTIMIZER_UNIVERSE", "EXCLUSION", state.reconciliation_category)
    elif state.allocation_gate == "CLOSED":
        add("ALLOCATION_GATE_CLOSED", "EXCLUSION", "Explicit allocation gate remains CLOSED.")

    if state.structural_candidate:
        missing = row.get("missing_exposures")
        if missing is not None and not pd.isna(missing) and str(missing):
            add("MISSING_EXPOSURE_DATA", "DATA_GAP", "Required exposure values are unavailable.", str(missing).split("|"))
        error = row.get("return_error")
        if error is not None and not pd.isna(error) and str(error):
            code = "MISSING_RETURN_DATA" if str(error) == "missing_snapshot" or "gross_apy or gross_apr" in str(error) else "RETURN_CALCULATION_UNAVAILABLE"
            add(code, "DATA_GAP", str(error))
        quote_error = row.get("runtime_exposure_error")
        if quote_error is not None and not pd.isna(quote_error) and str(quote_error):
            add("RUNTIME_QUOTE_UNAVAILABLE", "RUNTIME_GAP", str(quote_error))

    mappings = {
        "slippage_exceeds_profile_limit": "PROFILE_SLIPPAGE_LIMIT",
        "exit_time_exceeds_profile_limit": "PROFILE_EXIT_TIME_LIMIT",
        "no_usable_liquidity": "LEGACY_LIQUIDITY_BOUND",
    }
    for reason in legacy_reasons:
        if reason in mappings:
            add(mappings[reason], "EXCLUSION", reason)
        elif (reason == "optimizer_eligible=False" or reason == "missing_net_return_horizon"
              or reason.startswith(("missing_", "missing_exposures=", "optimizer_universe=", "allocation_gate=",
                                    "reconciliation_category=", "integration_status=", "protocol_availability="))):
            # Explicit dimensions/gaps already retain the underlying facts.
            continue
        else:
            add("UNCLASSIFIED_RUNTIME_REASON", "EXCLUSION", reason)
    if allocation_result == "ELIGIBLE_ZERO":
        add("ELIGIBLE_ZERO_ALLOCATION", "ALLOCATION_RESULT",
            "Current checks admit the route; the solver assigned zero. The specific economic or binding cause is not determined.")
    return {
        **state.reporting_fields(),
        "numerical_admissibility": {
            "optimizer_checks_passed": optimizer_eligible,
            "profile_checks_passed": profile_eligible,
            "basis": "CURRENT_NUMERICAL_CHECKS",
        },
        "allocation_result": allocation_result,
        "reasons": reasons,
        "execution_readiness": "NOT_ESTABLISHED",
        "constraint_diagnostics_basis": "LEGACY_STRATEGY_COEFFICIENTS_AND_SLEEVE_WEIGHTS",
    }
