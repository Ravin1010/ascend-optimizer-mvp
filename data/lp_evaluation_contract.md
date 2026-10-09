# LP_EVALUATION_CONFIG_V1

Artifact type: `SYNTHETIC_EVALUATION_CONFIGURATION`. Every configuration, shock and result is `MODELLED` / `SYNTHETIC_EVALUATION_ONLY`. This dataset is a mathematical experiment, not runtime configuration, admission, a quote, market evidence or public deployment proof. The capstone requires no public deployment; none is planned. Exactly Jaine and Oku are present. W0G remains an auxiliary execution asset.

## Configuration contract

| Fields | Meaning / validation |
|---|---|
| config_id | Version + strategy + SHA256 of sorted compact JSON containing every other field; changing range, fee, orientation, target or reference price changes identity. Decimal strings are hashed verbatim; equivalent alternate spelling deliberately creates a different identity. |
| strategy_id, venue, router_mode | Jaine / JAINE / V1 or Oku / OKU / ROUTER02, independently configured. |
| chain_id, chain_role | 16661 / INTENDED_EVALUATION_DOMAIN; network intent, not deployment proof. |
| evidence_class, label | MODELLED / SYNTHETIC_EVALUATION_ONLY required. |
| w0g, usdce, token0, token1 | Nonzero distinct lowercase address pair, with explicit order. Existing external token references from the Iteration 18 architecture only. Synthetic reverse ordering is a mathematical test and does not claim an actual pool factory ordering. |
| w0g_decimals, usdce_decimals | Explicit 18/6 model scales for these experiments; no fresh on-chain read. |
| price_orientation | USDC.e_PER_W0G, the human economic basis. |
| pool_price_orientation | ATOMIC_TOKEN1_PER_TOKEN0, including decimal conversion; bounds and ticks use this basis. |
| fee_tier | Positive integer below 1,000,000, in millionths. Synthetic fee metadata; not a claim of a factory-supported tier and not included in stress income/cost. |
| tick_spacing, tick_lower, tick_upper | Positive spacing, aligned ordered ticks within [-887272,887272]. |
| sqrt_lower, sqrt_upper | Positive ordered decimal sqrt(1.0001^tick); must match ticks within 1e-55 relative rounding tolerance. Not Q96 encoded or a contract parameter assertion. |
| reference_price | Positive finite decimal string, USDC.e per W0G. Assumption, not observation. |
| composition_rule, target_usdc_bps | RANGE_IMPLIED_FULL_NOTIONAL. All notional enters the mathematical position; actual inventory is derived from range/reference price. Target is the nearest integer bps of its USDC.e value share, validated against that derivation. It is a diagnostic of composition, not a separate rebalance instruction. No assumed 50/50 split or residual cash. |
| notional_convention | USDC.e_VALUE; USDC.e=1_MODELLED_USD. No external price evidence is implied. |
| pool_context, notes | Strategy-specific synthetic position context and assumptions. No pool address, adapter, manager, vault or registration is selected. |

The loader rejects a runtime artifact; the runtime loader rejects this artifact. The stress entry point requires explicit synthetic mode and the expected configuration identity. No optimizer or evidence-ingestion path imports this dataset.

## Mathematical contract: V3_RANGE_INVENTORY_V1

Let q be the atomic token1/token0 price, a=sqrt(q_lower), b=sqrt(q_upper), s=sqrt(q), and L the normalized liquidity. Atomic quantities x=token0 and y=token1 are:

| Region | x | y | Status |
|---|---|---|---|
| s <= a | L(1/a - 1/b) | 0 | BELOW_RANGE |
| a < s < b | L(1/s - 1/b) | L(s-a) | IN_RANGE |
| s >= b | 0 | L(b-a) | ABOVE_RANGE |

This is a continuous V3 inventory model, excluding fees. Ticks and sqrt bounds are internally consistent. It does not emulate integer TickMath/Q96 rounding or the adapter's execution transaction.

For economic price p (USDC.e per W0G), let d0/d1 be token0/token1 decimals. If W0G is token0, q=p*10^(d1-d0). If W0G is token1, q=(1/p)*10^(d1-d0). Convert x,y to whole tokens by dividing by their respective powers of ten, then map to W0G and USDC.e. A +20% shock always means p_s=1.2*p, even when q decreases because ordering is inverted.

Compute unit-L inventory (w_unit,u_unit) at p0. For notional N, set L=N/(w_unit*p0+u_unit), then recompute initial inventory (w_initial,u_initial). This deterministically invests the full notional. Initial position may be below/in/above range; neither inventory nor the HODL comparator assumes 50/50.

| Quantity | Definition / sign |
|---|---|
| V_initial | w_initial*p0 + u_initial |
| V_LP(p_s) | w_stressed*p_s + u_stressed |
| V_HODL(p_s) | w_initial*p_s + u_initial; initial inventory held unchanged |
| LP-vs-HODL difference | V_LP - V_HODL, in modelled USDC.e value |
| IL | V_LP/V_HODL - 1; negative means LP underperformance, not total portfolio loss |
| Absolute LP stress loss | max(0,(V_initial - V_LP)/V_initial) |
| HODL market loss | max(0,(V_initial - V_HODL)/V_initial) |
| Market value change | V_HODL - V_initial, signed |
| Rebalancing value change | V_LP - V_HODL, signed |
| LP value change | Market value change + rebalancing value change = V_LP - V_initial |

The last decomposition is an accounting identity, not independent stochastic events. Loss fractions need not add because denominators and zero floors differ. USDC.e depeg, liquidity withdrawals by other actors, discontinuous prices, fee accrual, execution impairment and probabilities are outside this primitive.

Decimal calculations use local precision 60 and ROUND_HALF_EVEN, independent of ambient precision/rounding. All configuration/shock/notional inputs and numeric outputs are decimal strings; no float conversion enters calculation or identity. Boundary snapping at relative 1e-55 only removes Decimal sqrt/inversion rounding noise; this is far smaller than a tick, not an economic tolerance. Display tables round outputs for readability; JSON retains calculation precision. Reject non-finite values, nonpositive prices/notionals and inverted ranges.

## Deterministic shocks: LP_SHOCKS_V1

| Scenario ID | Economic 0G shock | Meaning | Evidence class |
|---|---|---|---|
| LP_SHOCKS_V1:DOWN_20 | -0.20 | p_s=0.8*p0 | MODELLED / SYNTHETIC |
| LP_SHOCKS_V1:DOWN_10 | -0.10 | p_s=0.9*p0 | MODELLED / SYNTHETIC |
| LP_SHOCKS_V1:UP_10 | 0.10 | p_s=1.1*p0 | MODELLED / SYNTHETIC |
| LP_SHOCKS_V1:UP_20 | 0.20 | p_s=1.2*p0 | MODELLED / SYNTHETIC |

LP_SHOCKS_V1:REFERENCE_ZERO (shock 0) is a versioned test diagnostic; excluded from the four-shock results. Scenario ID and exact shock string must match. These are experiments, not forecasts, with no probabilities.

## Separation from economics and future risk aggregation

| Quantity | Iteration/model | Included in LP stress? | Included in ordinary economics? |
|---|---|---|---|
| LP fee return | 19 return evidence | No | Yes, when qualified |
| Entry slippage | 19 quote evidence | No | Yes, separately |
| Exit slippage | 19 quote evidence | No | Yes, separately |
| Lifecycle gas/cost | 19 cost evidence | No | Yes, separately |
| Market price move | 20 range primitive | Yes, signed market exposure | Not an added expected-income stream |
| Inventory rebalance | 20 range primitive | Yes, new inventory | Not added again |
| IL | 20 range primitive | Diagnostic relative to HODL; already reflected in LP value | Not a duplicate cost |

Range stress describes position-value behavior under price movement. Quote/slippage/cost economics remain separate execution effects. Projected fee income is excluded from stressed position value. The primitive establishes neither admission/capacity, economic evidence quality, executable quote validity nor public deployment proof. It is not integrated into current portfolio-risk constraints.
