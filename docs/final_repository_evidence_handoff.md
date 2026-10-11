# Final Repository & Evidence Handoff

**APPROVED / FINAL FROZEN — documentation handoff, 11 October 2026.** This is a navigation map, not a new technical iteration or a deployment claim. Iteration 29 was not started.

## 1. Final identity and authority

Repository: [Ravin1010/ascend-optimizer-mvp](https://github.com/Ravin1010/ascend-optimizer-mvp). The final frozen implementation, evidence and results are at **`4a280b90c6c39555b99658ee7855c6bd1f3bbba2`**. Verification began on `main` at that exact SHA with a clean working tree; connected GitHub `main` matched. Immediate parent: `ede77d4d0165d0fb076463ee964c8bbe3e6cdf90`.

The handoff commit adds only this document; it does not replace the frozen technical SHA. The accepted final lineage is audit `0b91eaf…` → technical/result reconciliation `ede77d4…` → Section 8.0 wording correction `4a280b9…`. Earlier iteration documents are historical evidence, not a competing current result baseline. In particular, pre-correction +$43.40 and quote-allocation-effect claims are superseded by the corrected outputs below and remain recoverable in Git history.

## 2. Implementation map

Paths are repository-relative. Status describes source purpose, **not execution readiness**. `IMPLEMENTED_CURRENT` means accepted source behavior; `REFERENCE_ONLY` means an architectural/reference artifact; `HISTORICAL/COMPATIBILITY` identifies the retained earlier method/transport. Generated reports and audits use `GENERATED_RESULT` and `AUDIT_ONLY`.

| Authoritative path/group | Purpose | Status |
| --- | --- | --- |
| `src/ascend_optimizer/amount_optimizer.py` | Exact-amount grid search, admission/economics qualification and selected-point revalidation | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/evaluation_policy.py` | Explicit synthetic final-policy feasibility, deadline and identity revalidation | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/profiles.py` | Existing profile values and retained legacy thresholds; final namespace comes from evaluation policy | HISTORICAL/COMPATIBILITY |
| `src/ascend_optimizer/economics_evidence.py`, `net_return_engine.py` in the same directory | Qualified return/quote/lifecycle evidence; fee basis and return calculations | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/admission_records.py`, `admission_provider.py`, `admission_validity.py` | Typed captures, amount/configuration matching, source and freshness qualification | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/runtime_config.py` | Actual-route configuration identity and unresolved/verified distinction | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/lp_range_stress.py`, `risk_stress.py`, `exit_liquidity.py` | V3 inventory stress, independent deterministic budgets, native-0G exit timing | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/data_loader.py`, `strategy_state.py`, `asset_normalization.py` | Canonical universe/category/gate interpretation and chain-bound wrapping semantics | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/application_contract.py` | Schema 1.4 adapter; primary current-request policy-aware recommendation | IMPLEMENTED_CURRENT |
| `frontend/src/app/api/decision-sleeve/route.ts` | Primary `/api/decision-sleeve` request endpoint | IMPLEMENTED_CURRENT |
| `frontend/src/app/page.tsx`, `decision-view.tsx`, `globals.css` | Current-request inputs, five strategy diagnostics, idle and separated status panels | IMPLEMENTED_CURRENT |
| `frontend/src/lib/final-types.ts`, `final-response.ts` | Typed final schema/parser; consumes canonical metadata through backend StrategyState | IMPLEMENTED_CURRENT |
| `src/ascend_optimizer/optimizer.py`, `pipeline.py`, `exposure_engine.py`, `lp_execution.py` | Legacy/reference linear path and compatibility LP execution/proxy semantics | HISTORICAL/COMPATIBILITY |
| `src/ascend_optimizer/result_contract.py`; `frontend/src/app/api/optimize/route.ts`; `frontend/src/lib/types.ts`, `optimizer-response.ts` | Schema 1.3 transport/endpoint/parser | HISTORICAL/COMPATIBILITY |

The dashboard shows the current request, not historical benchmark statistics. It does not import the report figures/findings. Recommendation, feasibility, protocol availability, integration, runtime configuration, execution readiness and public proof are separate dimensions.

### Accepted contract source stack

All paths below are source/local-test architecture; none establishes a public registered route.

| Path | Purpose | Status |
| --- | --- | --- |
| `contracts/AscendVault.sol` | Idle custody, registered adapter routing and protected withdrawal boundaries | IMPLEMENTED_CURRENT |
| `contracts/StrategyManager.sol` | Strategy registry/allocation controls | IMPLEMENTED_CURRENT |
| `contracts/RewardAccounting.sol` | Checkpointed, separately claimable reward accounting | IMPLEMENTED_CURRENT |
| `contracts/adapters/Native0GStakingAdapter.sol` | Native validator staking boundary | IMPLEMENTED_CURRENT |
| `contracts/adapters/GimoAdapter.sol` | st0G staking/request/claim boundary | IMPLEMENTED_CURRENT |
| `contracts/adapters/JaineLPAdapter.sol` | Jaine V1 LP path | IMPLEMENTED_CURRENT |
| `contracts/adapters/OkuV3Adapter.sol` | Oku Router02 LP path | IMPLEMENTED_CURRENT |
| `contracts/adapters/AscendProtocolAdapter.sol` | SourceCore/a0G source-level deposit and queued withdrawal interface | IMPLEMENTED_CURRENT |
| `contracts/adapters/V3LiquidityAdapter.sol`; `contracts/libraries/V3PositionMath.sol`; `contracts/interfaces/` | Shared LP machinery and protocol interfaces | IMPLEMENTED_CURRENT |
| `contracts/A0GToken.sol`, `contracts/adapters/AscendStakingAdapter.sol` | Reference/pre-launch local token/staking model, not external Ascend proof | REFERENCE_ONLY |
| `contracts/adapters/RestakingAdapter.sol`, `contracts/interfaces/IRestakingConnector.sol` | Generic connector boundary; no sixth current strategy | REFERENCE_ONLY |
| `contracts/mocks/` | Local test fixtures, not deployment/evidence | REFERENCE_ONLY |

## 3. Canonical scope, assets and chains

Current input is **native 0G only**. Scope is `DECISION_SLEEVE`: only explicitly designated decision capital is optimized. Existing holdings, LP NFTs, staking balances and pending exits are `EXOGENOUS_NOT_OPTIMIZED`; whole-portfolio compliance is `NOT_ASSESSED`.

Native 0G and W0G form one 0G economic asset family with distinct execution representations. Native 0G is input, idle and common cash output. W0G is internal wrapping for LP/Ascend ERC-20 paths, not a strategy or independent yield source; direct W0G input is future. st0G/a0G are receipt/share assets; USDC.e is an LP execution/position asset. ETH/BTC inputs remain future. This wrapping relationship is not an independent price-oracle assertion.

0G Mainnet **16661** is the intended execution domain. Mainnet W0G is the chain-bound external reference `0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c`, not capstone deployment proof. Galileo **16602** is conditional development/test only; Galileo W0G remains unresolved/not verified, with no other-chain address substitution. Ethereum is a backing/security dependency, not independent user-capital routing. Base is deferred.

| Independent strategy ID | Canonical category | Allocation gate |
| --- | --- | --- |
| NATIVE_STAKE_0G | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| GIMO_STAKE_0G | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| JAINE_LP_0G_USDC | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| OKU_LP_0G_USDC | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| ASCEND_STAKE_A0G | INTEGRATED_GATED | CLOSED |

All five are structural candidates with integration `IMPLEMENTED`; allocatable category does not mean live readiness. Ascend embedded Mellow/Symbiotic is `EMBEDDED_NON_ALLOCATABLE`, Morpho/iAI `OBSERVED_EXCLUDED`, standalone Symbiotic `KIV_FUTURE`, and W0G/Bond/Zia/reference assets `AUXILIARY_NOT_STRATEGY`.

## 4. Final mechanism and policy

Primary method: **`POLICY_AWARE_AMOUNT_OPTIMIZER`**. The deterministic **0.1 weight grid** evaluates exact candidate amounts, permits idle, charges fixed lifecycle cost once per positive allocation and applies amount-dependent variable/LP quote costs. Technical admission and economics precede final policy feasibility. Feasible candidates rank by expected net profit; selected economics/policy/configuration identities are revalidated, with changed or missing required evidence failing closed. TVL is not automatically executable capacity.

| Final constraint | Conservative | Balanced | Aggressive |
| --- | ---: | ---: | ---: |
| Maximum strategy concentration | 40% | 60% | 80% |
| Maximum weighted staking stress | 2% | 5% | 10% |
| Maximum LP absolute stress | 5% | 10% | 20% |
| Cash deadline | Optional | Optional | Optional |

These are `SYNTHETIC_EVALUATION_ONLY` policy choices, not calibrated production probabilities/VaR. Native/Gimo use the 5% modelled staking severity without duplicate Gimo slashing or assumed correlation. LP policy uses worst absolute position loss over -20/-10/+10/+20% economic-price shocks; IL/HODL attribution is not added again. Independent stress budgets do not imply a joint event. Ascend hypothetical analysis never opens CLOSED.

Old fixed profile slippage ceilings are **legacy/reference only, not final-policy constraints**; exact quote loss/evidence still affects economics. Old IL/bridge/fixed exit limits are likewise compatibility namespaces. Holding horizon, exit decision, modelled time-to-native-0G and optional cash deadline remain distinct. Deadline states are NOT_REQUESTED, COMPATIBLE_MODELLED, INCOMPATIBLE_MODELLED or UNRESOLVED; required unresolved positive timing fails closed. Synchronous LP unwind is not an execution guarantee.

## 5. Metadata, configuration and evidence map

| Canonical artifact | Role / current state |
| --- | --- |
| `data/strategies.csv`, `data/tracked_records.csv` | Strategy taxonomy, gates, capital paths and separate ecosystem records |
| `data/source_registry.csv`, `data/metadata_contract.md` | Source/provenance roles and metadata contract |
| `data/runtime_strategy_config.json`, `data/runtime_configuration_contract.md` | Five actual-route records, all UNRESOLVED |
| `data/admission_evidence.csv`, `data/admission_evidence_contract.md`, `data/admission_validity_policy.md` | Headers-only capture ledger and qualification policy |
| `data/strategy_return_evidence.json`, `data/lp_quote_evidence.json`, `data/lifecycle_cost_evidence.json`, `data/economics_evidence_contract.md` | Empty canonical economics records; separate return, quote and cost contracts |
| `data/strategy_snapshots.csv`, `data/demo_strategy_snapshots.csv` | Legacy/reference snapshots versus explicitly modelled demo fixtures; not substitutes for current qualification |
| `data/evaluation_policy.json`, `data/lp_evaluation_config.json`, `data/risk_scenarios.json`, `data/exit_evaluation_config.json` | Versioned synthetic policy, independent LP ranges, deterministic stress and exit assumptions |
| `data/application_evaluation_config.json`, `data/final_evaluation_config.json`, `data/final_evaluation_contract.md` | Explicit current-request fixtures and four-method experiment inputs/semantics |
| `data/deployment_recovery_audit.json`, `data/intended_deployment_architecture.json` | Historical deployment search and intended architecture, not deployment registration |

Observed, derived, historical, modelled, static and missing evidence remain distinguishable. Observation time and retrieval time are separate. VALID/STALE/CONFIG_MISMATCH/AMOUNT_MISMATCH/SOURCE_UNVERIFIED/MISSING/POLICY_UNDEFINED are typed qualifications; admission TTL is not a universal economics/quote TTL. Missing data does not become zero or unlimited capacity. Gimo embedded fees and Ascend embedded return are counted once; non-financial points are excluded from financial APY.

Production uses canonical evidence and intentionally returns **100% idle for all three profiles** because bindings/admission/economics are unresolved or empty. Synthetic mode must be explicitly requested and may use modelled valuations, returns, costs, quotes, risk and timing. It is not live APY, market calibration, executable quotes or production recommendation proof. Execution readiness/public proof remain NOT_ESTABLISHED. No recoverable public capstone deployment is established; public deployment is neither required nor planned as a milestone, and no live-capital proof is claimed.

## 6. Evaluation and report package

`src/ascend_optimizer/final_evaluation.py`, `final_evaluation_inputs.py`, `evaluation_baselines.py` and `final_results.py` in that directory, plus the two runner tools below, implement the reproducible evaluation/report pipeline (`IMPLEMENTED_CURRENT`).

Authoritative raw outputs (`GENERATED_RESULT`): `results/final_evaluation_iteration23.json`, `.csv` and `results/final_evaluation_iteration23_summary.json`. Current baseline is **ITERATION28_F1_CORRECTED_FINAL_POLICY**, retaining historical lineage despite iteration-labelled filenames.

FINAL_EVALUATION_V1 contains **49 scenarios / 196 rows**: 27 core scenarios/108 rows and 22 targeted scenarios. Exactly four methods are compared: HIGHEST_YIELD_BASELINE, EQUAL_WEIGHT_ELIGIBLE_BASELINE, LEGACY_LINEAR_OPTIMIZER and POLICY_AWARE_AMOUNT_OPTIMIZER. Capabilities differ; unsupported is not zero/passed.

Results: amount-aware–legacy disagreement **27/49**; any-method disagreement **39/49**. Common post-selection exact-allocation rescoring yields **19 positive / 7 negative / 23 zero** deltas, mean **+$46.32**, median **$0**. Disagreement is not improvement, rescore is not each internal objective, and these matrix counts are not empirical probabilities. Fixed-cost controlled allocation sensitivity is **1**; quote allocation sensitivity is **0**. QUOTE_CURVE and QUOTE_CONSTANT_CONTROL both select **Jaine 60% / idle 40%**, with different assessed quote loss/profit: economic sensitivity only. Other contributor labels are diagnostic associations. Ascend is zero in every row.

The current generated package has **7 tables, 8 figures, 34 files**. The following are all current `GENERATED_RESULT` assets; “not inserted” does not mean obsolete.

| Table path | Purpose | Proposal placement |
| --- | --- | --- |
| `results/final_tables/01_capabilities.md` | Four-method capabilities | Main Table 6.5 |
| `results/final_tables/02_matrix.md` | Matrix dimensions | Appendix Table A.2 |
| `results/final_tables/03_outcomes.md` | Recommendation/idle counts | Intentionally not inserted |
| `results/final_tables/04_representative_scenarios.md` | Traceable representative method rows | Appendix Table A.1 |
| `results/final_tables/05_disagreements.md` | Disagreement/common rescore | Main Table 6.6 |
| `results/final_tables/06_constraint_diagnostics.md` | Nonexclusive candidate/binding diagnostics | Intentionally not inserted |
| `results/final_tables/07_causality.md` | Controlled sensitivity versus association | Main Table 6.7 |

Each table has a same-stem `.csv` companion in `results/final_tables/`.

| Figure path | Purpose | Proposal placement |
| --- | --- | --- |
| `results/final_figures/01_outcomes.png` | Outcome counts, not success frequency | Intentionally not inserted |
| `results/final_figures/02_allocations.png` | Representative current-model allocations | Figure 6.2 |
| `results/final_figures/03_fixed_cost.png` | Fixed-cost controlled pair | Figure 6.3 |
| `results/final_figures/04_quote_curve.png` | Same allocation, different quote economics | Figure 6.4 |
| `results/final_figures/05_profiles.png` | Combined profile/grid LP progression | Figure 6.5 |
| `results/final_figures/06_deadlines.png` | Modelled cash-deadline feasibility | Figure 6.6 |
| `results/final_figures/07_profit_deltas.png` | Common post-selection rescore deltas | Figure 6.7 |
| `results/final_figures/08_constraints.png` | Constraint diagnostic counts | Intentionally not inserted |

Each figure has a `_data.csv` companion; captions are in `results/final_figures/captions.md`. Together these are 14 table files + 16 figure/data files + captions + `results/final_evaluation_findings.json` + `docs/final_evaluation_findings_iteration24.md` + `results/final_results_iteration24_manifest.json` = **34**. The manifest pins sources, renderer and hashes for the other 33 outputs; it does not hash itself. Findings and manifest are current, not pre-F1 results.

## 7. Reproduction and accepted validation

Run from repository root after installing existing dependencies: `python -m pip install -r requirements-results.txt`; `npm install` for contracts, and separately in `frontend/`. Use the existing Python/Node environment; renderer version is pinned, while other declared dependencies are not all pinned. No RPC is needed for deterministic replay.

```bash
python -m pytest -q
npm run contracts:test
python tools/run_final_evaluation.py --check
python tools/generate_final_results.py --check
python -m pytest -q tests/test_application_contract.py::test_production_fail_closed_all_profiles
python tools/audit_deployment_history.py --check
python tools/deployment_preflight.py
```

From `frontend/`:

```bash
node --test tests/*.test.ts
npm run typecheck
npm run build
```

Accepted Iteration 28 validation: Python **1,005 passed**, Hardhat **72 passed**, frontend/API/parser/SSR **58 passed**, typecheck/build passed. Application/result-contract Python subset **74 passed** overlaps the full suite. One existing pandas warning remains; local checks are not GitHub CI. Build-generated files are not approved source amendments; keep reproduction in a separate checkout if running builds.

This handoff reran only read-only verification: evaluation **49/196 exact**, result package **7/8/34 exact**, production-profile test **3 passed**, deployment audit and preflight passed. The fresh environment initially lacked requests; existing declared dependencies were installed without changing repository files. Full suites were not rerun here; their accepted counts come from the correction audit. No result was regenerated or modified.

## 8. Final proposal and provenance

Existing [Proposal Initial Draft](https://docs.google.com/document/d/1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4), document ID `1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4`.

Final revision: `AHj4eMS1IUyMt5eReN9DfndPNWT17NNkEB6dvBHaOdfaSqOj16C449FS0w8neYhnnQa-fw28hElcZCm013o9ySmdBMOnYrmTPv3Zl9E89Eg`.

Final PDF: **53 pages**, SHA-256 **`770bd0b658f8a30b3aad1446136aaf16e127556e0e55630657e10fde1a51285d`**. Live revision and retained export hash were reconfirmed read-only for handoff. Section 1.0 stayed protected; native TOC is present, Appendix A contains synthetic tables, Section 6 has corrected results and Section 8.0 the final contribution wording. No proposal edit/export regeneration occurred here.

All following records are `AUDIT_ONLY` except the staged reconciliation draft, which is historical proposal preparation. They preserve chronology, including superseded claims; read the latest corrections for current conclusions.

| Repository path | Purpose / associated SHA |
| --- | --- |
| `docs/proposal_reconciliation_iteration27.md` | Staged amendment map; `2c9071a1d58da0afb977fa011933c7ef205ea92d` |
| `docs/proposal_application_iteration27a.md` | Approved in-place proposal application; `2758a109d5450a0c6a71b565b8f94c89ae9306e6` |
| `docs/proposal_application_iteration27a_correction.md` | Artwork/future-work correction; `9fc56a883b8030540a7790fa24b48c1dbc7a7e97` |
| `docs/proposal_toc_finalization.md` | Native TOC/protected heading preparation; `f2d71c7b6765a60c98c38ce415a8cc028eef8a7c` |
| `docs/final_end_to_end_audit_iteration28.md` | Historical verification discovering F1/F2; `0b91eaf6195c04047a642ca813a07c4c04864085` |
| `docs/iteration28_correction_review.md` | Pre-promotion result-impact stop/review record; retained with technical correction |
| `docs/final_end_to_end_audit_iteration28_correction.md` | Resolved F1/F2, corrected results/proposal and READY_FOR_FINAL_FREEZE; `ede77d4d0165d0fb076463ee964c8bbe3e6cdf90` |
| `docs/final_end_to_end_audit_iteration28_correction2.md` | Single Section 8.0 sentence/PDF preservation; `4a280b90c6c39555b99658ee7855c6bd1f3bbba2` |

## 9. Residual observations and future scope

Only F3–F5 remain non-blocking: **F3** inherited compact table wrapping/small plot labels (cosmetic, preserved); **F4** user-approved illustrative external reward-price conversion remains uncorroborated, not canonical optimizer/benchmark economics; **F5** validation is local, with no GitHub CI/live-execution inference or new manual dashboard walkthrough. None reopens technical design.

**NOT REQUIRED FOR CURRENT CAPSTONE COMPLETION:** qualified observational economics/freshness evidence; direct W0G input; ETH/BTC/broader multi-asset normalization; whole-portfolio optimization; standalone Symbiotic allocation; future public/live execution/deployment. These are future/KIV, not missing mandatory work. No discrepancy was found in handoff checks; no existing implementation, evidence, result or proposal was changed.

## Submission / Viva Quick Reference

| Item | Frozen answer |
| --- | --- |
| Final repository SHA | `4a280b90c6c39555b99658ee7855c6bd1f3bbba2` |
| Final proposal PDF hash | `770bd0b658f8a30b3aad1446136aaf16e127556e0e55630657e10fde1a51285d` |
| Current optimizer | POLICY_AWARE_AMOUNT_OPTIMIZER |
| Scope | DECISION_SLEEVE |
| Current input | Native 0G |
| Independent strategies | 5 |
| Production behavior | 100% idle / fail closed |
| Evaluation | 49 scenarios / 196 rows |
| Key result | 27/49 amount-aware–legacy disagreement |
| Mean common-rescore delta | +$46.32; matrix diagnostic, not universal superiority |
| Deployment | NOT REQUIRED / NOT DEPLOYED |
| Whole portfolio | NOT_ASSESSED |

Final repository/evidence handoff only. Iteration 29 was not started.
