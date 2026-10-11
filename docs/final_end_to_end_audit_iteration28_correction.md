# Iteration 28 correction and result/claim reconciliation

**Decision: READY_FOR_FINAL_FREEZE**

Date: 11 October 2026. Parent committed SHA: `0b91eaf6195c04047a642ca813a07c4c04864085`. Branch: `main`. The original `docs/final_end_to_end_audit_iteration28.md` remains byte-identical as the historical audit that found F1/F2. This correction continues the explicitly approved work; Iteration 29 was not started.

## 1. Change control and semantic resolution

The starting working tree contained exactly the accepted F1 source edit, seven F1 tests, the F2 historical-boundary test correction and the uncommitted review record. Their complete diff and review record were inspected; none was discarded/reset. `docs/iteration28_correction_review.md` is retained as the pre-promotion stop/review record, not a claim that reconciliation remains pending.

**F1 — resolved:** final candidates with `evaluation_policy_mode == SYNTHETIC_EVALUATION_ONLY` no longer use the fixed profile slippage ceiling or PROFILE_SLIPPAGE_LIMIT as final-policy feasibility. Compatibility candidates with `evaluation_policy_mode is None` retain that exact check. The existing mode guard rejects other modes. Finite quote values, exact amount/context/evidence identity, technical admission, quote-loss economics, risk/deadline filtering, candidate grid, expected-profit objective and selected-point revalidation remain operative. Actual legacy optimizer code is unchanged.

Six cases cover both LP venues and all three profiles above their historical slippage ceilings: final qualification passes, compatibility qualification rejects and quote economics/fixed costs are identical. A seventh verifies positive final selection above the old ceiling and successful exact economic/policy revalidation.

**F2 — resolved:** the exhaustive documentation-freeze check compares `4bbe78dc621036e9f6b692af386f458c7b9311f3` → `2c9071a1d58da0afb977fa011933c7ef205ea92d`, requiring exactly the two authorized historical files and identical bytes for every other tracked file. It does not use a generic/open-ended allowlist.

## 2. Independent impact reproduction before promotion

The unchanged scenario package was rerun into an external temporary directory before authoritative generation, and independently repeated after the environment refresh. All 196 rows were compared field-by-field with the historical accepted result at the parent commit. The promoted JSON/CSV/summary are byte-identical to the independently rerun temporary outputs. Input/config/dependency fingerprints and production baseline are equal to historical inputs.

- 49 scenarios / 196 rows: unchanged.
- Core: 27 scenarios / 108 rows; targeted: 22 scenarios: unchanged.
- 8 changed rows, all POLICY_AWARE_AMOUNT_OPTIMIZER.
- 3 allocation changes; 5 diagnostics/rejections-only changes.
- All 147 rows belonging to the other three methods are exactly identical.
- All rows have exactly five strategy weights plus explicit idle summing exactly to one. Ascend is zero throughout.

| Scenario | Historical allocation/profit | Corrected allocation/profit |
| --- | --- | --- |
| CORE_CONSERVATIVE_10000_365 | Gimo 40%, Jaine 20%, Oku 10%, idle 30%; $1,205 | Gimo 40%, Oku 40%, idle 20%; $1,285 |
| CORE_BALANCED_10000_365 | Gimo 40%, Jaine 40%, Oku 20%; $1,822 | Gimo 40%, Jaine 60%; $1,842 |
| QUOTE_CURVE | Jaine 10%, idle 90%; $13.30 | Jaine 60%, idle 40%; $56.80 |

Native and Ascend are zero in these three rows. Profits are common exact-allocation post-selection rescoring, not an assertion of identical internal method objectives. No scenarios, quote curves, costs, rates, ranges, durations, thresholds or comparison algorithms were changed to recover old results.

Diagnostics-only changes: CORE_CONSERVATIVE_10000_30, CORE_CONSERVATIVE_10000_90, CORE_BALANCED_10000_30, CORE_BALANCED_10000_90 and FIXED_10000. The affected fields of every changed row are recorded below.

| Scenario | Changed fields |
| --- | --- |
| CORE_CONSERVATIVE_10000_30 | `diagnostics`, `rejection_reasons` |
| CORE_CONSERVATIVE_10000_90 | `diagnostics`, `rejection_reasons` |
| CORE_CONSERVATIVE_10000_365 | `allocation_weights`, `common_economic_points`, `diagnostics`, `expected_gross_return`, `expected_net_profit`, `expected_net_return`, `fixed_cost`, `idle_weight`, `lifecycle_cost`, `lp_absolute_stress`, `lp_quote_execution_loss`, `method_lifecycle_cost`, `method_lp_quote_loss`, `method_reported_profit`, `net_apy`, `posthoc_policy_constraints`, `rejection_reasons`, `total_stress_budget` |
| CORE_BALANCED_10000_30 | `diagnostics`, `rejection_reasons` |
| CORE_BALANCED_10000_90 | `diagnostics`, `rejection_reasons` |
| CORE_BALANCED_10000_365 | `allocation_weights`, `binding_constraints`, `common_economic_points`, `diagnostics`, `expected_gross_return`, `expected_net_profit`, `expected_net_return`, `fixed_cost`, `lifecycle_cost`, `lp_absolute_stress`, `lp_quote_execution_loss`, `method_lifecycle_cost`, `method_lp_quote_loss`, `method_reported_profit`, `net_apy`, `posthoc_policy_constraints`, `rejection_reasons`, `total_stress_budget` |
| FIXED_10000 | `diagnostics`, `rejection_reasons` |
| QUOTE_CURVE | `allocation_weights`, `binding_constraints`, `common_economic_points`, `diagnostics`, `expected_gross_return`, `expected_net_profit`, `expected_net_return`, `idle_weight`, `lp_absolute_stress`, `lp_quote_execution_loss`, `method_lp_quote_loss`, `method_reported_profit`, `net_apy`, `posthoc_policy_constraints`, `rejection_reasons`, `total_stress_budget` |

## 3. Corrected headlines and interpretation

| Quantity | Historical | Corrected |
| --- | ---: | ---: |
| Amount-aware vs legacy allocation disagreements | 27 / 49 | 27 / 49 |
| Any-method disagreements | 39 / 49 | 39 / 49 |
| Positive / negative / zero common-rescore deltas | 19 / 7 / 23 | 19 / 7 / 23 |
| Mean common-rescore delta USD | 43.395279634804 | 46.323851063376 |
| Report-facing mean | +$43.40 | +$46.32 |
| Median delta | $0 | $0 |
| Fixed-cost selected-allocation sensitivity | 1 | 1 |
| Quote selected-allocation sensitivity | 1 | 0 |
| LP absolute-stress diagnostic scenarios | 34 | 35 |
| Concentration diagnostic scenarios | 31 | 33 |
| Staking / deadline diagnostic scenarios | 13 / 4 | 13 / 4 |
| Admission-or-evidence diagnostics | 12 | 4 |
| Gate diagnostics | 49 | 49 |
| MULTIPLE / OBJECTIVE_DIFFERENCE | 26 / 1 | 26 / 1 |

Recommendation/idle totals remain Highest Yield 45/4, Equal Weight 45/4, Legacy Linear 35/14 and Policy-Aware Amount 36/13 (49 rows each). Other summary changes are the individual disagreement details; aggregate drivers do not change. Constraint diagnostics are nonexclusive scenario associations, not probabilities or isolated causal effects. Attribution/count logic was not modified.

The fixed-cost controlled pair retains its allocation effect. QUOTE_CURVE and QUOTE_CONSTANT_CONTROL now both select Jaine 60%, idle 40%. The curve case assesses $58.20 quote loss and $56.80 common profit; the constant control assesses $0.60 quote loss and $114.40 profit. This is controlled quote/economic sensitivity under identical selected weights, **not allocation-selection sensitivity**. No replacement scenario is added. Disagreement is not improvement; some profit deltas remain negative, median is zero and selection-objective comparability remains LIMITED.

## 4. Deterministic result promotion and affected derivatives

The normal evaluator generated the three authoritative Iteration 23 JSON/CSV/summary files. The existing final-results generator was updated only for corrected source hash pins/count guards, provenance and directly affected quote interpretation. It still fails on source tampering and uses the same figures/design, renderer, matrix and method capabilities. The baseline is explicitly `ITERATION28_F1_CORRECTED_FINAL_POLICY`, with parent SHA and historical result head `7abfa1a347f35985052bee617e1bd82165f471f0` in findings/manifest. Historical commits and audits are not rewritten.

The normal generator produces 7 tables / 8 figures / 34 files. A byte-by-byte comparison found **18 changed derivatives / 16 byte-identical derivatives**. Only figures 04_quote_curve, 07_profit_deltas and 08_constraints changed. Figures 01_outcomes, 02_allocations, 03_fixed_cost, 05_profiles and 06_deadlines (and their data) remain byte-identical. Tables 01_capabilities, 02_matrix and 03_outcomes remain byte-identical. No formatting-only changes were made to unaffected assets.

Changed derivatives:

- `results/final_tables/04_representative_scenarios.csv`
- `results/final_tables/04_representative_scenarios.md`
- `results/final_tables/05_disagreements.csv`
- `results/final_tables/05_disagreements.md`
- `results/final_tables/06_constraint_diagnostics.csv`
- `results/final_tables/06_constraint_diagnostics.md`
- `results/final_tables/07_causality.csv`
- `results/final_tables/07_causality.md`
- `results/final_figures/04_quote_curve.png`
- `results/final_figures/04_quote_curve_data.csv`
- `results/final_figures/07_profit_deltas.png`
- `results/final_figures/07_profit_deltas_data.csv`
- `results/final_figures/08_constraints.png`
- `results/final_figures/08_constraints_data.csv`
- `results/final_figures/captions.md`
- `results/final_evaluation_findings.json`
- `docs/final_evaluation_findings_iteration24.md`
- `results/final_results_iteration24_manifest.json`

Current-facing evaluation contract, harness summary and generated findings identify the correction and corrected quote interpretation. Historical proposal staging/audit documents retain their original claims as historical provenance. Their old statistics are not the authoritative current result.

## 5. Strict regression reconciliation

Historical assertions are scoped to their accepted historical boundaries, not relaxed:

- Iteration 26 asset normalization: Iteration 25 correction `8749d0ae1150b297dbae996ba0ce9155e13908d6` → accepted Iteration 26 `4bbe78dc621036e9f6b692af386f458c7b9311f3`; same protected paths.
- Iteration 27: the exact Iteration 26 → 27 boundary described under F2.
- Presentation-only correction: actual artifact contents at `8e214fa0d5437da22696267dcb1bc929ef1dd4a9` → `7abfa1a347f35985052bee617e1bd82165f471f0`; substantive invariance is still required for that historical correction.
- Application migration's three historical result guards: accepted Iteration 24 → accepted Iteration 25 correction. Canonical evidence/config/input guards still check current bytes against accepted history.
- Current result hashes, all three exact evaluator replay assertions, every derivative's manifest hash and exact generated PNG/CSV/Markdown/JSON bytes remain strict.
- Quote-pair test now requires identical selected weights, higher curve quote loss/lower profit, exact amount evidence and no final PROFILE_SLIPPAGE_LIMIT rejection. It does not fabricate allocation sensitivity.

No skip, xfail, suppression or open-ended allowlist was introduced.

## 6. Validation actually run

| Check | Result |
| --- | --- |
| Full Python suite (final clean source state) | 1,005 passed; 0 failed; 0 skipped; 63.31 s |
| Application/API and result contract subset | 74 passed (overlaps full suite) |
| Full Hardhat suite | 72 passed; 0 failed; 0 skipped; about 5 s |
| Existing frontend/API/parser/SSR tests | 58 passed; 0 failed; 0 skipped; 8.14 s |
| TypeScript typecheck | Passed |
| Frontend production build | Passed; existing four routes generated |
| Iteration 23 evaluator --check | Exact 49 scenarios / 196 rows; all three artifacts |
| Iteration 24 generator --check | Exact 7 tables / 8 figures / 34 files |
| Deployment-history audit --check | Passed |
| Deployment preflight | Passed: five strategies, intended 16661, unresolved runtime, NOT_DEPLOYED |
| Canonical production Conservative / Balanced / Aggressive | 100% idle for all three |
| git diff --check | Passed |

Subset counts are not additive. The complete Python suite retains one existing pandas collector FutureWarning. An intermediate run found three historical application-result guards and a concurrent frontend build side effect; their exact historical scope was corrected and generated frontend files restored. The final full suite is green. Refreshed runtime dependencies were installed from existing requirements; no dependency/config file was changed. Tests are local validation, not GitHub CI or public execution proof.

Production rejection diagnostics include NO_MATCHING_CAPTURE / TECHNICAL_ADMISSION_UNKNOWN. Runtime records remain UNRESOLVED, canonical admission remains headers-only and canonical economics remain empty; no hard-coded idle override or fresh evidence was added. Frontend build changes to next-env.d.ts/tsconfig.json were restored and untracked tsbuildinfo removed before final staging. No frontend/Solidity change is committed.

## 7. Google proposal reconciliation and PDF verification

Existing document: `Proposal Initial Draft`, ID `1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4`.

Revision before:
`AHj4eMSmWCq2SxRHOc6mFngaSY3McI0Il8k3b7S5Mt7mjVIK16TY9Idt4pfuD8WiEh28YtVuUPb05T-CTn91CbJYIsd1glJX8zRWWNXamHw`

Revision after scoped result edits, image verification and native TOC refresh:
`AHj4eMTuZTiqc2rS9d-KQDYuuHaeXhhCB9DZb7hSngAc98fQ4wVGX-t4yzhNCxVQy0S-ErWE5XB6pk3DoTLUuit2sKhJ8ecD4rgRD7lIauA`

Revision-aware writes were used for connector edits. Nine native text paragraphs/cells changed: Section 6.5 mean/quote interpretation, Table 6.6 mean, Table 6.7 quote interpretation, Figure 6.4 caption and five QUOTE_CURVE policy-aware Appendix cells (allocation, idle, common profit, LP stress and constraint diagnostic). Exactly two result images were replaced in place: Figure 6.4 quote curve and Figure 6.7 profit deltas, using corrected generated PNGs and original size/placement. An initial connector ordering mismatch reversed these two images; PDF inspection caught it and a scoped replacement corrected it before final export.

Native readback compared all 1,281 original body/table paragraphs in order against the explicit nine-change map: all other text and named paragraph styles remained unchanged before TOC refresh. The 18 native tables and 21 inline-image count remain. Unaffected image IDs, source references and geometry are retained; authenticated contentUri URLs may refresh between reads. No Section 6.6 prose correction was required. Sections 1–5 and 7–8 were not edited, including Section 8.6. Rejected outcome/constraint figures or tables were not added to the proposal.

**Section 1.0 is exactly unchanged**, with heading-to-next-section SHA-256:
`18f83624a62184e2cc32316e89de8f3f70a8d1a4d9fbea28880a01c1a12478a0`.

The existing native TOC was refreshed through its browser Update table of contents control, not manually typed or replaced. Heading text/levels and the accepted 8.3 → 8.5 sequence remain. Final TOC spans pages 2–3; all **61/61 page references** match their headings in the exported PDF. Section 1.0 begins on page 4. No blank page was introduced.

Final PDF: **53 pages**, SHA-256:
`d5541df762234d4efe99b1f1afac1ccd3bfaf8393ac53f57b417be4935697aa8`.

Visual inspection covered TOC/Objectives (pages 2–4), Section 6.4/6.5/result tables and figures (35–42), limitations pagination and Appendix (46–53), plus the final corrected image pages 41–42 and refreshed TOC. Captions match their images; plots are readable at the inherited size; no material clipping, overlap or blank page was found. Five shifted TOC references were corrected by the native refresh. Compact wrapping and small full-matrix profit labels remain the accepted F3 observation; no unrelated cosmetic redesign was made.

## 8. Corrected consistency and residual observations

| Domain | Final state |
| --- | --- |
| Final-policy fixed slippage ceiling | NOT USED |
| Legacy/reference fixed slippage ceiling | PRESERVED |
| Exact quote economics/evidence/revalidation | PRESERVED |
| Strategy universe and categories/gates | Five unchanged; first four INTEGRATED_ALLOCATABLE/CONDITIONAL; Ascend INTEGRATED_GATED/CLOSED |
| Production evidence and recommendation | Unresolved/empty; 100% idle |
| Scope/API/readiness | DECISION_SLEEVE; schema 1.4; whole portfolio NOT_ASSESSED; readiness/proof NOT_ESTABLISHED |
| Evaluation matrix | 49 scenarios / 196 rows; unchanged inputs |
| Other three methods | 147 rows exactly unchanged |
| Proposal/current findings | Match corrected evaluation and bounded interpretation |
| Historical results/audits | Recoverable and unchanged in Git history |
| Deployment | NOT_DEPLOYED; not required/planned |

No new material defect was found in this scoped reconciliation. F1 (MAJOR) and F2 (MINOR) are resolved. Residual F3–F5 remain non-blocking observations, uncorrected: inherited compact proposal layout; illustrative external reward-price basis not observationally corroborated; local validation is not GitHub CI/live execution. No market acquisition, deployment, strategy/gate change, dashboard redesign or new iteration occurred.

**READY_FOR_FINAL_FREEZE**. This decision applies to the corrected synthetic/source-validation capstone state, not public execution readiness or empirical market performance. Iteration 29 was not started.

## 9. Final reviewed commit footprint

Every changed path belongs to F1 source/tests, exact historical-test scoping, corrected evaluation/derivatives, directly affected current-facing result documentation or the correction audit/review record. Temporary outputs, PDF exports, readbacks, screenshots, dependency logs and frontend build side effects are outside the commit. The original verification-only audit remains unchanged.

- `data/final_evaluation_contract.md`
- `docs/final_end_to_end_audit_iteration28_correction.md`
- `docs/final_evaluation_findings_iteration24.md`
- `docs/final_evaluation_iteration23.md`
- `docs/iteration28_correction_review.md`
- `results/final_evaluation_findings.json`
- `results/final_evaluation_iteration23.csv`
- `results/final_evaluation_iteration23.json`
- `results/final_evaluation_iteration23_summary.json`
- `results/final_figures/04_quote_curve.png`
- `results/final_figures/04_quote_curve_data.csv`
- `results/final_figures/07_profit_deltas.png`
- `results/final_figures/07_profit_deltas_data.csv`
- `results/final_figures/08_constraints.png`
- `results/final_figures/08_constraints_data.csv`
- `results/final_figures/captions.md`
- `results/final_results_iteration24_manifest.json`
- `results/final_tables/04_representative_scenarios.csv`
- `results/final_tables/04_representative_scenarios.md`
- `results/final_tables/05_disagreements.csv`
- `results/final_tables/05_disagreements.md`
- `results/final_tables/06_constraint_diagnostics.csv`
- `results/final_tables/06_constraint_diagnostics.md`
- `results/final_tables/07_causality.csv`
- `results/final_tables/07_causality.md`
- `src/ascend_optimizer/amount_optimizer.py`
- `src/ascend_optimizer/final_results.py`
- `tests/test_application_contract.py`
- `tests/test_asset_normalization.py`
- `tests/test_evaluation_policy.py`
- `tests/test_final_evaluation.py`
- `tests/test_final_results.py`
- `tests/test_proposal_reconciliation.py`
