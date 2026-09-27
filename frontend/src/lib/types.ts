export type RiskProfile = "Conservative" | "Balanced" | "Aggressive";

export interface OptimizerAllocation {
  strategy_id: string;
  weight: number;
  amount_usd: number;
}

export interface OptimizerStrategy {
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
}

export interface OptimizerResponse {
  schema_version: string;
  input: {
    asset: string;
    amount: number;
    asset_price_usd: number;
    portfolio_value_usd: number;
    horizon_days: number;
    profile: RiskProfile;
    include_modelled: boolean;
  };
  profile_constraints: {
    max_strategy_concentration: number;
    max_bridge_exposure: number;
    max_entry_exit_slippage: number;
    max_portfolio_lp_il_stress: number;
    max_exit_time_days: number;
    max_slashing_stress_loss: number;
    binding_constraints: string[];
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
  portfolio: {
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
