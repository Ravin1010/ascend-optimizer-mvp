# RISK_STRESS_V1 and EXIT_LIQUIDITY_V1

These additive primitives provide deterministic evaluation diagnostics. Every quantified stress and exit assumption in the new artifacts is `MODELLED` / `SYNTHETIC_EVALUATION_ONLY`. Missing severity/duration remains `MISSING` and `UNRESOLVED`, never zero. Source-fixed exit topology uses `STATIC_CONFIG` only for the code path, with a separately missing timing evidence class. No probabilities, event frequencies, historical VaR, covariance or forecasts are inferred. No public deployment is performed, planned or required.

## Risk scenario contract: RISK_SCENARIOS_V1

Each record requires exactly scenario_id, version, strategies, category, model, severity, evidence_class, label, meaning, exposure_basis and assumptions. Unknown/probability fields are rejected. The scenario's strategies/category/model are validated against its versioned identity. The three 5% cases are version-fixed benchmarks; changes need a new scenario version. Canonical JSON SHA256 fingerprints additionally identify the full parameters and assumptions. LP scenario provenance includes the unchanged Iteration 20 config fingerprint and all four shock results.

| Scenario ID (prefix RISK_SCENARIOS_V1:) | Strategy/categories | Exposure basis | Severity/model | Evidence class | Meaning |
|---|---|---|---|---|---|
| NATIVE_STAKING_5PCT | Native / staking loss | Full synthetic delegated/pending allocation, counted once | 5% severe staking benchmark | MODELLED | Independent staking-loss experiment; configured validator and delegated/pending split unresolved |
| GIMO_UNDERLYING_5PCT | Gimo / underlying staking loss | st0G underlying synthetic staking value | 5%, one causal loss | MODELLED | No additional Gimo slash; same benchmark as Native does not establish a shared event/correlation |
| LP_WORST_ABSOLUTE | Jaine and Oku / position value | Strategy-specific LP_EVALUATION_CONFIG_V1 initial value | Worst absolute LP loss across LP_SHOCKS_V1 | MODELLED | Four economic price shocks evaluated independently for each configuration; deterministic first-in-version-order tie break |
| ASCEND_ECONOMIC_HAIRCUT | Ascend / SourceCore value | Single a0G/SourceCore economic value | Illustrative 5% haircut | MODELLED | Sensitivity test, not calibrated operator/slash data; embedded Mellow/Symbiotic exposure counted once |
| ASCEND_DEPENDENCIES_UNRESOLVED | Ascend / dependencies | Queue/funding, remote and oracle/accounting dependencies | null | MISSING | Severity cannot be quantified; no zero default or risk clearance |

Only explicit synthetic mode accepts these scenarios. The current contract cannot ingest arbitrary observed risk claims: it rejects relabelling scenario records or modelled results as observed. Existing project evidence vocabulary (`LIVE_OBSERVED`, `LIVE_DERIVED`, `HISTORICAL`, `MODELLED`, `STATIC_CONFIG`, `MISSING`) remains intact; no new observed evidence is supplied here. A later observed package needs its own source/freshness qualification rather than changing these labels.

## Loss semantics

For staking and illustrative haircut cases, stressed exposure equals the explicitly modelled strategy allocation, and absolute loss = exposure × severity. Synthetic native/ST0G/a0G values use a modelled USD-equivalent value basis; this is not a qualified valuation capture. Configured Native concentration remains unresolved. Gimo-specific protocol risk remains unresolved. Ascend haircut covers only a named economic sensitivity, so its result is PARTIALLY_ASSESSED even when that component is quantifiable. All Ascend dependency severities remain null and its gate remains CLOSED.

LP results use V3_RANGE_INVENTORY_V1 directly: loss = allocation × worst absolute LP loss fraction, where absolute loss=max(0,(V_initial−V_LP)/V_initial). IL=V_LP/V_HODL−1 and HODL market loss are diagnostic attribution already reflected in V_LP. Neither is added to the absolute loss. The model also excludes projected fee income, quote/slippage impairment and lifecycle costs, which belong to Iteration 19 economics.

Each typed `StressResult` carries the strategy, scenario/version/fingerprint, category, exposure basis and amount, allocation value, severity (null for the direct LP model), absolute loss, loss fraction, evidence class, stress basis, assessment state, eligibility, provenance, diagnostics and limitations. Assessment states currently used: ASSESSED_MODELLED, PARTIALLY_ASSESSED and UNRESOLVED. No modelled assessment is called verified.

## Decision-sleeve aggregation

`aggregate` takes exactly five results and five exact decimal weights, plus an explicit positive decision-sleeve value. Weights must be in [0,1] and sum to at most one; idle remainder contributes zero. Each result allocation must match decision value × weight. Its fraction and absolute loss must be consistent and within the allocation. Duplicate strategy contributions are rejected, preventing a second underlying Gimo slash or second embedded Ascend contribution.

Weighted contribution = allocation weight × strategy loss fraction. Absolute contribution = decision value × weighted contribution. Total budget is their sum. A positive unresolved component makes total loss null/UNRESOLVED. A zero-weight unresolved component contributes zero while retaining unresolved severity. An explicit analysis-only override is required to include a positive CLOSED Ascend allocation; this never modifies the actual gate or makes the allocation a recommendation.

The aggregation rule is `INDEPENDENT_STRESS_BUDGET_ENVELOPE_NOT_JOINT_EVENT`. This is a sum of independent strategy-specific loss budgets for allocation comparison, not a simultaneous portfolio event, estimated correlation, or probability. LP worst cases can differ; Native and Gimo scenario IDs remain distinct. Unknown dependencies are not presumed safe because their quantified budget is absent. Overall risk clearance remains NOT_ESTABLISHED.

Profile mapping is an explicit evaluation helper, not a solver integration. Current strategy concentration and weighted underlying-staking loss thresholds retain their meanings. Remote dependency is not automatically user-capital bridge exposure. A new `max_decision_sleeve_lp_absolute_stress_loss` accepts an explicit synthetic limit; absent that limit the check is unresolved. There are deliberately no new profile defaults. The old `max_portfolio_lp_il_stress` is never fed absolute loss. Both optimizers continue to use their legacy compatibility risk constraints; migration of solver/profile defaults is explicitly deferred rather than silently changing threshold semantics.

Decimal strings preserve inputs and output values. Computation uses local precision 60 / ROUND_HALF_EVEN; no randomness, wall clock or RPC. Scenario fingerprints include exact input spelling. Zero allocation retains model severity/fraction but zero absolute loss, and no division by zero occurs.

## Exit model contract

| Strategy | Exit type | Request step | Waiting step | Claim step | Native-0G time-to-cash basis | Current canonical qualification |
|---|---|---|---|---|---|---|
| Native | ASYNCHRONOUS | Validator undelegation request | Unbonding/maturity | Validator processing and adapter claim into vault | Unresolved authoritative duration; explicit model durations allowed | UNRESOLVED |
| Gimo | ASYNCHRONOUS | st0G unstake/request | Pending maturity | stakePool.withdraw and adapter claim | Unresolved duration/busy state; one adapter outstanding request serialization | UNRESOLVED |
| Jaine | SYNCHRONOUS | Remove LP liquidity and swap to W0G | Source-fixed zero protocol wait | Unwrap W0G to native 0G | Processing/quote/transaction availability unresolved | PARTIALLY_ASSESSED path, UNRESOLVED time-to-cash |
| Oku | SYNCHRONOUS | Remove LP liquidity and Router02 swap to W0G | Source-fixed zero protocol wait | Unwrap W0G to native 0G | Processing/quote/transaction availability unresolved independently | PARTIALLY_ASSESSED path, UNRESOLVED time-to-cash |
| Ascend | QUEUE_BASED | SourceCore requestWithdrawal | Epoch maturity then funding | Claim W0G and unwrap to native 0G | Queue/maturity/funding/claim state unresolved | UNRESOLVED; CLOSED |

Source topology comes from the existing adapters listed in each result's provenance. Source path alone never establishes a configured route, current requestability or claimability. LP synchronous operation does not guarantee successful execution. Iteration 19 quote validity remains separately necessary for recommendation economics; these models do not create admission, quote or execution approval.

The synthetic configuration `EXIT_EVALUATION_V1` is separate from runtime configuration. It requires a stable strategy-specific ID, version, MODELLED label, explicit stage durations and assumption notes. Its full SHA256 fingerprint changes when durations/assumptions change. All durations are nonnegative finite decimal strings or null. Synthetic durations require explicit evaluation mode; production mode rejects them. LP maturity/funding waiting must be zero to preserve synchronous topology; request/claim processing latency may be modelled nonzero.

Time-to-cash starts at an exit decision and equals sequential request processing + maturity waiting + incremental funding waiting + claim processing. These are durations, not overlapping cumulative timestamps; the Ascend example deliberately models funding after maturity. Any missing stage duration makes total time unresolved. Requestability is separately assumed for evaluation, maturity and funding remain separate stages, and claimability is conditional on those stages and execution. No present-tense live stage state is claimed.

Holding horizon is only a separate diagnostic; it does not enter the exit-duration sum. The optional `deadline_compatible` helper is analysis-only and returns unresolved/compatible-modelled/incompatible-modelled; no user deadline input, ranking rule or optimizer constraint is added. Existing max_exit_time_days compatibility semantics remain unchanged.

## Separation matrix

| Dimension | Meaning | Expected return? | Stress? | Liquidity? |
|---|---|---|---|---|
| Expected APY | Ordinary qualified return assumption | Yes, Iteration 19 | Not added to stress values | No |
| Lifecycle cost | Entry/exit/claim monetary costs | Deducted in ordinary net economics | Excluded here | Does not determine waiting duration |
| Quote loss | Amount/context-specific execution impairment | Separate execution deduction | Excluded here | Separate execution feasibility, not time estimate |
| Slashing stress | Named exposure × severity | No duplicate expected-income deduction | One underlying loss budget | No inferred wait |
| LP absolute loss | Total range position loss vs initial value | No | Sole LP total-loss measure | No |
| IL | LP underperformance vs HODL | No | Attribution only, not additive | No |
| Market loss | Initial inventory price exposure | No | Attribution already in LP loss | No |
| Time-to-cash | Delay after exit decision to native 0G | Not holding-period APY | Not a loss severity | Yes, separately qualified |
| Holding horizon | Planned invested period | Return horizon | Does not change fixed shock severity | Separate from exit delay |

Technical admission and public deployment proof are independent of all these dimensions and remain unavailable in canonical repository runs.
