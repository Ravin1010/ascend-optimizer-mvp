import type { OptimizerResponse } from "./types.ts";

function record(value: unknown): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Invalid optimizer contract object");
  }
  return value as Record<string, unknown>;
}
function oneOf(value: unknown, choices: readonly unknown[]): void {
  if (!choices.includes(value)) throw new Error("Invalid optimizer contract value");
}

/** Guard the required 1.3 semantics, then forward the entire payload unchanged.
 * Legacy measurements/diagnostics are not upgraded into qualified evidence.
 */
export function parseOptimizerResponse(stdout: string): OptimizerResponse {
  const parsed: unknown = JSON.parse(stdout);
  const root = record(parsed);
  oneOf(root.schema_version, ["1.3"]);
  const scope = record(root.run_scope);
  oneOf(scope.capital_scope, ["DECISION_SLEEVE"]);
  oneOf(scope.constraint_scope, ["DECISION_SLEEVE"]);
  oneOf(scope.whole_portfolio_compliance, ["NOT_ASSESSED"]);
  const input = record(root.input);
  oneOf(input.decision_asset, ["0G"]);
  for (const key of ["decision_amount", "decision_value_usd"]) {
    if (typeof input[key] !== "number" || !Number.isFinite(input[key])) throw new Error("Invalid decision capital");
  }
  record(input.submitted);
  const valuation = record(root.valuation);
  oneOf(valuation.acquisition_mode, ["FETCHED", "USER_OVERRIDE"]);
  oneOf(valuation.provenance_status, ["NOT_REPRESENTED"]);
  const outcome = record(root.outcome);
  oneOf(outcome.state, ["RECOMMENDATION_GENERATED", "NO_POSITIVE_ALLOCATION"]);
  oneOf(outcome.execution_readiness, ["NOT_ESTABLISHED"]);
  oneOf(outcome.live_capstone_proof, ["NOT_ESTABLISHED"]);
  const portfolio = record(root.portfolio);
  oneOf(portfolio.scope, ["DECISION_SLEEVE"]);
  const constraints = record(root.profile_constraints);
  oneOf(constraints.scope, ["DECISION_SLEEVE"]);
  record(root.solver);
  if (!Array.isArray(root.strategies)) throw new Error("Missing optimizer strategy rows");
  for (const value of root.strategies) {
    const row = record(value);
    oneOf(row.optimizer_universe, ["TRUE", "FALSE"]);
    oneOf(row.reconciliation_category, ["INTEGRATED_ALLOCATABLE", "INTEGRATED_GATED", "EMBEDDED_NON_ALLOCATABLE", "OBSERVED_EXCLUDED"]);
    oneOf(row.protocol_availability, ["LIVE", "DEPLOYED_MARKET_UNRESOLVED"]);
    oneOf(row.integration_status, ["IMPLEMENTED", "EMBEDDED", "NOT_INTEGRATED"]);
    oneOf(row.allocation_gate, ["CONDITIONAL", "CLOSED", "NOT_APPLICABLE"]);
    oneOf(row.evidence_readiness, ["NOT_ASSESSED", "INCOMPLETE", "NOT_APPLICABLE"]);
    oneOf(row.runtime_feasibility, ["NOT_ASSESSED", "NOT_APPLICABLE"]);
    oneOf(row.live_capstone_proof, ["NOT_ESTABLISHED", "NOT_APPLICABLE"]);
    for (const key of ["structural_candidate", "allocation_admitted"]) {
      if (typeof row[key] !== "boolean") throw new Error("Missing strategy state");
    }
    oneOf(row.allocation_result, ["NOT_CANDIDATE", "GATED", "EXCLUDED", "ALLOCATED_POSITIVE", "ELIGIBLE_ZERO"]);
    oneOf(row.execution_readiness, ["NOT_ESTABLISHED"]);
    const numerical = record(row.numerical_admissibility);
    oneOf(numerical.basis, ["CURRENT_NUMERICAL_CHECKS"]);
    for (const key of ["optimizer_checks_passed", "profile_checks_passed"]) {
      if (typeof numerical[key] !== "boolean") throw new Error("Invalid numerical admissibility");
    }
    oneOf(row.constraint_diagnostics_basis, ["LEGACY_STRATEGY_COEFFICIENTS_AND_SLEEVE_WEIGHTS"]);
    if (!Array.isArray(row.reasons)) throw new Error("Missing typed reasons");
    for (const value of row.reasons) {
      const reason = record(value);
      oneOf(reason.code, ["NOT_IN_OPTIMIZER_UNIVERSE", "ALLOCATION_GATE_CLOSED", "MISSING_RETURN_DATA", "RETURN_CALCULATION_UNAVAILABLE", "MISSING_EXPOSURE_DATA", "RUNTIME_QUOTE_UNAVAILABLE", "PROFILE_SLIPPAGE_LIMIT", "PROFILE_EXIT_TIME_LIMIT", "LEGACY_LIQUIDITY_BOUND", "UNCLASSIFIED_RUNTIME_REASON", "ELIGIBLE_ZERO_ALLOCATION"]);
      oneOf(reason.kind, ["EXCLUSION", "DATA_GAP", "RUNTIME_GAP", "ALLOCATION_RESULT"]);
      if (typeof reason.detail !== "string" || !Array.isArray(reason.fields) || !reason.fields.every((x: unknown) => typeof x === "string")) {
        throw new Error("Invalid typed reason");
      }
    }
  }
  if (root.amount_aware !== undefined) {
    const extension = record(root.amount_aware);
    oneOf(extension.method, ["AMOUNT_GRID_ENUMERATION_V1"]);
    oneOf(extension.scope, ["DECISION_SLEEVE"]);
    oneOf(extension.whole_portfolio_compliance, ["NOT_ASSESSED"]);
    oneOf(extension.selected_amount_revalidation, ["PASSED", "FAILED", "NOT_REQUIRED"]);
    oneOf(extension.outcome, ["RECOMMENDATION_GENERATED", "NO_POSITIVE_ALLOCATION", "SELECTED_REVALIDATION_FAILED"]);
    oneOf(extension.execution_readiness, ["NOT_ESTABLISHED"]);
    oneOf(extension.live_capstone_proof, ["NOT_ESTABLISHED"]);
    if (!Array.isArray(extension.candidates)) throw new Error("Missing amount candidates");
    for (const value of extension.candidates) {
      const candidate = record(value);
      oneOf(candidate.technical_admission, ["SUPPORTED", "UNSUPPORTED", "UNKNOWN", "NOT_REQUIRED"]);
      if (typeof candidate.eligible !== "boolean") throw new Error("Missing candidate eligibility");
    }
    if (extension.selected_amount_revalidation === "FAILED" && extension.recommendation !== null) {
      throw new Error("Failed revalidation cannot carry a recommendation");
    }
  }
  // Preserve all fields, including legacy aliases; never reconstruct/pick keys.
  return parsed as OptimizerResponse;
}
