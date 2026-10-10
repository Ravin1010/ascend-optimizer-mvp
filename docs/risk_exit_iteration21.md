# Iteration 21: deterministic stress and time-to-cash

Iteration 21 uses deterministic modelled stress and exit assumptions for evaluation. It does not estimate event probabilities, prove live liquidity, or establish public execution readiness. The final evaluation harness has not been started.

## Strategy risk matrix

| Strategy | Primary stressed exposure | Stress model | Total loss measure | Diagnostics | Current limitation |
|---|---|---|---|---|---|
| Native | Synthetic delegated/pending staking value | One 5% severe benchmark | Exposure × 5% | Configured concentration and exposure split unresolved | No validator selected or observed slash data |
| Gimo | st0G underlying staking value | One 5% underlying loss | Exposure × 5%, no second protocol slash | Common severity, distinct causal ID | Protocol risk/distribution unresolved, no correlation claim |
| Jaine | Independent synthetic concentrated LP | Iteration 20 four-shock range path | Worst absolute LP loss | IL, HODL market loss, range state, LP/HODL difference | Synthetic config, not a registered range |
| Oku | Independent synthetic concentrated LP | Iteration 20 four-shock range path | Worst absolute LP loss | Independent reversed-token config, same diagnostics | Synthetic config, not a registered range |
| Ascend | Single SourceCore/a0G economic value | Illustrative 5% value haircut; dependency severity missing | Haircut once; dependency loss null | Embedded exposures not additive; queue/remote/oracle unknown | PARTIALLY_ASSESSED; allocation CLOSED |

## Synthetic stress results

Each allocation is 1,000 modelled USD-equivalent. LP values use the frozen Iteration 20 reference and USDC.e=1 assumption.

| Strategy | Scenario suffix | Exposure | Severity | Absolute loss | Loss fraction | State |
|---|---|---|---|---|---|---|
| NATIVE_STAKE_0G | NATIVE_STAKING_5PCT | 1000 | 0.05 | 50.000000 | 5.000000% | ASSESSED_MODELLED |
| GIMO_STAKE_0G | GIMO_UNDERLYING_5PCT | 1000 | 0.05 | 50.000000 | 5.000000% | ASSESSED_MODELLED |
| JAINE_LP_0G_USDC | LP_WORST_ABSOLUTE | 1000 | Direct range path / unresolved | 162.518804 | 16.251880% | ASSESSED_MODELLED |
| OKU_LP_0G_USDC | LP_WORST_ABSOLUTE | 1000 | Direct range path / unresolved | 120.632486 | 12.063249% | ASSESSED_MODELLED |
| ASCEND_STAKE_A0G | ASCEND_ECONOMIC_HAIRCUT | 1000 | 0.05 | 50.000000 | 5.000000% | PARTIALLY_ASSESSED |
| ASCEND_STAKE_A0G | ASCEND_DEPENDENCIES_UNRESOLVED | 1000 | Direct range path / unresolved | UNRESOLVED | UNRESOLVED | UNRESOLVED |

Both LP worst cases occur at LP_SHOCKS_V1:DOWN_20. Their total loss includes rebalancing and underlying market exposure; no IL or market loss is added again. All four shock results are preserved in diagnostics.

## Independent decision-sleeve budget

Five hypothetical allocations of 20% in a 5,000 value sleeve are used only to exercise the budget primitive. Ascend is included through an explicit CLOSED-gate analysis override, not a recommendation. The unresolved dependency-severity case is reported separately; using it at positive allocation instead blocks the total.

| Strategy | Weight | Loss fraction | Weighted contribution | Absolute loss |
|---|---|---|---|---|
| NATIVE_STAKE_0G | 20% | 5.000000% | 1.000000% | 50.000000 |
| GIMO_STAKE_0G | 20% | 5.000000% | 1.000000% | 50.000000 |
| JAINE_LP_0G_USDC | 20% | 16.251880% | 3.250376% | 162.518804 |
| OKU_LP_0G_USDC | 20% | 12.063249% | 2.412650% | 120.632486 |
| ASCEND_STAKE_A0G | 20% | 5.000000% | 1.000000% | 50.000000 |

Total independent stress-budget envelope: **433.151290 value / 8.663026%**. This is not an assumed simultaneous slash or a joint-event estimate. Unknown components remain outside this quantified sensitivity budget; overall risk clearance is not established.

## LP legacy migration and profile constraints

| Legacy element | Current meaning / use | New replacement | Migrated now? | Compatibility behavior / future cleanup |
|---|---|---|---|---|
| lp_execution.py: MODELLED_LP_STRESS_20PCT | Generic [0.8P0,1.2P0] worst IL proxy | risk_stress.py consumes config-specific V3_RANGE_INVENTORY_V1 worst absolute loss | New evaluation path only | Constant and old tests retained; remove only with explicit solver migration |
| exposure_engine.py: lp_stress_loss_20pct | Snapshot proxy resolution, non-LP zero behavior | Typed StressResult.loss_fraction for LP absolute loss | Evaluation only | Existing exposure/API columns unchanged; no alias/reinterpretation |
| optimizer.py: lp_stress_loss_20pct | Weighted proxy/IL constraint in legacy linear optimizer | Dedicated independent stress budget | No solver migration | Legacy linear optimizer still uses old proxy and old threshold |
| amount_optimizer.py: lp_stress_loss_20pct | Candidate exposure, fallback proxy and weighted old LP constraint | Dedicated range-aware result and aggregate | No solver migration | Amount-aware optimizer still uses old proxy; new module never accepts snapshot proxy overrides |
| pipeline.py: MODELLED_LP_STRESS_20PCT | resolve_runtime_lp_exposures fills missing generic proxy | Separate risk scenario replay | No | Old proxy remains compatibility-only |
| readiness.py: lp_stress_loss_20pct | Runtime-resolvable compatibility exposure | New assessment_state and risk limitations | Additive helper only | Existing readiness unchanged; no claim of full risk readiness |
| profiles.py: max_portfolio_lp_il_stress | Conservative .02 / Balanced .05 / Aggressive .10 old IL-style budgets | max_decision_sleeve_lp_absolute_stress_loss with explicit evaluation limit | No default/solver migration | No absolute loss fed to IL-named threshold; absent new limit is UNRESOLVED |
| max_slashing_stress_loss | Frozen .02/.05/.10 weighted staking-loss budget | Evaluation maps only underlying Native/Gimo staking budget under same dimensional semantics | Evaluation mapping only | Legacy solver unchanged; no correlation inferred, no Ascend haircut recast as another slash |
| max_bridge_exposure / concentration | Frozen bridge and strategy-weight constraints | Concentration checked against weights; bridge unassessed without exposure input | Mapping only | Remote dependency not automatically user-capital bridge |
| live_optimize.py / data_loader.py / API-result transport | Existing schema 1.3 proxy values and threshold diagnostics | Separate replay artifacts and typed modules | No transport change | Frontend/API compatible; future additive serialization requires explicit contract migration |

New risk helpers use the new absolute LP measure. Existing production/legacy optimizers use the old compatibility proxy. This is the explicitly chosen deferred-profile migration option, preserving semantics instead of relabelling old thresholds. The example new LP limit 0.10 is an explicit synthetic test input, not a new Balanced default.

## Exit results

| Strategy | Type | Request processing | Maturity wait | Incremental funding wait | Claim processing | Time-to-cash | Holding horizon | Class |
|---|---|---|---|---|---|---|---|---|
| NATIVE_STAKE_0G | ASYNCHRONOUS | 0 | 7 | 0 | 0.1 | 7.1 | 90 | MODELLED |
| GIMO_STAKE_0G | ASYNCHRONOUS | 0 | 10 | 0 | 0.1 | 10.1 | 90 | MODELLED |
| JAINE_LP_0G_USDC | SYNCHRONOUS | 0.01 | 0 | 0 | 0 | 0.01 | 90 | MODELLED |
| OKU_LP_0G_USDC | SYNCHRONOUS | 0.02 | 0 | 0 | 0 | 0.02 | 90 | MODELLED |
| ASCEND_STAKE_A0G | QUEUE_BASED | 0.1 | 7 | 7 | 0.1 | 14.2 | 90 | MODELLED |

All durations are illustrative days and have no observed timing provenance. Every canonical production time-to-cash is null. LP zero maturity/funding wait is source-path structure only; processing time, requestability and executable quotes remain unresolved in production. Ascend maturity, funding and claimability are separate; its gate remains CLOSED. No user cash-deadline optimizer input or ranking change is added.

## Reproduction and boundaries

```bash
python tools/risk_exit_preflight.py --kind risk --check results/risk_stress_iteration21.json
python tools/risk_exit_preflight.py --kind exit --check results/exit_liquidity_iteration21.json
python -m pytest -q tests/test_risk_exit.py tests/test_lp_range_stress.py tests/test_economics_evidence.py
python -m pytest -q
python tools/economics_preflight.py
python tools/audit_deployment_history.py --check
python tools/deployment_preflight.py
git diff --check
```

Without --check, stdout reproduces the committed JSON. No RNG, RPC, timestamps or blocks are supplied. The risk and exit artifacts are distinct from canonical evidence ingestion and runtime configuration. A fixed strategy order makes output independent of Python hash randomization.

The detailed risk scenario contract, exit stage contract and separation matrix are in data/risk_exit_contract.md. All frozen runtime/admission/economics datasets and Iteration 20 LP configurations remain byte-for-byte unchanged. Canonical production profiles remain 100% idle at the existing explicit replay as_of. No public deployment or fresh evidence acquisition is included. No dashboard, proposal, Solidity or frontend change is included. Iteration 22 and the final evaluation harness are not started.

## Validation record

- New risk/exit suite: **52 passed**.
- Iteration 20 LP suite: **64 passed**; Iteration 19 economics suite: **72 passed**.
- Combined focused suite: **188 passed**.
- Full Python suite: **604 passed** (one existing Gimo/pandas FutureWarning).
- Result-contract suite: **10 passed**; API contract suite: **7 passed**.
- Risk and exit committed artifacts replay exactly, without wall-clock or hash-order dependencies.
- Iteration 17 audit replay and Iteration 18 deployment preflight: passed.
- Frozen dataset comparison against accepted a02844c802c781cf056b79c59172d719aaaf990a: unchanged.
- Conservative/Balanced/Aggressive canonical repository replay: **100% idle**, empty economics, unresolved runtime/admission.
- `git diff --check`: passed.

Solidity/contracts and frontend/types were untouched; Hardhat and frontend build/typecheck were not run. Result/API checks were additional regression coverage; transport/schema remains unchanged.
