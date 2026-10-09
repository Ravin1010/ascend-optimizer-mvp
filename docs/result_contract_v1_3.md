# Optimizer result contract 1.3 — Iteration 12

Version 1.3 extends 1.2 without changing optimizer mathematics, profiles, CSVs, gates or evidence. Dashboard rendering is unchanged.

## Migration

| Concept | 1.2 | 1.3 | Compatibility |
|---|---|---|---|
| Input | asset/amount/portfolio_value_usd | decision_asset/decision_amount/decision_value_usd and submitted context | Legacy value alias means decision sleeve, never total holdings |
| Status | PROFILE_ELIGIBLE/PROFILE_EXCLUDED/SCOPE_EXCLUDED | Explicit metadata dimensions and allocation_result | Legacy summary retained, not primary |
| Eligibility | optimizer_eligible/profile_eligible | structural_candidate/allocation_admitted/numerical_admissibility | Existing-check results, not evidence certification |
| Reasons | opaque strings | code/kind/detail/fields | Raw reasons/errors preserved |
| Scope | implicit portfolio wording | DECISION_SLEEVE; whole-portfolio compliance NOT_ASSESSED | No holdings/funding state invented |
| Recommendation | implied by solver | Typed outcome and numerical-check basis | Weights/returns/stress unchanged |
| Readiness/proof | absent | NOT_ESTABLISHED; per-row proof from metadata | Positive allocation is not readiness/proof |
| Valuation | price only | price/value/acquisition mode; provenance NOT_REPRESENTED | No observation date/provider/validity invented |
| Outcome | solver status | RECOMMENDATION_GENERATED/NO_POSITIVE_ALLOCATION | Existing exception/error path retained |
| include_modelled | compatibility flag | same no-op, echoed | Cannot change gates, membership or allocations |

## Logical structure and semantics

- schema_version: literal 1.3.
- input.submitted: accepted numeric amount/horizon/fee inputs, original asset/profile labels, price override or null, compatibility flag. Copied from frozen run context, not mutable UI state.
- input: resolved decision asset/amount/USD value, canonical horizon/profile, price and legacy aliases.
- run_scope: capital_scope and constraint_scope DECISION_SLEEVE; whole_portfolio_compliance NOT_ASSESSED.
- valuation: asset, price_usd, decision_value_usd, FETCHED/USER_OVERRIDE acquisition_mode, NOT_REPRESENTED provenance_status.
- strategies: all seven reportable rows; exactly five structural candidates.
- portfolio: explicitly decision-sleeve allocations/idle/expected return/profit/legacy stress.
- profile_constraints: unchanged thresholds/diagnostics, explicitly sleeve-scoped.
- solver: unchanged status/message.
- outcome: positive versus no-positive allocation, CURRENT_INPUTS_AND_NUMERICAL_CHECKS basis, readiness/proof NOT_ESTABLISHED.

Existing positions, pending claims, existing idle, funding origin and whole-portfolio value are not acquired or synthesized. Total-portfolio compliance cannot be claimed. USER_OVERRIDE is assumed/user-supplied valuation, not observed live valuation. FETCHED identifies acquisition mode only; no provider/freshness/evidence qualification is established.

## Strategy fields

Every row carries optimizer_universe, reconciliation_category, protocol_availability, integration_status, allocation_gate, evidence_readiness, runtime_feasibility, live_capstone_proof, parent_strategy_id, structural_candidate and allocation_admitted.

allocation_admitted permits continuation through existing checks; numerical_admissibility reports those checks separately. NOT_ASSESSED remains unknown. allocation_result is NOT_CANDIDATE/GATED/EXCLUDED/ALLOCATED_POSITIVE/ELIGIBLE_ZERO. execution_readiness is NOT_ESTABLISHED. constraint_diagnostics_basis is LEGACY_STRATEGY_COEFFICIENTS_AND_SLEEVE_WEIGHTS; raw coefficient versus aggregate-cap diagnostics are not redesigned.

Jaine is conditional. Ascend is LIVE/IMPLEMENTED/structural but CLOSED/GATED, zero allocation, no live proof. Embedded restaking is attached to Ascend; embedded/Morpho have no independent return or allocation.

## Typed reasons

| Code | Trigger |
|---|---|
| NOT_IN_OPTIMIZER_UNIVERSE | Explicit non-member |
| ALLOCATION_GATE_CLOSED | Explicit CLOSED gate |
| MISSING_RETURN_DATA | Missing snapshot or APR/APY source |
| RETURN_CALCULATION_UNAVAILABLE | Other reported return calculation failure |
| MISSING_EXPOSURE_DATA | Required current fields missing, listed in fields |
| RUNTIME_QUOTE_UNAVAILABLE | Actual quote error |
| PROFILE_SLIPPAGE_LIMIT | Existing slippage exclusion |
| PROFILE_EXIT_TIME_LIMIT | Existing exit-time exclusion |
| LEGACY_LIQUIDITY_BOUND | Existing no-usable-liquidity exclusion, not true capacity |
| UNCLASSIFIED_RUNTIME_REASON | Actual unmapped reason retained without invented diagnosis |
| ELIGIBLE_ZERO_ALLOCATION | Checks admit route; solver assigns zero, not exclusion |

Kinds are EXCLUSION/DATA_GAP/RUNTIME_GAP/ALLOCATION_RESULT. Zero allocation does not prove economic domination, fixed-cost cause or binding aggregate risk. PROFILE_RISK_LIMIT and causal SOLVER_NOT_SELECTED explanations are not emitted because runtime does not establish those attributions. No probabilities, freshness validity or new risk/capacity semantics are inferred.

## API/TypeScript

POST /api/optimize preserves existing amount/horizon/profile inputs and error behavior; optionally forwards the existing include_modelled compatibility flag. Required version/state semantics are checked, then the entire result is forwarded unchanged. Incompatible output fails through the existing 500 envelope.

TypeScript defines literal version and state/scope/outcome/reason unions, extending existing interfaces. Existing UI fields remain available. No page changes. Node contract tests use built-in TypeScript support (tested on Node 24.19.0), actual API/subprocess boundary, synthetic snapshots and assumed price; no collectors or market measurements.

## Validation boundary

Tests cover strict JSON, five members/two non-members, gate suppression, zero versus exclusion, scope aliases, acquisition modes without invented provenance, immutable submitted/resolved context, compatibility no-op and API pass-through/rejection. Full Python suite, API tests, TypeScript check and production build are required before publication.
