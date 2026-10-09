# Iteration 13 — amount-aware decision-sleeve foundation

No existing-position acquisition, funding-origin treatment, freshness TTLs, live collector run, new stress calibration or dashboard/proposal changes. Exactly five structural strategies remain. Ascend's gate is CLOSED. The original linear optimizer and pipeline are unchanged.

## A. Architecture

| Aspect | Legacy linear benchmark | Amount-aware foundation |
|---|---|---|
| Economics | Coefficient calculated at full decision notional | Net profit calculated separately at each actual candidate amount |
| Options | Continuous strategy weights | One tested discrete option per strategy, including zero |
| Fixed USD lifecycle costs | Included in full-notional coefficient then scaled by weight | Existing fixed-USD convention charged once per positive candidate; zero costs at zero |
| LP quotes | Full notional, skipped if slippage prefilled | Always quote supported positive points, ignoring prefilled slippage |
| Capacity | liquidity_usd proxy ceiling | Explicit point admission; no TVL/reserve/NAV capacity fallback |
| Solver | scipy linprog | Exhaustive deterministic feasible-option enumeration |
| Validation | No selected-amount second check | Reevaluate selected points; any changed/failed result invalidates recommendation |

Entry/exit quotes use the existing whole-strategy-notional loss convention. Exit inventory is a current-target proxy, not predicted future-position inventory. Registered adapter/config binding remains unresolved and is explicitly labelled NOT_ESTABLISHED. Quotes do not alone establish protocol admission or a maximum capacity.

## B. Grid/search

Weights are 0, 0.1, 0.2, ... up to the selected profile's concentration ceiling, plus the exact ceiling if off-grid. Existing 40/60/80% ceilings are represented exactly: at most 5/7/9 options per strategy. Diagnostic rows include closed-gate positive options as rejected; the search only receives its zero option.

The present four conditional routes yield upper search bounds of 5^4=625, 7^4=2401, 9^4=6561 combinations before filtering. General five-member bound is 11^5=161051 when an explicitly supplied 100% profile is used. Off-grid custom ceilings add at most one boundary option without interpolation.

Weight/constraint tolerance: 1e-10. Profit tie tolerance: USD 1e-8 absolute. Tie-break: greater profit beyond tolerance, then less deployed capital, then lexicographic weights favouring earlier strategy metadata registration. No synthetic risk score. Idle is the exact residual (floating-point dust clamped at zero). One option per strategy; no interpolation/extrapolation of quote points.

## C. Candidate contract

| Field | Meaning |
|---|---|
| strategy_id, weight | Independent strategy and tested sleeve fraction |
| amount_0g, amount_usd | Actual candidate native-0G quantity/reference value |
| net_profit_usd, net_return_horizon, net_apy | Current return-engine calculation at that amount; null if unavailable |
| fixed_execution_cost_usd | Sum of known legacy USD lifecycle costs at the positive point; zero for zero |
| technical_admission, admission_evidence | SUPPORTED/UNSUPPORTED/UNKNOWN, explicit point identity/source/mechanism/evidence class and optional scalar headroom |
| runtime_execution | NOT_TESTED / NOT_REQUIRED / TESTED_PROXY / SNAPSHOT_PROXY / FAILED |
| eligible, rejection_reasons | Current candidate checks, not live-capital certification |
| quote_context | Tested amount, price, fee/output context, current snapshot notes and unresolved config/exit-inventory boundaries |
| legacy exposure coefficients | Existing slippage, delay, dependency and stress inputs only |

Default admission is UNKNOWN. A provider must explicitly identify strategy, exact amount, chain and evidence basis. A separately supplied scalar bound is validated but never inferred. MODELLED support is for explicit demo/test assumptions, not live headroom. The provider integration boundary is not a new live admission collector.

## D. Capacity reconciliation

| Strategy | Old proxy | New treatment | Repository-only positive support |
|---|---|---|---|
| Native | Sampled delegation depth | Explicit admission point/bound required | Unknown; no configured-validator headroom captured |
| Gimo | Backed TVL | Explicit admission point/bound required | Unknown; TVL/rate history insufficient |
| Jaine | Pool reserves | Admission and amount quote are separate | Unknown admission; quote alone insufficient |
| Oku | Pool reserves | Same separation, own quote route | Unknown admission; quote alone insufficient |
| Ascend | SourceCore NAV | CLOSED gate before positive evaluation | Blocked regardless of capacity/economics |

StrategyManager depositCap / currentAssets checks exist in Solidity, but there is no qualified corresponding Python runtime admission capture. Do not infer those values from source/config examples. Vault maxAllocationBps and holdings are not acquired here.

## E. Costs

Known gas/bridge/deposit/withdrawal USD fields retain the existing engine's fixed-per-positive-route convention. Their actual provenance and fixed/variable decomposition remain unresolved; this convention is not a new empirical classification. Missing costs do not become zero and block positive candidates. Protocol fee/incentive components must be present; unresolved fee basis blocks admission. Slippage loss is amount × price × (entry+exit whole-notional rates). Management/performance fees retain existing amount/horizon formulas. No new withdrawal-fee or incentive-realization mechanism is invented.

P(0)=0; no admission provider or quote is called at zero. P(A>0) deducts the lifecycle sum once, not multiplied by weight. Receipt-rate protocol fees are not deducted twice. Incentives and yield assumptions in the demo remain explicitly MODELLED, not qualified live earnings.

## F. Synthetic LP verification

The executable demo uses A/100000 entry and A/80000 exit loss fractions, separately for each tested amount. These are artificial fixtures, not markets. Both Jaine and Oku at Balanced:

| 0G amount | Quote | Entry / exit loss | Status with synthetic point support |
|---|---|---|---|
| 100 | Attempted | 0.100% / 0.125% | Pass |
| 200 | Attempted | 0.200% / 0.250% | Pass |
| 300 | Attempted | 0.300% / 0.375% | Pass |
| 400 | Attempted | 0.400% / 0.500% | Pass |
| 500 | Attempted | 0.500% / 0.625% | Pass |
| 600 | Attempted | 0.600% / 0.750% | Pass |

Separate tests fail only one point; no passing point is extrapolated. Repository-only UNKNOWN admission skips quotes rather than requesting unnecessary live RPC state.

## G. Reproducible comparison

Run `python -m src.ascend_optimizer.amount_demo` for the corrected default or append `--synthetic-support` for explicit modelled admission/quote support. Both use committed demo snapshots, 1000 0G, assumed USD 1/0G and 90 days. No RPC calls. N=Native, G=Gimo, J=Jaine, O=Oku.

| Profile | Legacy weights / idle | Legacy profit USD | New repository-only weights / idle / profit |
|---|---|---|---|
| Conservative | N40 G40 / 20 | 14.974946 | None / 100 / 0 |
| Balanced | J60 G40 / 0 | 25.795213 | None / 100 / 0 |
| Aggressive | J80 O20 / 0 | 28.343056 | None / 100 / 0 |

The default difference is corrected admission semantics; all positive admission is unknown, not unlimited. This is an evidence limitation, not a solver malfunction.

| Profile | New synthetic-support weights / idle | New profit USD | Horizon net return |
|---|---|---|---|
| Conservative | N40 G40 J10 O10 / 0 | 22.854761 | 2.285476% |
| Balanced | G50 J20 O30 / 0 | 28.256943 | 2.825694% |
| Aggressive | G10 J40 O50 / 0 | 30.504786 | 3.050479% |

Synthetic differences reflect different amount-dependent LP costs, newly admitted tested points and discrete/aggregate constraints. The synthetic quote function differs from prefilled demo rates; these profit differences are not an isolated empirical solver-performance improvement. Legacy profit / 1000 gives its horizon return. Quotes: legacy 0 calls with prefilled snapshots; new synthetic 10/14/18 total calls (candidate + selected revalidation) for Conservative/Balanced/Aggressive. New default 0 calls. Native/Gimo per-point economics do not need LP quotes.

## H. Revalidation/serialization

Each positive selection repeats metadata admission, explicit technical-admission provider, exact-amount LP quote (where applicable), current profile/exposure checks, fee/cost/return calculation, and compares the resulting candidate with the tested option. Final metadata checks catch a gate closing during revalidation. Any change—even a quote still within limits—returns FAILED and recommendation=null. Proposed selections remain diagnostic only. No retries or fabricated idle replacement for the failed selection.

Eligible-zero is distinct from EXCLUDED; CLOSED remains GATED. Success is a numerical/modelled recommendation, never execution readiness or proof. Legacy sleeve risk coefficients remain approximations, not a new scenario engine.

Schema 1.3 optionally adds `amount_aware` via `legacy_run.to_dict(amount_aware=amount_run)`. Original portfolio/outcome fields continue to describe the legacy benchmark; the extension carries the new method/grid/candidates/selection/revalidation/recommendation and benchmark metadata. Decision amount, price, horizon, profile and fee context must match. This is an additive optional comparison, not a silent replacement of 1.3 field meanings. The API remains on its existing default legacy path; its contract guard/TypeScript types can carry the optional extension unchanged. No request method switch or dashboard rendering change.

## I. Deferred gaps

- PORTFOLIO_STATE: existing holdings/claims/idle/funding origin, actual vault value basis/maxAllocationBps and whole-portfolio constraints.
- FRESHNESS: TTLs, source/quote age and registered config/amount evidence validity beyond tested-point matching.
- RISK: exposure reconciliation, causal events/operator overlap and whole-portfolio aggregation.
- LP_STRESS: registered-position stress; future exit inventory; HODL/denominator migration.
- COST_PROVENANCE: actual costs, fixed/variable decomposition, withdrawal fees and financial incentive qualification.
- EVIDENCE: qualified admission headroom/point support and registered LP configuration; no new live evidence is supplied.
- DASHBOARD: eventual optional-result adoption and multidimensional rendering, not implemented here.
- PROPOSAL: eventual methodology/evaluation updates, not edited here.

## Validation

- New amount-aware tests: 27 passed.
- Focused optimizer/pipeline/serialization set: 63 passed.
- Full Python suite: 196 passed (one existing Gimo pandas FutureWarning).
- Actual API/subprocess contract tests: 6 passed.
- TypeScript typecheck and Next production build: passed.
- git diff --check: passed.

No tests were deselected; no original optimizer/pipeline tests were rewritten. Synthetic support is never installed as the default runtime admission provider.
