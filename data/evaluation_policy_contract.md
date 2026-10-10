# EVALUATION_POLICY_V1

Final capstone evaluation scope is `DECISION_SLEEVE`. This is an explicitly `SYNTHETIC_EVALUATION_ONLY` policy, not a production investment mandate. The optimizer allocates only the native-0G amount explicitly designated for the current run. Whole-portfolio state acquisition is not required for final capstone completion under DECISION_SLEEVE; it remains future work. Public deployment is neither required nor planned.

## Scope contract

| Dimension | Final scope | Included? | Reason |
|---|---|---|---|
| Decision amount | Explicit native-0G capital supplied for this run | Yes | Sole optimized principal |
| Existing holdings | Exogenous | No | No acquisition or inference; not added to principal |
| Existing pending withdrawals | Outside optimized state | No | Previous decisions are not this sleeve |
| Existing LP NFTs/positions | Outside optimized state | No | New synthetic LP evaluation is not a whole-vault rebalance |
| Existing staking/restaking balances | Exogenous | No | No inferred delegated or remote balances |
| Idle decision capital | Unallocated remainder of designated principal | Yes | Immediately available native 0G, zero stress and exit delay |
| Existing vault idle | Outside unless explicitly designated as decision amount | Conditional designation only | No automatic addition to new capital |
| Whole-portfolio compliance | NOT_ASSESSED | No | Sleeve concentration/risk checks cannot establish whole-portfolio compliance |

The policy interface has no holdings/pending-exit input; extra fields cannot silently enter principal. Existing compatible result fields remain intact. decision_amount_0g and decision_value are explicit analysis inputs, with modelled valuation inherited from Iteration 19; their provenance is not a current price claim.

## Evaluation policy matrix

| Constraint | Conservative | Balanced | Aggressive | Measure | Evidence/policy class |
|---|---|---|---|---|---|
| max_strategy_concentration | 0.40 | 0.60 | 0.80 | Each positive sleeve strategy weight; idle excluded | Existing frozen profile values |
| max_slashing_stress_loss | 0.02 | 0.05 | 0.10 | Iteration 21 weighted underlying Native/Gimo staking loss budget | Existing thresholds; MODELLED stress inputs |
| max_decision_sleeve_lp_absolute_stress_loss | 0.05 | 0.10 | 0.20 | Weighted worst absolute LP loss across LP_SHOCKS_V1 | SYNTHETIC_EVALUATION_ONLY policy limits |
| max_portfolio_lp_il_stress | 0.02 (legacy) | 0.05 (legacy) | 0.10 (legacy) | Old generic IL-style measure | Compatibility only, not a final policy constraint |
| Allocation gate | Ascend zero | Ascend zero | Ascend zero | Positive Ascend rejected | Canonical CLOSED gate preserved |
| Cash deadline | Optional | Optional | Optional | Time after exit decision to native 0G | Explicit MODELLED timing, fail closed when required |
| Bridge exposure | No new blocking rule | No new blocking rule | No new blocking rule | No invented user-capital bridge exposure | Remote dependency is not a capital bridge |

The new LP measure includes total position value loss, not IL alone. Its own monotonic 5%/10%/20% namespace makes evaluation tolerance transparent. These limits are not empirical probabilities, historical VaR or calibrated production limits. The old threshold field is untouched. Common Native/Gimo 5% severity remains an independent benchmark, not a shared causal event. No LP loss or Ascend haircut is added to the staking threshold.

## Cash-deadline contract

Holding horizon != time-to-cash != cash deadline. Holding horizon is invested duration for expected economics; time-to-cash starts after an exit decision; cash_deadline_days is the optional maximum acceptable value of the latter. It is a finite nonnegative decimal string in days. It never changes APY, profit or stress severity.

| Condition | State | Candidate consequence |
|---|---|---|
| No deadline | NOT_REQUESTED | No deadline rejection; all exit states may remain unresolved |
| Positive allocation, qualified synthetic time <= deadline | COMPATIBLE_MODELLED | Deadline passes, including exact equality |
| Positive allocation, time > deadline | INCOMPATIBLE_MODELLED | FAIL; allocation is not feasible |
| Positive allocation, missing/unqualified time | UNRESOLVED | Fail closed; allocation is not feasible |
| Zero weight | NOT_REQUIRED_ZERO_WEIGHT | Does not block even if timing is missing |
| Idle | Time-to-cash=0 | Compatible with every valid nonnegative deadline |

Only EXIT_LIQUIDITY_V1 native-0G typed results with explicit synthetic mode, MODELLED timing and ASSESSED_MODELLED qualification qualify a requested deadline. Source-only synchronous LP topology is insufficient. Missing stages do not become zero. The stage semantics remain those of Iteration 21. No production liquidity or quote success is inferred.

## Feasibility contract

`evaluation_policy.assess` requires versioned policy, named profile, positive decision amount/value, positive holding horizon, exact five-strategy decimal-string weights, exact idle weight, five risk/exit entries (entries may be unavailable), and explicit synthetic mode. Weights plus idle must equal exactly one. Extra holdings fields are unsupported. Missing zero-weight risks/timing do not block the idle option.

The typed PolicyResult contains policy version/fingerprint, scope, profile, weights, idle, amount/value, horizon/deadline, each constraint state/value/limit, per-strategy deadline state, unresolved required constraints, overall PASS/FAIL/UNRESOLVED, rejection reasons, binding constraints, risk budget, risk/exit identities and source identity. No composite risk score is produced. FAIL takes precedence when a known violation or prior admission/economics rejection exists; otherwise unresolved required evidence returns UNRESOLVED. Only PASS is feasible. Binding constraints include failed/unresolved constraints and exact concentration/stress limit boundaries.

Iteration 21 aggregate supplies weighted staking and LP absolute budgets using actual allocation value=decision value × exact weight. Absolute losses scale with value, while stress fractions remain configuration-specific. Positive missing LP risk is unresolved; the generic IL proxy is never a fallback. IL and HODL market loss are not added to total LP loss. At precision 60, frozen risk V1's loss/allocation round trip can differ from its original range fraction by a final decimal ulp. Policy validates agreement within 1e-55 and canonicalizes only that ratio back to the range fraction for exact aggregation; it preserves the original input fingerprint. This rounding tolerance is not a feasibility-limit tolerance.

An analysis_only_closed_gate_override may allow hypothetical Ascend risk diagnostics; it never changes gate feasibility. Every positive Ascend candidate is FAIL, and the amount-aware metadata gate already rejects it before policy search. All-idle remains PASS for valid top-level inputs without positive required constraints.

## Amount-aware integration

`run_amount_optimizer` accepts optional evaluation_policy_mode, evaluation_policy_fn (a per-stage provider) and cash_deadline_days. The final path requires SYNTHETIC_EVALUATION_ONLY for both policy and Iteration 19 economics and an economics provider. Providing a deadline without this mode is rejected. Named frozen profiles are required; arbitrary custom profile values cannot override final policy limits.

1. Existing strategy gates, exact-amount admission and economics run first. Ineligible points never enter policy search, and their original rejection reasons remain visible.
2. The original candidate_grid constructs exact same point weights. Complete candidate sleeves are enumerated using the same objective and deterministic tie-break.
3. The prepared policy stage scales risk to actual candidate values and assesses the complete sleeve. Non-PASS sleeves are skipped. Point-level candidate.eligible still describes admission/economic eligibility; complete-sleeve policy feasibility is a distinct assessment.
4. Feasible sleeves retain the unchanged expected-net-profit ranking. Risk and deadline are constraints, not objective penalties. Fixed lifecycle costs and exact amount-specific quotes remain Iteration 19 behavior.
5. Selected admission/economics points are revalidated as before. A new policy stage snapshots source data and repeats the full selected sleeve assessment, including all-idle selections. Any failed state, invalid identity or changed policy/risk/LP/exit/deadline fingerprint suppresses the recommendation. No retry or silent replacement occurs.

A stage's policy/risk/LP/exit configuration snapshot is explicit and deterministic; per-amount risk caching only exists inside it. A fresh snapshot is taken at revalidation. No live RPC, wall clock or probabilities are introduced. Decimal strings preserve candidate identities; legacy float weights remain the compatibility/grid interface.

Only the final synthetic path skips old risk/bridge/exit snapshot constraints; it still requires admitted economics and valid slippage. Default production and compatibility runs retain all previous behavior. In policy mode, serialization adds evaluation_policy and identifies the new risk basis; it omits legacy_stress from the recommendation to avoid implying that compatibility coefficients control final feasibility. Existing API/frontend entry points are unchanged and do not automatically enable this mode.

## Legacy separation matrix

| Legacy element | Final evaluation use | Legacy comparison use | Status |
|---|---|---|---|
| lp_stress_loss_20pct | Not a feasibility input; candidate snapshot remains compatibility diagnostic | Old weighted LP proxy | Preserved, never reinterpreted |
| MODELLED_LP_STRESS_20PCT | Never a final risk fallback | Old quote/proxy path | Preserved only in default/legacy path |
| max_portfolio_lp_il_stress | Not used | Old IL-style threshold | Existing values unchanged |
| max_exit_time_days | Not used as optional deadline | Old snapshot exit-time screen | Existing values unchanged; new deadline is explicitly supplied |
| Legacy linear optimizer | No new policy integration | Future compatibility comparison | Untouched |
| Amount-aware default | No automatic policy enablement | Existing compatibility coefficients | Preserved; production remains idle |

Canonical runtime/admission/economics datasets and the frozen LP configurations remain unchanged. Whole-portfolio acquisition, final experiment matrix, dashboard, README/proposal reconciliation and public deployment are outside this iteration.
