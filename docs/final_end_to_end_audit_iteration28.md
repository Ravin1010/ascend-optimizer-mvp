# Iteration 28 — Final End-to-End Capstone Audit

**Audit decision: NOT_READY_FOR_FINAL_FREEZE**

Verification-only audit of the approved/frozen capstone. No finding was corrected. Iteration 29 was not started.

- Audit date: **11 October 2026 (UTC)**.
- Repository: [Ravin1010/ascend-optimizer-mvp](https://github.com/Ravin1010/ascend-optimizer-mvp).
- Branch: `main`.
- Repository HEAD audited: `f2d71c7b6765a60c98c38ce415a8cc028eef8a7c`.
- Initial working tree: **clean**.
- Proposal: [Proposal Initial Draft](https://docs.google.com/document/d/1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4/edit).
- Exact native Google Docs revision read and subsequently reconfirmed:
  `AHj4eMSmWCq2SxRHOc6mFngaSY3McI0Il8k3b7S5Mt7mjVIK16TY9Idt4pfuD8WiEh28YtVuUPb05T-CTn91CbJYIsd1glJX8zRWWNXamHw`.
- Proposal mutations during this audit: **none**.
- Findings: **0 BLOCKER / 1 MAJOR / 1 MINOR / 3 OBSERVATION**.

The reproducible results, five-strategy universe, advisory application boundary and production abstention are intact. Final freeze is withheld because the final amount-aware path still enforces legacy fixed profile slippage ceilings contrary to the stated final-policy separation, and the full Python suite retains a stale documentation-freeze test. These are recorded below, without changing code, tests, policy, proposal or results.

## 1. Audit method and claim boundaries

The audit combined source inspection, canonical metadata/configuration inspection, existing local tests, exact artifact replay, native proposal readback and a fresh PDF export with visual inspection. Source implementation, tested local behavior, modelled evaluation, external protocol availability, runtime binding, production evidence and public deployment proof were assessed separately.

No RPC, market-data acquisition, transaction submission, wallet creation or deployment was performed. No probability model or additional benchmark scenario was introduced. One temporary, in-memory synthetic candidate was used solely to reproduce finding F1; it was not written into any repository data or benchmark artifact.

Dashboard verification used its existing actual API subprocess tests, parser tests, server-rendered component tests, CSS/source inspection, TypeScript check and production build. A manual interactive browser/mobile walkthrough was not performed. This audit is not a security certification, operational-liquidity assessment or fresh verification of external protocol facts.

## 2. Repository lineage and freeze integrity

The starting HEAD matched the requested SHA exactly. `git merge-base --is-ancestor` confirmed descent from `9fc56a883b8030540a7790fa24b48c1dbc7a7e97`. The direct parent-to-head TOC diff contains only `docs/proposal_toc_finalization.md`.

| Commit | Frozen milestone |
| --- | --- |
| f2d71c7 | Native TOC finalization audit only |
| 9fc56a8 | Narrow 27A figure/future-work correction audit |
| 2758a10 | Approved proposal reconciliation application audit |
| 2c9071a | Iteration 27 repository-side reconciliation draft |
| 4bbe78d | Iteration 26 current-facing documentation and asset-family helper |
| 8749d0a | Schema 1.4 canonical metadata correction |
| 7933258 | Iteration 25 current-request API/dashboard migration |
| a786d63 | Iteration 24 frozen report package |
| 7abfa1a | Iteration 23 presentation-precision correction |
| 8e214fa | Iteration 23 four-method benchmark |
| 0d85089 | Iteration 22 evaluation-policy integration |
| 432e2ed | Iteration 21 deterministic risk/exit primitives |
| a02844c | Iteration 20 range-aware LP primitive |
| b9c8bf9 | Native base-return qualification correction |

Later documentation-only commits did not overwrite production source or frozen artifacts. Source and metadata inspection confirmed the later policy/schema additions while preserving compatibility namespaces. Finding F1 is an existing semantic inconsistency, not a change introduced by this audit.

All **232 previously tracked files** were unchanged against the audited HEAD before writing this report. Iteration 23 source hashes and all **33 payload hashes** in the Iteration 24 manifest matched; the generator's **34-file** package count also includes its manifest. The relevant canonical data/configuration and frozen results remain unchanged against their accepted freeze points as exercised by existing tests and replay guards.

### Test/build side effects

Next.js production build automatically regenerated `frontend/next-env.d.ts` and `frontend/tsconfig.json`; TypeScript created `frontend/tsconfig.tsbuildinfo`. These generated changes were restored/removed to return exactly to HEAD bytes. They were not retained or committed. An initial concurrent deployment audit/Python run encountered this transient generated-file mismatch; the deployment audit and clean-source Python suite were subsequently rerun. No defect was repaired in that process.

Only this new audit document is intended for the audit commit. No existing repository file is changed.

## 3. Local tests, builds and actual GitHub state

| Existing command/check | Passed | Failed | Skipped | Result / duration |
| --- | ---: | ---: | ---: | --- |
| `python -m pytest -q`, final clean-source run | 997 | 1 | 0 | 998 tests; 62.44 s; F2 |
| Application + result contract: `tests/test_application_contract.py tests/test_result_contract.py` | 74 | 0 | 0 | 10.20 s; includes schema 1.4 and compatibility/invariance checks |
| Asset/docs, policy, risk/exit, LP, economics, final evaluation/results focused modules | 423 | 0 | 0 | 36.91 s; subset of full suite |
| Clean isolated rerun of stale proposal-freeze test | 0 | 1 | 0 | 0.03 s; F2 reproduced without generated frontend files |
| `npm run contracts:test` | 72 | 0 | 0 | Complete Hardhat suite; 6 s |
| `node --test tests/*.test.ts` in frontend | 58 | 0 | 0 | 7.00 s; both existing test files |
| `npm run test:contract` in frontend | 7 | 0 | 0 | Compatibility subset; 3.26 s; included in the 58 |
| `npm run typecheck` | — | — | — | Passed; exit 0 |
| `npm run build` | — | — | — | Passed; five static pages generated; both API routes present |
| Deployment-history audit `--check` | — | — | — | Passed after restoring generated build files |
| Deployment preflight | — | — | — | Passed; design/static validation only |
| `git diff --check` | — | — | — | Passed before final staging |

Focused/subset test counts overlap the complete suites and must not be added to them.

The first concurrent Python run reported **996 passed / 2 failed**: the transient generated-file mismatch and the stale documentation test. The final sequential clean-source run removed the transient cause and left **997 passed / 1 failed**. No failure was waived or repaired.

One pandas concatenation FutureWarning remains. npm reports an environment `http-proxy` warning and Node reports existing module-type detection warnings; neither caused a test/build failure. An attempted focused command named a nonexistent `tests/test_frontend_contract.py` and collected no tests; it was replaced with the actual Python contract files and the existing frontend tests. That command-selection error is not a repository test failure.

### GitHub CI versus local checks

At the audited SHA, actual GitHub API reads returned:
- commit status contexts: **0**;
- check runs: **0**;
- Actions workflow runs filtered by the exact SHA: **0**.

The repository has no tracked `.github/workflows` directory. The connector's PR-only workflow wrapper also returned no runs; the general Actions API was queried separately to avoid inferring all-event absence from that limited wrapper. **No GitHub CI success is claimed.** Post-commit status will be queried and reported separately in the completion response.

## 4. Assets, chains and strategy universe

### Asset/chain model

`asset_normalization.py`, `data/strategies.csv`, README/current state, application contract and proposal Sections 4.0.1/7.1/7.2 agree on:
- native 0G as current decision input, idle representation and common cash-output asset;
- native 0G and W0G as one economic asset family, with distinct execution representations;
- W0G as internal ERC-20 representation, not an independent yield source or sixth strategy;
- direct W0G and ETH/BTC/broader input normalization as future/KIV;
- st0G/a0G as receipt/share representations and USDC.e as an LP execution/position asset.

The helper is deliberately outside valuation/search logic. It does not assert a universal observed 1:1 price oracle or perform wrapping.

| Chain/domain | Current meaning | W0G identity treatment |
| --- | --- | --- |
| 0G Mainnet 16661 | Intended strategy execution domain | `0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c`, EXTERNAL_PROTOCOL_REFERENCE |
| Galileo 16602 | Conditional development/test only | No address; UNRESOLVED_NOT_VERIFIED |
| Ethereum 1 | Underlying protocol/security dependency | No independent optimizer routing or address substitution |
| Base 8453 | Deferred/KIV | No current execution-domain promotion |

Supplying the Mainnet address for Galileo fails closed in the helper. No new chain verification or deployed-address claim was made.

### Independent strategies

Canonical source is `data/strategies.csv` interpreted through `StrategyState`; schema 1.4 derives these dimensions rather than reconstructing category from gate.

| Strategy | Canonical category | Gate | Structural candidate | Integration |
| --- | --- | --- | --- | --- |
| NATIVE_STAKE_0G | INTEGRATED_ALLOCATABLE | CONDITIONAL | true | IMPLEMENTED |
| GIMO_STAKE_0G | INTEGRATED_ALLOCATABLE | CONDITIONAL | true | IMPLEMENTED |
| JAINE_LP_0G_USDC | INTEGRATED_ALLOCATABLE | CONDITIONAL | true | IMPLEMENTED |
| OKU_LP_0G_USDC | INTEGRATED_ALLOCATABLE | CONDITIONAL | true | IMPLEMENTED |
| ASCEND_STAKE_A0G | INTEGRATED_GATED | CLOSED | true | IMPLEMENTED |

All five canonical protocol-availability fields are `LIVE`, explicitly meaning the external protocol availability metadata, not capstone runtime/deployment proof. Exactly five strategies appear in API/evaluation; idle is separate. `INTEGRATED_CONDITIONAL` is absent from the final adapter/frontend contract.

Embedded Ascend Mellow/Symbiotic remains EMBEDDED_NON_ALLOCATABLE; Morpho/iAI remain OBSERVED_EXCLUDED in the current taxonomy; standalone Symbiotic is KIV_FUTURE; W0G/Bond/Zia/reference assets are AUXILIARY_NOT_STRATEGY. Not every ecosystem label is an allocation-data row: the CSV has only the relevant excluded/embedded records in addition to the five members. None creates a sixth candidate.

Native and Gimo paths use native input/output. Jaine/Oku have independent wrap/LP/unwind/unwrap paths; Jaine uses V1 and Oku ROUTER02. Ascend's intended SourceCore/a0G request/epoch/funding/claim path remains gated.

## 5. Optimizer, economics and evidence

### Primary search

`application_contract.py`, `amount_optimizer.py`, `evaluation_policy.py` and existing regression tests establish:
- primary method POLICY_AWARE_AMOUNT_OPTIMIZER;
- DECISION_SLEEVE, existing positions EXOGENOUS_NOT_OPTIMIZED, whole-portfolio NOT_ASSESSED;
- fixed 0.1 weight-grid increments, subject to each profile concentration ceiling;
- Decimal candidate amount identity before the numerical compatibility boundary;
- technical admission and economics before final policy assessment;
- explicit all-idle option;
- expected-net-profit ranking among eligible/feasible combinations;
- deterministic tie-breaking and exact selected-point revalidation;
- evidence/economic/route identity and policy/risk/exit/config/deadline changes fail closed.

Existing production/legacy compatibility paths retain their old fields. The final synthetic policy path skips the legacy bridge, IL-proxy and fixed exit-duration budgets, and uses the new LP absolute-loss measure. **The fixed legacy slippage screen is not skipped: see F1.** No final solver reverted to the linear algorithm.

TVL is not automatically executable capacity: the repository admission provider requires configuration-bound evidence, and unknown admission does not trigger an LP quote as a substitute for capacity. Zero-weight structural-zero calculations do not qualify missing evidence for positive weights.

### Economics and accounting

`economics_evidence.py`, `net_return_engine.py`, evidence contracts and tests preserve:
- distinct return, quote and lifecycle-cost records with source/provenance;
- exact amount/context quote applicability and separate observation/retrieval timestamps;
- source/metric-specific freshness policy boundaries; missing current policies fail closed;
- no reuse of admission's 300-second policy as a universal economics/quote TTL;
- required missing return/cost/quote evidence is not numerical zero;
- structural zero requires an explicit basis;
- fixed cost once per positive lifecycle and amount-dependent/variable cost scaling;
- horizon conversion separate from exit delay;
- Gimo net exchange-rate return avoids a second protocol-fee deduction;
- Native configured-validator role qualification applies to the base return only; commission metadata has its own qualified role;
- Ascend embedded yield counted once, LP share/NAV/fee growth not added again as separate reward income;
- non-financial points excluded from financial APY.

`RewardAccounting.sol` expressly limits notification to separately claimable rewards, with user-share checkpointing before share changes. The source cannot itself prove that a future notifier's economic classification is correct; no public reward stream or registration is claimed.

Evidence classes remain LIVE_OBSERVED, LIVE_DERIVED, HISTORICAL, MODELLED, STATIC_CONFIG and MISSING, with typed unresolved/validity states. Historical/modelled evidence does not become current observed evidence. Admission, economic qualification, risk, exit and deployment proof remain distinct.

## 6. Deterministic risk, final profiles and liquidity

`risk_stress.py`, `lp_range_stress.py`, `exit_liquidity.py`, their artifacts and tests establish:
- RISK_STRESS_V1 / RISK_SCENARIOS_V1 / EXIT_LIQUIDITY_V1;
- Native severe staking benchmark 5%, MODELLED;
- Gimo underlying staking stress once; same severity is not a shared event/correlation assumption;
- LP_SHOCKS_V1 economic shocks -20%, -10%, +10%, +20%;
- V3 range inventory with explicit token orientation and Decimal model inputs;
- worst absolute LP position loss is the LP budget measure;
- IL, initial-inventory HODL market loss and LP-vs-HODL difference remain attribution diagnostics, not extra losses;
- quote loss, lifecycle costs and projected LP fee income are excluded from the mathematical stress value;
- Ascend illustrative 5% economic haircut plus unresolved embedded/backing/queue/remote/oracle dependency severity; no gate opening;
- independent stress-budget envelope, not a correlated joint-event scenario;
- remote dependency is not automatically user-capital bridge exposure.

No probability, VaR, covariance/correlation calibration or opaque composite risk score is introduced.

### Versioned final policy artifact

| Constraint | Conservative | Balanced | Aggressive |
| --- | ---: | ---: | ---: |
| Strategy concentration | 40% | 60% | 80% |
| Weighted staking stress | 2% | 5% | 10% |
| LP absolute stress | 5% | 10% | 20% |
| Cash deadline | Optional request | Optional request | Optional request |

EVALUATION_POLICY_V1 labels these SYNTHETIC_EVALUATION_ONLY, not calibrated production risk limits. The artifact has no final bridge/old IL/fixed exit/slippage thresholds. Legacy bridge 10/25/50%, IL 2/5/10% and exit 7/30/90 days do not control final policy-mode combinations. Nevertheless the earlier candidate stage still applies legacy slippage 0.5/1/3% (F1), so the policy table is not a complete description of implemented final feasibility.

### Exit/cash semantics

| Strategy | Source-level path | Synthetic time-to-cash | Canonical current timing |
| --- | --- | ---: | --- |
| Native | Undelegate, maturity, claim; ASYNCHRONOUS | 7.1 days | UNRESOLVED |
| Gimo | Request unstake, pending period, withdraw; ASYNCHRONOUS | 10.1 days | UNRESOLVED |
| Jaine | Remove/collect/swap, W0G unwrap; SYNCHRONOUS | 0.01 days | PARTIALLY_ASSESSED path; timing unresolved |
| Oku | Independent remove/collect/swap, unwrap; SYNCHRONOUS | 0.02 days | PARTIALLY_ASSESSED path; timing unresolved |
| Ascend | Request, epoch/queue/funding, claim W0G, unwrap; QUEUE_BASED | 14.2 days, analysis only | UNRESOLVED; CLOSED |

These values are modelled stage sums, not guaranteed protocol durations. Holding horizon, exit decision, time-to-native-0G and optional cash deadline are distinct. Positive unresolved timing fails closed when a deadline is required; zero-weight unresolved strategies do not block; idle has zero delay. NOT_REQUESTED, COMPATIBLE_MODELLED, INCOMPATIBLE_MODELLED and UNRESOLVED remain typed. Synchronous protocol operation does not prove successful execution or qualified quotes.

## 7. Runtime, deployment and production replay

All five `runtime_strategy_config.json` records remain `verification_state=UNRESOLVED`, with no canonical deployed configuration identity. `admission_evidence.csv` is headers-only. Return/LP-quote/lifecycle-cost JSON datasets each have **0 records**.

Deployment audit replay passed provenance, pinned history and frozen-file checks. Preflight returned:
- INTENDED_DEPLOYMENT_ARCHITECTURE;
- STATICALLY_VALIDATED source structure;
- five strategies / chain 16661;
- UNRESOLVED_RUNTIME_BINDING;
- NOT_DEPLOYED;
- public_deployment_required=false.

The frozen accessible-evidence finding remains NO_RECOVERABLE_CAPSTONE_DEPLOYMENT. The audit did not search for new public deployments or reinterpret protocol references/local tests as deployment records.

Direct canonical production runs at explicit `as_of=2026-10-11T00:00:00+00:00`, 1,000 native 0G and 90-day horizon returned:

| Profile | Recommendation | Idle | Positive-admission explanation |
| --- | --- | ---: | --- |
| Conservative | KEEP_IDLE | 100% | NO_MATCHING_CAPTURE / TECHNICAL_ADMISSION_UNKNOWN; Ascend CLOSED |
| Balanced | KEEP_IDLE | 100% | Same typed fail-closed evidence boundary |
| Aggressive | KEEP_IDLE | 100% | Same typed fail-closed evidence boundary |

This follows admission/configuration/economics qualifications, not a newly added all-idle override. API valuation is MISSING; its numerical placeholder does not qualify production evidence. Execution readiness/public proof remain NOT_ESTABLISHED. Public deployment remains NOT_REQUIRED_NOT_PLANNED and is not a capstone milestone.

## 8. API/dashboard and contract/source architecture

### Application

Schema 1.4 at `/api/decision-sleeve` exposes decision amount, profile, holding horizon, optional cash deadline and explicit mode. Production is default. Five strategy diagnostics and idle remain present. Missing measurements use typed states with null values, rather than fabricated zero.

Canonical category, gate, structural candidate, integration, protocol availability, runtime configuration, current recommendation, economics/policy feasibility, readiness and public proof remain separate. Parent-response equivalence tests preserve all non-metadata fields. Schema 1.3 and `/api/optimize` remain compatibility-only. Current-input legacy comparison is explicitly LIMITED and does not claim final range-risk/deadline support.

The dashboard renders the current request, with scope/synthetic banners, idle as a valid outcome, final LP absolute-stress namespace, modelled liquidity, typed reasons and separate readiness/proof. Ascend stays visible as CLOSED with zero allocation. Source/tests show no Iteration 24 figure/table/finding imports or hard-coded benchmark statistics. CSS provides wrapping, expandable diagnostics and narrow-screen rules. No transaction submission UI or whole-portfolio rebalance is introduced.

The otherwise correct risk panel does not disclose the retained legacy slippage ceiling that can reject candidates (F1); raw rejection diagnostics can contain PROFILE_SLIPPAGE_LIMIT.

### Contract source

Inspected AscendVault, StrategyManager, RewardAccounting and adapters, with all 72 local Hardhat tests passing:
- vault deposits enter user idle balances; registered routes require user-authorized allocation;
- manager registration validates adapter/input asset/withdrawal mode; owner controls registry and hard caps;
- vault checks active routes, deadlines, minimum shares, deposit and per-user allocation caps;
- allocation/deposit pause controls do not imply a universal withdrawal halt;
- asynchronous request ownership, stored minimum output and claim accounting remain explicit;
- accounting binds vault/manager, checkpoints user shares and separately claimable streams;
- adapters restrict their entry points to the configured vault and protect returned shares/output.

The optimizer has no privileged custody/execution role or private key. These are source/local-test capabilities, not deployed instances. A0GToken/AscendStakingAdapter remain reference/pre-launch artifacts in architecture/proposal; generic RestakingAdapter/connector does not expand the five-strategy universe. AscendProtocolAdapter checks external SourceCore/W0G/queue/share relationships but has no established public runtime registration.

## 9. Evaluation replay and frozen results

| Replay | Frozen result |
| --- | --- |
| `python tools/run_final_evaluation.py --check` | Exact replay: 49 scenarios / 196 rows |
| `python tools/generate_final_results.py --check` | Exact replay: 7 tables / 8 figures / 34 generated files |

The four actual methods remain Highest Yield, Equal Weight Eligible, Legacy Linear and Policy-Aware Amount; wrappers call the existing legacy solver and the existing policy-aware amount search. Shared synthetic inputs and capability differences remain explicit.

Core matrix: **27 scenarios / 108 rows**. Targeted: **22 scenarios**. All 196 rows carry SYNTHETIC_EVALUATION_ONLY; all five weights plus idle sum exactly to one; Ascend is zero throughout.

| Method | Recommendation rows | Idle rows |
| --- | ---: | ---: |
| HIGHEST_YIELD_BASELINE | 45 | 4 |
| EQUAL_WEIGHT_ELIGIBLE_BASELINE | 45 | 4 |
| LEGACY_LINEAR_OPTIMIZER | 35 | 14 |
| POLICY_AWARE_AMOUNT_OPTIMIZER | 36 | 13 |

Direct recalculation from accepted rows confirmed:
- amount-aware/legacy allocation differences **27/49**;
- any-method disagreement **39/49**;
- common rescore signs **19 positive / 7 negative / 23 zero**;
- mean amount-minus-legacy common-rescore delta **43.395279634804… USD**, report display **+$43.40**;
- median **$0**;
- diagnostic driver counts MULTIPLE=26, OBJECTIVE_DIFFERENCE=1;
- paired fixed-cost sensitivity count=1, quote sensitivity count=1;
- LP absolute-stress/concentration/staking/deadline diagnostic scenario counts **34/31/13/4**.

Disagreement is not profit improvement. The common exact-allocation post-selection rescore is not necessarily either method's selection objective; legacy selection-objective comparability is LIMITED. No universal or percentage superiority claim is supported. Only FIXED_100 versus FIXED_ZERO_CONTROL and QUOTE_CURVE versus QUOTE_CONSTANT_CONTROL are controlled within-model sensitivities. Other contributors remain diagnostic associations.

The results are exactly reproducible **including the retained slippage screen**. F1 does not authorize changing them: any separately approved semantic correction must assess consequences for the frozen benchmark and claims.

### Fingerprints checked

| Frozen source | SHA-256 |
| --- | --- |
| Iteration 23 raw JSON | 746d2e77b19c5f701e6171902b4902f414c6ad4098691fdb493abd1ab60c08ee |
| Iteration 23 CSV | cee106705b5622766c0080a64d8318e83c83ca7b36a3dc8a6c0618b6a6f9f75d |
| Iteration 23 summary | 215f2d17a1af41ffc112395333c8a298110771532c389b3c06b22be420523da0 |

Config/contract source hashes and all 33 nonmanifest output hashes also matched the Iteration 24 manifest; exact replay verified the complete 34-file package. No artifact was regenerated in place.

## 10. Proposal, protected text and PDF layout

Fresh native readback and a subsequent revision-only read both matched the exact approved revision. The proposal contains one native TableOfContents, **61 entries**, **18 native tables** and **21 inline images**.

Section 1.0 heading-to-next-section SHA-256:
`18f83624a62184e2cc32316e89de8f3f70a8d1a4d9fbea28880a01c1a12478a0`.

It matches the preserved Objectives hash in all accepted application/correction/TOC audits. Section 1.0 remains unchanged; its broad original multi-asset/cross-chain objectives are not evidence that those capabilities were delivered. Later sections explicitly bound the final native-0G implementation.

Approved title, Project Proposal and June 2026 remain. Sections 1–8 and Appendix A remain in order. Sections 4–8 state native input, five strategies/categories/gates, W0G internal, decision sleeve/exogenous holdings, NOT_ASSESSED, fail-closed production, synthetic evaluation, advisory dashboard and deployment-free boundaries. The exception is the fixed-slippage policy wording identified in F1.

Figure 4.1 ends in Current-Request Advisory Result. Figures 5.1/5.3 use source-level/intended terminology, unresolved runtime and Ascend CLOSED; the stale live/on-chain terminal labels were not observed. Technical wrap/share/queue/claim/unwrap paths remain intact.

Section 8.6 explicitly defers observational economics/freshness, direct W0G, ETH/BTC/broader multi-asset inputs, whole-portfolio optimization, standalone Symbiotic and future public/live execution or deployment. It states none are current implemented capabilities and deployment is not required for completion.

### Report integration

Native cell matrices matched each selected frozen Markdown table after whitespace normalization:
- main: capabilities (16 rows including header), disagreements/common rescore (11), causal-versus-diagnostic (11);
- appendix: complete representative scenarios (61), evaluation matrix (10).

Visual inspection confirmed six approved report images: representative allocations, fixed cost, quote curve, profiles, deadlines and common-rescore delta. Outcome-count/frequency and constraint-count figures/tables are absent from the selected native table/image set. The excluded outcome and diagnostic counts were not inserted as proposal charts.

### Fresh PDF export

- **53 pages**, matching approved final export.
- SHA-256: `cd3c883dffc5db78fa6ae2949ce3e8816f37d79a31ffbf591558921b2a047c45`.
- Fresh export is byte-for-byte identical to the TOC-finalization export.
- TOC pages **2–3**, Objectives page **4**.
- **61/61** TOC page references independently matched the corresponding heading text.
- All-page geometry scan: **0 out-of-page text/image blocks; 0 completely blank pages**.

Rendered pages inspected: **1–4, 21, 23, 25, 28, 35–43, 45–46 and 53**. These cover title/TOC/Objectives, Figures 4.1/5.1/5.3, profile table, Section 6 tables/figures/limitations, Section 8.6 and appendix start/end. No material clipping, distortion, detached caption or overlapping element was observed. Existing compact tables wrap identifiers across lines, and some tables continue across pages; see F3. No cosmetic edit was made.

## 11. Contextual claim-strength review

Relevant current-facing README/state/application/findings documents and proposal text were searched for live, production, deployed, ready, real-time, real, current APY, guaranteed, optimal, best, proof, cross-chain and multi-asset; occurrences were interpreted in context.

| Claim/context | Assessment |
| --- | --- |
| Canonical protocol availability LIVE | Valid narrow external-protocol metadata; explicitly separated from capstone proof |
| “not live capital management”, “no execution-ready proof” | Appropriately qualified negative boundaries |
| Reference Multi-Asset Vault / generic ERC-20 Solidity support | Valid source/reference architecture; does not expand native-only optimizer request |
| Original Objectives and external restaking/satellite background | Preserved historical/background scope; later applicability boundaries are explicit |
| Future cross-chain/multi-asset/W0G inputs | Appropriately deferred, not current implementation claims |
| “optimal routes” in unchanged Objectives | Original objective, not demonstrated global optimum; discrete-grid limitation stated later |
| Modelled APYs, stress and exit times | Explicit synthetic labels; not current APY or guaranteed liquidity |
| Profit delta / 27-of-49 disagreement | Qualified deterministic matrix/common-rescore diagnostics; not empirical superiority |
| Proposal 4.4 legacy slippage restricted to reference optimizer | **INCONSISTENT** with final candidate source and accepted diagnostics; F1 |
| Illustrative external reward dollar conversions | Explicit user-approved illustrative basis, not corroborated market capture; F4 |

Historical iteration documents remain scoped to their freeze points. Their older live/proxy terminology is not relied upon as current execution evidence. No newly unqualified deployment, live-capital performance, empirical probability or current general multi-asset routing claim was found in the current-facing material inspected.

## 12. Cross-artifact consistency matrix

Cells give status plus narrow supporting evidence; no source-implementation state is promoted to live proof.

| Domain | Source code | Canonical data/config | API/dashboard | Evaluation | Proposal | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Native-0G current input | CONSISTENT: asset helper/request | CONSISTENT: capital paths | CONSISTENT: Decision Amount | CONSISTENT: native notionals | CONSISTENT: 4.0.1/7.2 | CONSISTENT |
| Five-strategy universe | CONSISTENT: exact member guard | CONSISTENT: five TRUE rows | CONSISTENT: five diagnostics | CONSISTENT: five weights | CONSISTENT: 4.1/6.1 | CONSISTENT |
| Ascend CLOSED | CONSISTENT: gate rejection | CONSISTENT: CLOSED | CONSISTENT: gated/zero | CONSISTENT: 196 zero rows | CONSISTENT: source-level/gated | CONSISTENT |
| W0G internal role | CONSISTENT: distinct representation | CONSISTENT: internal paths | CONSISTENT: no selector/strategy | CONSISTENT: LP internals | CONSISTENT: auxiliary/KIV input | CONSISTENT |
| Decision-sleeve scope | CONSISTENT: policy/request | CONSISTENT: scope artifact | CONSISTENT: exogenous/NOT_ASSESSED | CONSISTENT: scope label | CONSISTENT: later scope sections | CONSISTENT |
| Production fail-closed | CONSISTENT: evidence guards | CONSISTENT: empty/unresolved | CONSISTENT: typed idle | CONSISTENT: production baseline | CONSISTENT: no live evidence | CONSISTENT |
| Risk-policy semantics | INCONSISTENT: legacy slippage screen remains | CONSISTENT: final typed budgets | PARTIAL / N/A: displays final budgets, raw slippage reason | INCONSISTENT: final rows inherit legacy screen | INCONSISTENT: says slippage reference-only | INCONSISTENT: F1 |
| Exit/deadline semantics | CONSISTENT: separate primitives | CONSISTENT: modelled stage durations | CONSISTENT: typed timing/deadline | CONSISTENT: deadline cases | CONSISTENT: modelled qualification | CONSISTENT |
| Deployment-free boundary | CONSISTENT: no optimizer execution role | CONSISTENT: runtime unresolved | CONSISTENT: proof NOT_ESTABLISHED | CONSISTENT: no execution claim | CONSISTENT: not required/planned | CONSISTENT |
| Synthetic labels | CONSISTENT: explicit mode checks | CONSISTENT: labels/empty production | CONSISTENT: prominent mode | CONSISTENT: all 196 labelled | CONSISTENT: prose/captions | CONSISTENT |
| Final result counts | PARTIAL / N/A: harness source | CONSISTENT: frozen inputs | PARTIAL / N/A: not benchmark UI | CONSISTENT: exact replay/counts | CONSISTENT: matched tables/text | CONSISTENT |

## 13. Severity-classified findings

### F1 — MAJOR: legacy fixed slippage ceilings still affect final-policy candidates

**Evidence:** `src/ascend_optimizer/amount_optimizer.py`, candidate block immediately before `PROFILE_SLIPPAGE_LIMIT`, applies `profile.max_entry_exit_slippage` regardless of evaluation_policy_mode. `profiles.py` supplies 0.005/0.01/0.03 for Conservative/Balanced/Aggressive. The final EVALUATION_POLICY_V1 artifact has no such constraint. Proposal Section 4.4 (PDF page 23) says legacy bridge, slippage, IL and exit-delay limits retain compatibility meaning in the reference optimizer. The Iteration 28 frozen-policy requirement expressly excludes fixed slippage limits from final profile constraints.

**Reproduction:** with existing synthetic primitives only, Balanced, decision 1,000 0G, horizon 365 days, Jaine weight 0.1, modelled entry/exit quote loss 0.011 per direction, technical admission SUPPORTED and expected net profit **$16.80**, evaluate_candidate returns **eligible=false**, solely **PROFILE_SLIPPAGE_LIMIT**. No data file was changed.

Accepted Iteration 23 policy-aware rows already expose this rejection in **8 scenarios**: CORE_CONSERVATIVE_10000_30/90/365, CORE_BALANCED_10000_30/90/365, FIXED_10000 and QUOTE_CURVE. This is not merely dead compatibility code or hypothetical wording.

**Impact:** the stated final-policy table omits an operative feasibility screen; the application and frozen benchmark inherit it. This does not alter or disprove exact reproduction, but it prevents a complete code/proposal policy-consistency conclusion. It also limits claims about mechanisms behind quote-curve selection beyond the already qualified within-model paired sensitivity.

**Required separately reviewed action:** resolve whether this screen is an intentionally retained, explicitly versioned quote-qualification constraint or a legacy constraint to remove from the final path. Reconcile source, policy/capability documentation and proposal accordingly, and assess any impact on frozen benchmark results through an explicitly approved correction plan. Do not silently relabel old limits or rewrite frozen results. No action was taken here.

### F2 — MINOR: historical documentation-freeze test rejects approved later audit documents

**Evidence:** `tests/test_proposal_reconciliation.py::test_documentation_only_change_and_all_frozen_files_exact` compares the current tree to the Iteration 26 base and permits only `docs/proposal_reconciliation_iteration27.md` and its own test file. The clean audited HEAD legitimately also contains the accepted 27A application/correction and TOC audit documents. The isolated clean-tree reproduction lists exactly those three accepted later documents as unexpected.

**Impact:** full Python regression is not green even though all 997 other tests pass and production source/frozen artifacts are unchanged. Adding this audit will also fall outside that historical allowlist. This is an obsolete temporal scope assumption, not an optimizer failure.

**Required separately reviewed action:** scope the historical Iteration 27 freeze assertion to its accepted commit or explicitly support later approved documentation-only additions without weakening production/data/result byte checks. Then rerun the complete suite. No test was modified.

### F3 — OBSERVATION: inherited compact proposal layout

The native TOC preserves background subheadings and the accepted 8.3-to-8.5 numbering sequence. Capability/causality/appendix tables split across pages and wrap long identifiers tightly; profit-delta figure labels are small. All inspected content remains within page bounds, captions are present and the 61 page references are correct. No material clipping or blank page was found. Optional cosmetic review may be useful, but no change is required by this finding.

### F4 — OBSERVATION: illustrative external reward-price basis remains uncorroborated

The accepted 27A audit and proposal identify the external reward USD conversion basis as user-approved illustrative pricing, not independently captured historical market evidence. This audit did not acquire new observations or validate that price. It is not canonical optimizer economics or benchmark input. Preserve the qualification; do not use it as current market evidence.

### F5 — OBSERVATION: validation is local, not GitHub CI or live execution

Actual GitHub status/check/workflow reads found no runs/checks for the audited commit. Local Python/Hardhat/frontend tests and exact replay cannot prove public execution or operational liquidity. No deployment or CI-success claim is made. The dashboard was tested through existing API/parser/SSR checks, not a new manual browser walkthrough.

## 14. Readiness decision and minimum residual tasks

**NOT_READY_FOR_FINAL_FREEZE**

The frozen results reproduce exactly; no blocker invalidating the entire capstone was found. The decision is withheld for the **material F1 final-policy inconsistency**, with **F2** also preventing the required green full regression.

Minimum correction set for separate human review:
1. Approve a narrow resolution of F1, explicitly handling code/policy/proposal agreement and any frozen-evaluation implications.
2. Correct only F2's obsolete historical test scope while preserving all substantive freeze checks.
3. Rerun the affected tests, complete Python suite and exact replay after any approved correction; re-audit the affected proposal wording if changed.

No fresh evidence, deployment, whole-portfolio feature, benchmark redesign, dashboard redesign or Iteration 29 is needed to address these findings. Observations F3–F5 do not themselves require a correction.

## 15. Final change-control verification

Before committing, only `docs/final_end_to_end_audit_iteration28.md` is to be staged. Existing production code, tests, canonical data/evidence, runtime configuration, Solidity, API/frontend, evaluation inputs and Iteration 23/24 artifacts remain byte-for-byte unchanged from the audited HEAD. The Google Doc revision and PDF are unchanged. The audit commit contains only this report; it implements no correction.

**Iteration 28 is verification-only. Findings are recorded for separate review. Iteration 29 was not started.**
