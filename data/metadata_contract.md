# Iteration 10 data contract

This contract reconciles frozen Iterations 1–9. It defines metadata, not optimizer algorithms, execution readiness, numeric capacity, freshness TTLs, or a new API contract.

## Dataset boundaries

- `strategies.csv`: seven retained strategy/dependency/opportunity rows; exactly five `optimizer_universe=TRUE` rows. Row count is not optimizer-universe size.
- `tracked_records.csv`: auxiliary, observed-excluded and future records. Never concatenate this inventory into optimizer candidates. All membership values are FALSE.
- `strategy_snapshots.csv`: unchanged numeric schema and blank measurements; staged rows are not fresh observations. Morpho's deployment is observed but no usable market measurements exist.
- `demo_strategy_snapshots.csv`: unchanged synthetic evaluation fixtures. Dates, fees, costs and stress values are demo assumptions, not live captures or authoritative calibration. Embedded-restaking fixture return must never become independent income.
- `source_registry.csv`: collection/source mechanism metadata. All existing URLs, source IDs and historical `last_verified_utc` values are preserved. Those dates are historical registry review/reference dates, not upstream observation or new retrieval timestamps.

## Strategy status dimensions

| Column | Meaning | Used values |
|---|---|---|
| record_role | Economic record type | INDEPENDENT_STRATEGY, EMBEDDED_DEPENDENCY, OBSERVED_OPPORTUNITY |
| reconciliation_category | Frozen structural category | INTEGRATED_ALLOCATABLE, INTEGRATED_GATED, EMBEDDED_NON_ALLOCATABLE, OBSERVED_EXCLUDED |
| protocol_availability | Protocol existence; no claim of capstone transactions or usable market | LIVE; DEPLOYED_MARKET_UNRESOLVED for Morpho |
| integration_status | Capstone path implementation boundary | IMPLEMENTED, EMBEDDED, NOT_INTEGRATED |
| optimizer_universe | Membership, independent of readiness or positive allocation | TRUE, FALSE |
| allocation_gate | Baseline admission state, not an execution guarantee | CONDITIONAL, CLOSED, NOT_APPLICABLE |
| gate_requirements | Pipe-separated evidence dimensions; necessary, not a claim they pass | required data, fee/cost basis, freshness, config, amount, admission, exit and policy; Ascend also risk/withdrawal/history |
| evidence_readiness | No fresh run validation is performed here | NOT_ASSESSED, INCOMPLETE, NOT_APPLICABLE |
| runtime_feasibility | Candidate amount/config context has not been tested here | NOT_ASSESSED, NOT_APPLICABLE |
| live_capstone_proof | Entry-to-exit proof boundary | NOT_ESTABLISHED for all five; NOT_APPLICABLE for non-independent rows |

INTEGRATED_ALLOCATABLE means candidate-universe membership conditional on evidence, runtime and policy checks. It does not mean live-capital suitability. Ascend is LIVE + IMPLEMENTED + INTEGRATED_GATED + CLOSED; its gate is not merely a 24-hour-history requirement. Jaine's legacy exclusion is removed; this does not waive runtime checks. Morpho is observed/deployed on 0G but not integrated, with market ID blank/unresolved.

## Chain, asset and path columns

| Column | Exact meaning |
|---|---|
| network / chain_id | Legacy contextual deployment network, not a universal supported/user/execution-chain label. Morpho: observed 0G deployment; embedded row: SourceCore context. |
| execution_chain_id | Configured capstone strategy-execution chain, 16661 for the five; blank for embedded/Morpho, never fabricated. |
| dependency_chain_ids | Pipe-separated underlying dependency chain IDs. Ethereum 1 under Ascend; not independently routed user capital. |
| parent_strategy_id | Embedded exposure's independent parent; ASCEND_RESTAKE belongs to ASCEND_STAKE_A0G. |
| internal_assets | Internal conversion/inventory assets, not alternate current user inputs. |
| position_asset | Persistent economic position: validator shares, st0G, a0G or pooled V3 NFT. Receipt shares are not 1:1 0G aliases. |
| user_bridge_required | User-controlled routing distinction: FALSE for the five. |
| protocol_managed_remote_exposure | Dependency existence indicator, not a capital fraction; TRUE under Ascend. |
| legacy_liquidity_meaning | Explicit interpretation of current snapshot liquidity_usd proxy, not technical capacity. |
| capital_path | Structural entry/exit sequence; final native 0G settles to vault idle before wallet withdrawal. |

Native 0G is current configured input. W0G is an internal representation in the same economic family and a target alternate input. LP inventory target is derived during deployment/planning and then fixed per registered pool/fee/ticks/targetUsdcBps. Runtime quote/planner state is not proof of registered configuration alignment. Ethereum is backing/security dependency; Galileo is conditional development/test only (W0G unresolved); Base is KIV. Mainnet addresses must not be reused for Galileo.

## Legacy compatibility

| Field | Temporary interpretation | Deferred migration |
|---|---|---|
| execution_status | Coarse legacy protocol/data bucket; LIVE_INCOMPLETE is not structural exclusion. Morpho uses LIVE_INCOMPLETE only as a compatibility bucket alongside explicit DEPLOYED_MARKET_UNRESOLVED. | Consumers must use distinct dimensions. |
| technical_eligibility | Engine compatibility adapter: Jaine ELIGIBLE_WITH_RUNTIME_CONSTRAINTS; Ascend EXCLUDED_LIVE_DATA_INCOMPLETE keeps its closed gate; embedded EXCLUDED_EMBEDDED; Morpho EXCLUDED_OBSERVED_UNINTEGRATED. | Explicit universe/gate/evidence/runtime checks replace string-prefix semantics. |
| bridge_required | Legacy underlying dependency hint for Ascend; not user bridging. | Separate user routing, remote backing, transport and slashable exposure. |
| bridge_fraction | Residual-NAV exposure proxy under Ascend; accounting populations unresolved. | Reconcile SourceCore NAV versus funded/burned queue populations before exact exposure use. |
| liquidity_usd | Native sampled delegation depth; Gimo backed TVL; LP reserve USD; Ascend NAV. Never technical capacity/exit cash. | Separate admission headroom, amount-specific depth and async readiness. |
| exit_time_days | Nominal legacy delay, not complete time-to-cash or guaranteed exit. | Requestability, maturity, funding, claimability and uncertainty. |
| entry/exit_slippage_rate | Fee-inclusive whole-strategy-notional quote loss at tested amount/context. | Candidate-amount/config alignment and future exit inventory assumptions. |
| optional cost fields | Missing remains economically unknown, even though current engine defaults some blanks to zero. | Explicit observed/quote-derived/modelled/structural-zero/measured-zero/missing states. |
| data_status | Coarse snapshot description; LIVE_* does not prove per-field validity. | Field-level evidence/provenance and validity. |

TVL is observed existing scoped value, not an allocation ceiling. LP reserves additionally enter fee-return derivation. Technical capacity can include protocol admission and strategy depositCap; user capital, vault maxAllocationBps (actual vault basis/existing holdings), and profile limits are separate. No capacity values are created here.

## Source metadata

| Column | Meaning |
|---|---|
| chain_ids | Source-relevant chain IDs; Ethereum references remain dependencies, not current optimizer execution. |
| source_role | PROTOCOL_REFERENCE, MARKET_OBSERVATION, RETURN_HISTORY, EXECUTION_QUOTE, WITHDRAWAL_STATE, INCENTIVE_OBSERVATION, DEPENDENCY_REFERENCE or MODEL_ASSUMPTION. |
| mechanism_evidence_class | Mechanism-level LIVE_OBSERVED, LIVE_DERIVED, HISTORICAL, MODELLED or STATIC_CONFIG; not certification of a supplied fresh capture. |
| freshness_class | RUN_TIME_FRESH, PERIODICALLY_FRESH, TIME_SERIES_REQUIRED, DEPLOYMENT_CONFIG_STATIC, PROTOCOL_STATIC or MODEL_ASSUMPTION. Numeric TTLs unresolved. |
| amount_specific | Mechanism yields amount-specific observations, e.g. quotes. FALSE does not waive later amount-dependent readiness evaluation. |
| config_specific | Interpretation needs source/configuration alignment; TRUE does not prove current alignment. |
| history_required | APY derivation requires multiple qualified observations; one exchange-rate read is insufficient. |
| capture_status | NO_FRESH_CAPTURE_SUPPLIED for every retained source. No fresh observations generated. |

Deferred per-capture extensions: upstream observation time, retrieval time, block/hash, historical window, derivation/model version, configuration identity (chain/adapter/pool/fee/range/target), tested amount and valuation basis, cost state, validity reason and assumption provenance. Static source registry alone cannot provide those dynamic facts. Existing source URLs are retained references, not newly reverified links.

Source coverage gaps remain for Morpho's exact usable market, iAI investable route, Bond/Zia verified exit routes and qualified Ascend backing/queue population/target composition. No new external source or evidence date is fabricated. `tracked_records.source_coverage=GAP` flags unsupported coverage; EXISTING_REPOSITORY_REFERENCE denotes repository/config/reference presence, not live execution proof.

## Risk/return provenance

- Native/Gimo retained 5% double-sign-inspired severe-staking number is MODELLED severity, not probability/current Mainnet parameter or evidence of shared validator/operator events. Gimo backing composition is unresolved. Operator-event aggregation requires verified overlapping claims; Ascend linkage cannot be inferred.
- LP +/-20% generic range stress is MODELLED versus HODL starting inventory, with stressed-HODL denominator; it is not absolute capital loss or registered-position stress.
- Ascend residual proxy x 5% is an uncertain-exposure MODELLED scenario, not exact slashable loss or guaranteed conservative bound.
- Gimo/a0G rate-derived appreciation is NET_OF_PROTOCOL_FEES. Do not deduct embedded fees again or count Ascend/Symbiotic return twice. Native commission basis remains unresolved. LP pool APR is a proxy; incentives require realization qualification.
- Expected returns and adverse deterministic stress remain separate. Unknown is never semantically zero, unlimited or eligible.

## Downstream contract gaps (not implemented)

1. Exposure/readiness/pipeline consumers still interpret legacy status/prefixes, not all new dimensions; row count includes non-universe records. Compatibility exclusions preserve Ascend/embedded/Morpho gates.
2. Pipeline still quotes full decision amount, skips prefilled quotes, has no maximum-age enforcement, may discover a different range/target than registered adapters, and uses fixed return coefficients.
3. Optimizer uses liquidity_usd as capacity, legacy delay and dependency/stress coefficients, and sleeve-only weights rather than post-existing-plus-new portfolio positions.
4. Net-return engine defaults optional missing costs to zero; native fee basis and incentive realization still need reconciliation.
5. live_optimize serialization/API/TypeScript/dashboard do not carry new metadata dimensions, funding origin, existing/pending holdings, separate horizon/deadline, field-level provenance, configuration or proof states. No API/type/dashboard changes are made here.
6. Dashboard obsolete Jaine/Morpho reason mappings, raw coefficient versus portfolio headroom comparisons, unconditional concentration explanation and exit-time percent formatting remain future work.
7. a0G history is absent at the inspected commit, not currently gitignored; absence does not prove it was never collected locally. History-path ignore cleanup remains deferred.

## Validation boundary

Schema validation rejects duplicate/unknown references, malformed metadata values and frozen-universe/gate contradictions. It does not enforce freshness, execute quotes, clear gates, validate live contract deployments or supply portfolio evidence. Full test results are reported in the Iteration 10 completion response.

### Iteration 10 validation results

- `python -m src.ascend_optimizer.main`: passed; seven metadata rows/seven staged snapshot rows.
- Explicit `load_source_registry`, `load_tracked_records` and demo `load_snapshots` validation: passed; 31 sources, ten non-candidate records, seven demo snapshots.
- Focused `python -m pytest -q tests/test_data_loader.py tests/test_exposure_engine.py tests/test_pipeline.py tests/test_live_optimize.py tests/test_readiness.py` with the following six stale behavioral assertions explicitly deselected: **48 passed, six deselected**.
- Broader `python -m pytest -q`: **138 passed, six failed**. The six failures are preserved downstream contract expectations, not schema failures or redefinitions of the frozen baseline:
  - `tests/test_pipeline.py::test_demo_balanced_allocation`
  - `tests/test_pipeline.py::test_demo_aggressive_allocation`
  - `tests/test_pipeline.py::test_pipeline_annotates_profile_specific_eligibility`
  - `tests/test_live_optimize.py::test_json_exposes_per_strategy_constraint_headroom`
  - `tests/test_readiness.py::test_readiness_separates_return_and_exposure_gaps`
  - `tests/test_readiness.py::test_static_jaine_liquidity_exclusion_precedes_runtime_quote_gap`
- These assertions assume the removed blanket Jaine metadata exclusion and its resulting synthetic allocation/headroom. They are not rewritten in this data/schema-only iteration. No optimizer, API, serialization or dashboard behavior is changed to make them pass.
- Direct metadata tests cover exact membership, closed Ascend gate, Morpho deployment/unresolved market, preserved non-candidate inventory, forbidden gate/universe/config contradictions, source references and missing proof/capture states.
- Numeric/timestamp preservation check against the base commit passed for both snapshot CSVs; all 31 source IDs/URLs/historical review dates are unchanged. `git diff --check` passed.
- One existing pandas FutureWarning occurs in the Gimo history test; unrelated collector refactoring is deferred.
