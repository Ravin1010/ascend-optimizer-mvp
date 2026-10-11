# Iteration 28 narrow correction — review record

Status: **F1/F2 implemented locally; frozen-result reconciliation requires review.**

Starting HEAD: `0b91eaf6195c04047a642ca813a07c4c04864085`.
Historical implementation audited: `f2d71c7b6765a60c98c38ce415a8cc028eef8a7c`.
Date: 11 October 2026. This is an Iteration 28 correction, not Iteration 29.

The existing Iteration 28 audit remains untouched. Observations F3–F5 were not addressed. No proposal, dashboard, canonical data, policy, risk/exit configuration, evaluation scenario or frozen result file was modified.

## Implemented corrections

### F1

`amount_optimizer.evaluate_candidate` now applies `PROFILE_SLIPPAGE_LIMIT` only when `evaluation_policy_mode is None`. The existing explicit synthetic-mode guard remains unchanged. Final-policy candidates still require qualified quotes at the exact candidate amount/context, valid finite slippage fractions, technical admission and economics. Quote loss remains in expected net profit; fixed costs, policy filtering, grid, tie-breaking and selected-point revalidation are unchanged.

Compatibility amount candidates retain the historical profile ceiling. `optimizer.py`, the actual legacy linear solver, is unchanged. The temporary benchmark comparison confirms every row for all three comparison methods is identical.

Six new parameterized cases cover both LP venues across all three profiles: a qualified quote above the legacy ceiling passes final candidate qualification but fails compatibility qualification. The economics/evidence and fixed-cost values are identical between modes. A seventh test verifies positive final selection above the old ceiling, unchanged grid and successful exact selected-point policy/economic revalidation.

### F2

The historical proposal test compares the exact accepted commits:

- Iteration 26: `4bbe78dc621036e9f6b692af386f458c7b9311f3`;
- Iteration 27: `2c9071a1d58da0afb977fa011933c7ef205ea92d`.

It requires exactly the two authorized files at that historical boundary and compares every other tracked file byte-for-byte between those commits. Later approved work and untracked build output no longer masquerade as Iteration 27 changes. No blanket allowlist expansion or production-byte-check removal was used.

## Consequences measured before changing any result artifact

Command: `python tools/run_final_evaluation.py --output-dir /tmp/correction28_benchmark`.

The unchanged 49-scenario configuration was executed with corrected code into temporary output only. Each of its 196 rows was compared field-by-field to the accepted artifacts. Input/configuration/dependency fingerprints and the production baseline remain equal. This is **SYNTHETIC_EVALUATION_ONLY**, not new market evidence.

- **8 changed rows**, all POLICY_AWARE_AMOUNT_OPTIMIZER.
- **3 allocation changes**; the other five rows change rejection/candidate diagnostics only.
- **147 rows for the three comparison methods are exactly unchanged**.
- All 196 rows retain Ascend zero; all weights plus idle equal exactly one.

| Scenario | Change |
| --- | --- |
| CORE_CONSERVATIVE_10000_30 | Candidate/rejection diagnostics only |
| CORE_CONSERVATIVE_10000_90 | Candidate/rejection diagnostics only |
| CORE_CONSERVATIVE_10000_365 | Gimo 40%, Jaine 20%, Oku 10%, idle 30% → Gimo 40%, Oku 40%, idle 20%; common-rescore profit $1,205 → $1,285 |
| CORE_BALANCED_10000_30 | Candidate/rejection diagnostics only |
| CORE_BALANCED_10000_90 | Candidate/rejection diagnostics only |
| CORE_BALANCED_10000_365 | Gimo 40%, Jaine 40%, Oku 20% → Gimo 40%, Jaine 60%; common-rescore profit $1,822 → $1,842 |
| FIXED_10000 | Candidate/rejection diagnostics only |
| QUOTE_CURVE | Jaine 10%, idle 90% → Jaine 60%, idle 40%; common-rescore profit $13.30 → $56.80 |

Native and Ascend are zero in each of the three allocation-change rows. Economic/risk aggregates, selected evidence, binding constraints and post-selection diagnostics were compared along with allocations; no claim that only displayed numbers changed is made.

| Summary quantity | Frozen value | Corrected-code temporary value |
| --- | ---: | ---: |
| Scenarios / normalized rows | 49 / 196 | 49 / 196 |
| Amount-aware versus legacy allocation disagreements | 27 | 27 |
| Any-method disagreements | 39 | 39 |
| Mean common-rescore delta USD | 43.395279634804 | 46.323851063376 |
| Median common-rescore delta USD | 0 | 0 |
| Concentration diagnostic scenarios | 31 | 33 |
| LP absolute-stress diagnostic scenarios | 34 | 35 |
| Staking stress / deadline diagnostic scenarios | 13 / 4 | 13 / 4 |
| Admission-or-evidence diagnostic count | 12 | 4 |
| Gate diagnostic count | 49 | 49 |
| Fixed-cost allocation sensitivity count | 1 | 1 |
| Quote-curve allocation sensitivity count | 1 | 0 |
| MULTIPLE / OBJECTIVE_DIFFERENCE | 26 / 1 | 26 / 1 |

Method recommendation/idle totals are unchanged: Highest Yield 45/4, Equal Weight 45/4, Legacy 35/14, Policy-Aware Amount 36/13. The five summary keys that differ are candidate constraint counts, admission/evidence counts, disagreement details, mean profit delta and quote allocation-sensitivity count.

**Important interpretation consequence:** QUOTE_CURVE and QUOTE_CONSTANT_CONTROL both select Jaine 60% under corrected code. Quote cost/profit still differs, but the frozen paired claim of a changed selected allocation is no longer supported by that pair. It must not be retained as a current corrected-code finding or replaced with a fabricated sensitivity. The frozen historical figure/table/findings/proposal have not been edited.

Potential downstream reconciliation includes the representative quote row, common-rescore summary/profit plot, constraint diagnostics and quote-sensitivity table/figure/findings. This record does not approve their regeneration or a scenario redesign.

## Validation actually run

| Check | Result |
| --- | --- |
| Policy + proposal reconciliation tests | 147 passed |
| Application/result, amount optimizer, economics, policy, proposal tests | 320 passed |
| Existing frontend/API tests | 58 passed |
| Complete Python suite | 999 passed, 6 failed, 0 skipped; 60.81 s |
| Corrected benchmark in temporary output | 49 scenarios / 196 rows generated |
| Iteration 23 current-code `--check` | Fails at raw JSON: expected consequence of retaining historical results |
| Iteration 24 frozen package `--check` | Exact: 7 tables / 8 figures / 34 files |
| Deployment-history audit | Passed |
| Deployment preflight | Passed: five strategies, 16661, unresolved runtime, NOT_DEPLOYED |

Overlapping subset counts are not additive. Runtime dependencies declared in requirements.txt were installed in the refreshed environment; no repository dependency file changed.

The six full-suite failures were investigated, not suppressed:

1. `test_asset_normalization.py::test_frozen_data_results_application_and_frontend_unchanged` compares current source against the pre-Iteration-26 base and rejects this authorized F1 change. This separate historical test was not broadened under the F2-only instruction.
2. `test_final_evaluation.py::test_lp_quote_amount_and_pair_changes` asserts the old selected-allocation sensitivity that no longer holds.
3–5. Three `test_exact_artifact_replay` cases detect the retained historical JSON/CSV/summary versus corrected-code output.
6. `test_presentation_correction_substantive_invariance` compares corrected-code output to the historical presentation-only correction baseline, which necessarily has different allocations/diagnostics now.

The F2 test itself passes. No assertion was weakened to conceal result consequences. Hardhat/build were not repeated because Solidity/frontend source did not change. Production profile/contract regressions remain fail-closed with 100% idle. Canonical evidence/runtime and all data/results/frontend/contracts are unchanged.

## Review boundary

F1 and F2 are implemented and directly tested, but the repository is **not yet ready for final freeze**: current-code replay cannot match historical results after the accepted semantic correction. A separate explicit decision is required on versioned result/interpretation reconciliation and the additional historical freeze assertions. Neither frozen artifacts nor proposal may be silently updated just to make tests green.

No commit/push is claimed in this review record. Iteration 29 was not started.
