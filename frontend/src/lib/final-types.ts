import type { RiskProfile, AllocationResult } from './types.ts';
export const STRATEGY_IDS = ['NATIVE_STAKE_0G','GIMO_STAKE_0G','JAINE_LP_0G_USDC','OKU_LP_0G_USDC','ASCEND_STAKE_A0G'] as const;
export type StrategyId = typeof STRATEGY_IDS[number];
export type EvidenceMode = 'PRODUCTION' | 'SYNTHETIC_EVALUATION_ONLY';
export type DeadlineState = 'NOT_REQUESTED' | 'COMPATIBLE_MODELLED' | 'INCOMPATIBLE_MODELLED' | 'UNRESOLVED';
export type Measurement = {state:'ASSESSED'; value:string; unit:'USD'|'FRACTION'|'DAYS'; basis:string} | {state:'NOT_ASSESSED'|'MISSING'|'POLICY_UNDEFINED'|'NOT_SUPPORTED'; value:null; unit:'USD'|'FRACTION'|'DAYS'; basis:string};
export type Economics = Record<'gross_income_usd'|'lifecycle_cost_usd'|'fixed_cost_usd'|'quote_execution_cost_usd'|'expected_net_profit_usd'|'expected_net_return'|'net_apy',Measurement>;
export interface Limit {state:'PASS'|'FAIL'|'UNRESOLVED'|'NOT_ASSESSED'; value:string|null; limit:string}
export interface FinalStrategy {
 strategy_id:StrategyId; display_name:string; canonical_state:'INTEGRATED_ALLOCATABLE'|'INTEGRATED_GATED'; structural_candidate:true;
 allocation_gate:'CLOSED'|'CONDITIONAL'; allocation_result:AllocationResult; allocated_weight:string; allocated_amount_0g:string;
 technical_admission:'UNKNOWN'|'SUPPORTED'|'UNSUPPORTED'|'NOT_REQUIRED'; economics_state:'ASSESSED'|'MISSING'; economics:Economics;
 diagnostic_amount_0g:string; economics_basis:'SELECTED_EXACT_AMOUNT'|'UNSELECTED_CANDIDATE_DIAGNOSTIC';
 risk:{state:'ASSESSED_MODELLED'|'ASSESSED_OBSERVED'|'PARTIALLY_ASSESSED'|'UNRESOLVED'|'NOT_APPLICABLE';loss_fraction:Measurement;absolute_loss_usd:Measurement;basis:'SELECTED_EXACT_AMOUNT'|'UNSELECTED_CANDIDATE_DIAGNOSTIC'};
 policy_feasibility:'PASS'|'FAIL'|'UNRESOLVED'|'NOT_ASSESSED'; rejection_reasons:string[]; binding_constraints:string[];
 evidence:{mode:EvidenceMode; class:'MODELLED'|'MISSING'; provenance:unknown};
 liquidity:{exit_type:'SYNCHRONOUS'|'ASYNCHRONOUS'|'QUEUE_BASED'|'UNRESOLVED'; time_to_cash_days:Measurement; deadline_state:DeadlineState; qualification:string; model_version:'EXIT_LIQUIDITY_V1'; output_asset:'native 0G'};
 protocol_availability:'LIVE'|'DEPLOYED_MARKET_UNRESOLVED'; integration_state:'IMPLEMENTED'; runtime_configuration:'UNRESOLVED'; execution_readiness:'NOT_ESTABLISHED'; public_proof:'NOT_ESTABLISHED';
}
export interface FinalResponse {
 schema_version:'1.4'; input:{decision_amount_0g:string;profile:RiskProfile;holding_horizon_days:string;cash_deadline_days:string|null;evidence_mode:EvidenceMode};
 run_scope:{scope:'DECISION_SLEEVE';whole_portfolio_compliance:'NOT_ASSESSED';existing_positions:'EXOGENOUS_NOT_OPTIMIZED'};
 valuation:{price_usd:Measurement;evidence_class:'MODELLED'|'MISSING'};
 recommendation:{method:'POLICY_AWARE_AMOUNT_OPTIMIZER';state:'RECOMMENDATION_GENERATED'|'KEEP_IDLE'|'SELECTED_REVALIDATION_FAILED';allocation_weights:Record<StrategyId,string>;allocated_amounts_0g:Record<StrategyId,string>;idle_weight:string;idle_amount_0g:string;economics:Economics;revalidation_state:'PASSED'|'FAILED'|'NOT_REQUIRED'};
 strategies:FinalStrategy[];
 risk:{profile:RiskProfile;concentration:Limit;staking_stress:Limit;lp_absolute_stress:Limit;total_decision_sleeve_stress:Measurement;qualification:string};
 liquidity:{holding_horizon_days:string;cash_deadline_days:string|null;deadline_state:DeadlineState;idle_time_to_cash_days:'0'};
 policy:{version:'EVALUATION_POLICY_V1';state:'PASS'|'FAIL'|'UNRESOLVED'|'NOT_ASSESSED';binding_constraints:string[];unresolved_required_constraints:string[];assessment:unknown;qualification:string};
 solver:{method:'AMOUNT_GRID_ENUMERATION_V1';grid:number[];combinations_tested:number;revalidation_errors:string[]};
 evidence:{mode:EvidenceMode;valuation_and_admission:'MODELLED'|'UNRESOLVED';runtime_binding:'UNRESOLVED'};
 readiness:{execution_readiness:'NOT_ESTABLISHED';public_proof:'NOT_ESTABLISHED';public_deployment:'NOT_REQUIRED_NOT_PLANNED'};
 comparison:{legacy_linear:({state:'NOT_ASSESSED';capability_warning:string}|{state:'ASSESSED';capability_warning:string;allocation_weights:Record<StrategyId,string>;idle_weight:string;selection_expected_net_profit:Measurement;profit_comparability:'LIMITED';cash_deadline:'NOT_SUPPORTED';risk_namespace:'LEGACY_COMPATIBILITY'})};
}
