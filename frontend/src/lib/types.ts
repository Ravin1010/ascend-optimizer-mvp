// Schema 1.3: numerical recommendation is not evidence validity or execution proof.
export type UniverseMembership = "TRUE" | "FALSE";
export type ReconciliationCategory = "INTEGRATED_ALLOCATABLE" | "INTEGRATED_GATED" | "EMBEDDED_NON_ALLOCATABLE" | "OBSERVED_EXCLUDED";
export type AllocationGate = "CONDITIONAL" | "CLOSED" | "NOT_APPLICABLE";
export type EvidenceReadiness = "NOT_ASSESSED" | "INCOMPLETE" | "NOT_APPLICABLE";
export type RuntimeFeasibility = "NOT_ASSESSED" | "NOT_APPLICABLE";
export type ProofState = "NOT_ESTABLISHED" | "NOT_APPLICABLE";
export type AnalysisScope = "DECISION_SLEEVE";
export type AllocationResult = "NOT_CANDIDATE" | "GATED" | "EXCLUDED" | "ALLOCATED_POSITIVE" | "ELIGIBLE_ZERO";
export type ReasonCode = "NOT_IN_OPTIMIZER_UNIVERSE" | "ALLOCATION_GATE_CLOSED" | "MISSING_RETURN_DATA" | "RETURN_CALCULATION_UNAVAILABLE" | "MISSING_EXPOSURE_DATA" | "RUNTIME_QUOTE_UNAVAILABLE" | "PROFILE_SLIPPAGE_LIMIT" | "PROFILE_EXIT_TIME_LIMIT" | "LEGACY_LIQUIDITY_BOUND" | "UNCLASSIFIED_RUNTIME_REASON" | "ELIGIBLE_ZERO_ALLOCATION";
export type RunOutcome = "RECOMMENDATION_GENERATED" | "NO_POSITIVE_ALLOCATION";
export interface StrategyReason {
  code: ReasonCode;
  kind: "EXCLUSION" | "DATA_GAP" | "RUNTIME_GAP" | "ALLOCATION_RESULT";
  detail: string;
  fields: string[];
}
export interface StrategyState {
  optimizer_universe: UniverseMembership;
  reconciliation_category: ReconciliationCategory;
  protocol_availability: "LIVE" | "DEPLOYED_MARKET_UNRESOLVED";
  integration_status: "IMPLEMENTED" | "EMBEDDED" | "NOT_INTEGRATED";
  allocation_gate: AllocationGate;
  evidence_readiness: EvidenceReadiness;
  runtime_feasibility: RuntimeFeasibility;
  live_capstone_proof: ProofState;
  parent_strategy_id: string | null;
  structural_candidate: boolean;
  /** Metadata admission to existing checks; not execution readiness. */
  allocation_admitted: boolean;
}
export type RiskProfile = "Conservative" | "Balanced" | "Aggressive";

export interface OptimizerAllocation {
  strategy_id: string;
  weight: number;
  amount_usd: number;
}

export interface OptimizerStrategy extends StrategyState {
  numerical_admissibility: {
    optimizer_checks_passed: boolean;
    profile_checks_passed: boolean;
    basis: "CURRENT_NUMERICAL_CHECKS";
  };
  allocation_result: AllocationResult;
  reasons: StrategyReason[];
  execution_readiness: "NOT_ESTABLISHED";
  constraint_diagnostics_basis: "LEGACY_STRATEGY_COEFFICIENTS_AND_SLEEVE_WEIGHTS";
  /** Legacy summary; authoritative dimensions above are primary. */
  strategy_id: string;
  status: "PROFILE_ELIGIBLE" | "PROFILE_EXCLUDED" | "SCOPE_EXCLUDED";
  optimizer_eligible: boolean;
  profile_eligible: boolean;
  scope_eligible: boolean;
  exclusion_reasons: string[];
  technical_eligibility: string | null;
  data_status: string | null;
  net_apy: number | null;
  net_return_horizon: number | null;
  net_profit_usd: number | null;
  gross_apy_used: number | null;
  liquidity_usd: number | null;
  max_entry_exit_slippage: number | null;
  exit_time_days: number | null;
  bridge_fraction: number | null;
  slashing_stress_loss: number | null;
  lp_stress_loss_20pct: number | null;
  allocation_weight: number;
  allocation_usd: number;
  return_error: string | null;
  runtime_exposure_error: string | null;
  constraint_diagnostics: {
    strategy_concentration: ConstraintDiagnostic;
    slippage: ConstraintDiagnostic;
    exit_time: ConstraintDiagnostic;
    bridge: ConstraintDiagnostic;
    slashing: ConstraintDiagnostic;
    lp_stress: ConstraintDiagnostic;
  };
}

export interface ConstraintDiagnostic {
  value: number | null;
  limit: number;
  headroom: number | null;
  utilization: number | null;
  state:
    | "UNAVAILABLE"
    | "WITHIN_LIMIT"
    | "NEAR_LIMIT"
    | "AT_LIMIT"
    | "EXCEEDED";
}

export interface OptimizerResponse {
  schema_version: "1.3";
  /** Optional comparison; original portfolio remains the legacy benchmark. */
  amount_aware?: AmountAwareComparison;
  run_scope: {
    capital_scope: AnalysisScope;
    constraint_scope: AnalysisScope;
    whole_portfolio_compliance: "NOT_ASSESSED";
  };
  valuation: {
    asset: "0G";
    price_usd: number;
    decision_value_usd: number;
    acquisition_mode: "FETCHED" | "USER_OVERRIDE";
    provenance_status: "NOT_REPRESENTED";
  };
  outcome: {
    state: RunOutcome;
    recommendation_basis: "CURRENT_INPUTS_AND_NUMERICAL_CHECKS";
    execution_readiness: "NOT_ESTABLISHED";
    live_capstone_proof: "NOT_ESTABLISHED";
  };
  input: {
    /** Accepted numeric inputs plus original submitted asset/profile labels. */
    submitted: {
      decision_asset: string;
      decision_amount: number;
      horizon_days: number;
      profile: string;
      price_usd_override: number | null;
      management_fee_rate: number;
      performance_fee_rate: number;
      include_modelled: boolean;
    };
    decision_asset: "0G";
    decision_amount: number;
    decision_value_usd: number;
    asset: string;
    amount: number;
    asset_price_usd: number;
    /** Legacy alias of decision_value_usd, never total user holdings. */
    portfolio_value_usd: number;
    horizon_days: number;
    profile: RiskProfile;
    include_modelled: boolean;
  };
  profile_constraints: {
    scope: AnalysisScope;
    max_strategy_concentration: number;
    max_bridge_exposure: number;
    max_entry_exit_slippage: number;
    max_portfolio_lp_il_stress: number;
    max_exit_time_days: number;
    max_slashing_stress_loss: number;
    at_limit_constraints: string[];
    triggered_constraints: string[];
    observed: {
      max_allocated_strategy_weight: number;
      max_allocated_slippage: number;
      max_allocated_exit_time_days: number;
      portfolio_bridge_exposure: number;
      portfolio_lp_il_stress: number;
      portfolio_slashing_stress_loss: number;
    };
  };
  /** Recommendation for the decision sleeve only. */
  portfolio: {
    scope: AnalysisScope;
    allocations: OptimizerAllocation[];
    idle: {
      weight: number;
      amount_usd: number;
    };
    deployed_weight: number;
    expected_net_return_horizon: number;
    annualized_expected_net_apy: number;
    expected_net_profit_usd: number;
    stress: {
      bridge_exposure: number;
      lp_il: number;
      slashing: number;
    };
  };
  strategies: OptimizerStrategy[];
  solver: {
    status: number;
    message: string;
  };
}


export type TechnicalAdmission = "SUPPORTED" | "UNSUPPORTED" | "UNKNOWN";
export interface AdmissionEvidence {
  status: TechnicalAdmission; strategy_id: string; amount_0g: number; chain_id: number;
  source: string; mechanism: string; evidence_class: string; scalar_headroom_usd: number | null;
  /** Optional per-capture provenance; validity applies only to admission. */
  capture?: AdmissionCapture | null;
  diagnostics?: string[];
  validity?: AdmissionValidity | null;
  validity_records?: AdmissionValidity[];
}
export interface AmountCandidate {
  strategy_id: string; weight: number; amount_0g: number; amount_usd: number;
  net_profit_usd: number | null; net_return_horizon: number | null; net_apy: number | null;
  fixed_execution_cost_usd: number | null;
  technical_admission: TechnicalAdmission | "NOT_REQUIRED";
  admission_evidence: AdmissionEvidence | null;
  runtime_execution: "NOT_TESTED" | "NOT_REQUIRED" | "TESTED_PROXY" | "SNAPSHOT_PROXY" | "FAILED";
  eligible: boolean; rejection_reasons: string[];
  quote_context: {
    amount_0g: number; price_usd: number;
    quote: {strategy_id: string; fee_tier: number; entry_slippage_rate: number; exit_slippage_rate: number;
      entry_amount_out_usdc: number; exit_amount_out_0g: number};
    snapshot_notes: string; basis: "CURRENT_QUOTER_AND_MODELLED_EXIT_INVENTORY";
    registered_configuration_alignment: "NOT_ESTABLISHED";
    exit_inventory: "CURRENT_TARGET_PROXY_NOT_FUTURE_POSITION";
  } | null;
  entry_slippage_rate: number | null; exit_slippage_rate: number | null;
  bridge_fraction: number | null; lp_stress_loss_20pct: number | null;
  slashing_stress_loss: number | null; exit_time_days: number | null;
}
export interface AmountAwareComparison {
  method: "AMOUNT_GRID_ENUMERATION_V1"; scope: AnalysisScope; whole_portfolio_compliance: "NOT_ASSESSED";
  profile: RiskProfile; decision_amount_0g: number; decision_value_usd: number; price_usd: number; horizon_days: number;
  management_fee_rate: number; performance_fee_rate: number;
  grid: number[]; weight_tolerance: number; profit_tolerance_usd: number; combinations_tested: number;
  selected_amount_revalidation: "PASSED" | "FAILED" | "NOT_REQUIRED"; revalidation_errors: string[];
  outcome: RunOutcome | "SELECTED_REVALIDATION_FAILED";
  execution_readiness: "NOT_ESTABLISHED"; live_capstone_proof: "NOT_ESTABLISHED";
  risk_basis: "LEGACY_SLEEVE_COEFFICIENTS";
  cost_basis: "EXISTING_FIXED_USD_LIFECYCLE_CONVENTION_PROVENANCE_UNRESOLVED";
  candidates: AmountCandidate[]; proposed_selected: AmountCandidate[];
  strategy_results: Record<string, "ALLOCATED_POSITIVE" | "ELIGIBLE_ZERO" | "EXCLUDED" | "GATED" | "REVALIDATION_FAILED">;
  reported_non_members: string[];
  recommendation: {
    allocations: Record<string, {weight: number; amount_0g: number; amount_usd: number}>;
    idle_weight: number; idle_amount_0g: number; expected_net_profit_usd: number; expected_net_return_horizon: number;
    legacy_stress: {bridge_fraction: number; lp_stress_loss_20pct: number; slashing_stress_loss: number};
  } | null;
  benchmark?: {
    method: "LEGACY_LINEAR"; allocations: Record<string, number>; idle_weight: number;
    expected_net_profit_usd: number; expected_net_return_horizon: number; coefficient_amount_0g: number;
    quote_policy: "FULL_NOTIONAL_ONLY_WHEN_PREFILLED_SLIPPAGE_MISSING"; exclusions: Record<string, string[]>;
  };
}


export interface AdmissionCapture {
  evidence_id: string; strategy_id: string; chain_id: number;
  evidence_type: "EXACT_POINT" | "SCALAR_BOUND";
  admission_status: "SUPPORTED" | "UNSUPPORTED";
  amount_0g: number | null; amount_usd: number | null;
  scalar_headroom_0g: number | null; scalar_headroom_usd: number | null;
  source_id: string;
  source_role: "CONFIGURED_VALIDATOR_ADMISSION" | "GIMO_PROTOCOL_ADMISSION" | "REGISTERED_LP_ADMISSION" | "SOURCECORE_ADMISSION";
  mechanism: string;
  evidence_class: "LIVE_OBSERVED" | "LIVE_DERIVED" | "HISTORICAL" | "MODELLED" | "STATIC_CONFIG";
  observation_timestamp: string | null; retrieval_timestamp: string | null;
  block_number: number | null; block_hash: string | null;
  config_identity: string | null; config_required: boolean;
  tested_amount_0g: number | null; tested_amount_usd: number | null;
  valuation_price_usd: number | null;
  capture_status: "CAPTURED" | "NO_FRESH_CAPTURE_SUPPLIED" | "SOURCE_UNVERIFIED" | "CONFIG_UNRESOLVED" | "INVALID";
  notes: string;
}


export type AdmissionValidityState = "VALID" | "STALE" | "CONFIG_MISMATCH" | "AMOUNT_MISMATCH" | "SOURCE_UNVERIFIED" | "MISSING" | "POLICY_UNDEFINED";
export interface AdmissionValidity {
  state: AdmissionValidityState; as_of: string;
  observation_timestamp: string | null; retrieval_timestamp: string | null;
  observation_age_seconds: number | null; max_age_seconds: number | null;
  source_role: string; evidence_class: string; config_identity: string | null;
  candidate_amount_0g: string; candidate_amount_usd: string;
  policy_version: string; reason_code: string; details: string;
  config_verification_state: string | null; config_verification_source: string | null;
  evidence_id?: string; captured_assertion?: TechnicalAdmission;
}
