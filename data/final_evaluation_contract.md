# FINAL_EVALUATION_V1 — deterministic synthetic comparison

Every scenario is `SYNTHETIC_EVALUATION_ONLY`. This contract evaluates a **new native-0G decision sleeve**, not holdings or a whole vault. Whole-portfolio compliance is `NOT_ASSESSED`. No public deployment is required/planned. No result establishes technical admission, live liquidity, public execution readiness, probabilities or market forecasts.

The canonical scenario list is enumerated in `final_evaluation_config.json` before execution: 27 core scenarios (3 profiles × 100/1000/10000 0G × 30/90/365 days, no deadline), plus 22 targeted scenarios, each with its own purpose, modifications and hypothesis. Four methods per scenario yield **196 rows**, including **108 core rows**. Hypotheses describe potential behavior, not predetermined outputs.

## Fair comparison and method rules

Shared experiment assumptions must be identical wherever methods support them. Unsupported capabilities are reported, not silently approximated. The capability matrix below is selection-time capability; common post-selection diagnostics do not grant a method capabilities it lacks.

| Feature | Highest yield | Equal weight | Legacy linear | Policy-aware amount |
|---|---|---|---|---|
| Decision sleeve, canonical membership/gate | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Concentration | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Exact amount economics | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Fixed lifecycle cost | NOT_SUPPORTED | NOT_SUPPORTED | APPROXIMATED | SUPPORTED |
| LP entry/exit quote effects | NOT_SUPPORTED | NOT_SUPPORTED | APPROXIMATED | SUPPORTED |
| Admission evidence | APPROXIMATED | APPROXIMATED | APPROXIMATED | SUPPORTED |
| Range-aware LP stress | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Legacy LP stress proxy | NOT_SUPPORTED | NOT_SUPPORTED | LEGACY_ONLY | NOT_SUPPORTED |
| Staking stress | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | SUPPORTED |
| Exit time | NOT_SUPPORTED | NOT_SUPPORTED | LEGACY_ONLY | SUPPORTED |
| Optional cash deadline | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Idle | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Amount-specific feasibility | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Selected-point revalidation | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |

**Highest yield**: require a qualified modelled return, structural membership, open/conditional gate and synthetic admission assumption at the full decision notional. Rank positive annual net-of-protocol-fee APYs descending, strategy ID ascending for ties. Fill each ranked strategy up to its concentration cap until capital is exhausted. Remainder is idle. No fixed-cost, quote, risk or deadline search is hidden in this rule.

**Equal weight**: same eligibility; give each positive-return eligible strategy `min(1/n, concentration cap)`. Leave residual idle. No iterative redistribution or profit maximization. Both simple methods exclude missing returns and explicit admission failures; they cannot screen costs/quotes they do not support. Their common economic rescore can therefore be negative or `NOT_ASSESSED`.

**Legacy linear**: call the actual frozen `optimizer.optimize_portfolio` with a deterministic compatibility table. Normalize Iteration 19 economics at the **full decision notional** and translate its net horizon return to one linear coefficient. The solver scales that coefficient by allocation weight, which fractionally scales the reference fixed charge and assumes reference quotes apply at other amounts. These are explicitly `APPROXIMATED`, not exact amount semantics. Missing return/cost/reference quote excludes a strategy. Synthetic admission at reference notional becomes a boolean eligibility with liquidity cap equal to decision value; this is an explicit modelled capacity assumption, not deployed headroom. Iteration 21 underlying staking severity is 5%; the unchanged legacy LP proxy is 0.06358893302521518. Legacy exit limits use Iteration 21 synthetic time-to-cash. There is no new LP absolute-loss threshold or cash-deadline enforcement. No algorithm or profile threshold is changed.

**Policy-aware amount**: call actual `run_amount_optimizer` with explicit synthetic economics and policy modes. The original 0.1 grid, exact Decimal candidate identities, expected-net-profit objective, fixed-cost-once semantics, idle/ties and selected economic/policy revalidation remain unchanged. Iteration 22 feasibility owns concentration, independent staking budgets, LP absolute loss and optional deadline. Ascend remains zero. Snapshot route columns are compatibility scaffolding; canonical economics never come from demo snapshot numbers in this harness.

## Shared package

`SYNTHETIC_ECONOMIC_PACKAGE_V1` is an in-memory adapter of the existing Iteration 19 schema and normalizer, not a second economics taxonomy. Valuation is an explicit modelled $1/0G convention. Base APYs, already net of protocol fees, are Native 12%, Gimo 14%, Jaine 24%, Oku 20%, Ascend 50%; lifecycle fixed charges are $2/$3/$5/$4/$3. These arbitrary evaluation values are not empirical estimates. No incentives are added and embedded returns/fees are counted once.

Every other required cost component has explicit **synthetic structural-zero** evidence with static experiment provenance. This includes no user-capital bridge: remote dependencies do not imply capital bridging. Missing cost scenarios delete evidence; missing never becomes zero.

LP per-direction quote loss is `base + slope × exact candidate 0G amount / reference 0G amount`, with base 0.0005, slope 0.002, reference 1000. This is a versioned synthetic analytical curve, **not interpolation of observed quotes**. ENTRY/EXIT each get an exact amount/context-specific quote identity. Mathematical quotes are available at continuous legacy/baseline allocation amounts for common rescoring; that does not make their selection amount-aware. Pool/reference context is synthetic and unbound to canonical runtime configuration. Jaine/Oku use independent fee/config references from Iteration 20. Risk, LP configurations, exit configurations and policy reuse Iterations 20–22 unchanged; their fingerprints are included in raw results.

The fixed replay `as_of` is inherited from prior validation (2026-10-09T14:30:00Z), **not an observation/retrieval timestamp**. Synthetic records contain null observation/retrieval/block fields. No RPC, clock, random generator or market acquisition occurs.

## Normalized fields and comparison

Common gross income, net profit/rate/APY, lifecycle/fixed costs and quote loss are **post-selection exact-allocation rescoring** through Iteration 19, using the same package. This is distinct from `method_reported_profit` and selection-time capabilities. Simple methods' reported profit and exact selection costs are `NOT_SUPPORTED`; missing common economics are `NOT_ASSESSED`, never zero. Idle-only totals are genuine structural zeros because no position incurs economics.

`profit_comparability = DIRECT_COMMON_RESCORE` means both common scores use the same economics at their respective exact selected amounts. Pairwise delta is computed only on that basis. Legacy selection objective versus final selection objective is always `LIMITED` because of reference linearization. Rows with unavailable rescoring are `LIMITED`; no improvement percentages are emitted. `net_apy` annualizes the sleeve net horizon return only when its domain is meaningful; it is not a forecast.

Risk and deadline posthoc diagnostics use RISK_STRESS_V1/EVALUATION_POLICY_V1 for all methods, with explicit `final_policy_enforced`. Unsupported deadline enforcement stays `NOT_SUPPORTED` even if posthoc diagnostics happen to pass. `feasibility_state` means only the method's supported constraints; it does not mean execution readiness. Total risk is an independent stress-budget envelope, not a joint-event/correlation/probability claim. IL and HODL market loss are not added to LP absolute loss. No execution loss is added to mathematical stress.

Presentation uses Decimal, 60-digit intermediate context and round-half-even 12-place numeric display; after quantization, values within an absolute tolerance of `1e-12` (one display unit) of a coarser decimal are snapped to the coarsest qualifying grid, checking integer through 8 decimal places in order; legacy solver internals remain floats. Display weights are quantized once, with residual idle derived exactly. Exact model inputs/config IDs remain strings and are not snapped. Ordinary high-precision display values outside this tolerance retain all 12 places (for example, `43.395279634804` and `0.120632485555`). Restricting the simpler grids to at most 8 places protects genuine 9–12-place model/allocation values from losing a meaningful final digit. Snapping has no relative tolerance or solver effect. No NaN/Infinity is emitted. Counts remain integers.

## Attribution and summaries

Disagreement attribution records **diagnostic contributors, not isolated causal claims**. Final-policy violations of the legacy allocation support stress/deadline contributors. Fixed-cost/reference quote objective differences and off-grid legacy weights identify additional method differences. More than one contributor is `MULTIPLE`; attribution does not invent a sole cause. Explicit paired ablations (`FIXED_100`/`FIXED_ZERO_CONTROL`, `QUOTE_CURVE`/`QUOTE_CONSTANT_CONTROL`) alone support causal sensitivity counts within this synthetic model.

Constraint counts distinguish selected binding constraints and candidate exclusions; they are scenario counts, not rejected candidate counts or frequencies in markets. Gate/admission/evidence counts are counts of scenarios with excluded strategy diagnostics. Deadline exclusions describe modelled potential Native/Gimo exits, not selected allocation claims. Mean/median profit differences summarize this enumerated matrix, not statistical inference.

Whole-portfolio state acquisition, deployment, production admission and fresh economics collection remain outside required completion. Runtime config, admission and canonical economics remain untouched; production stays idle. Final figures/dashboard/README/proposal changes are deferred.

## Reproduction

```bash
python tools/run_final_evaluation.py
python tools/run_final_evaluation.py --check
python -m pytest tests/test_final_evaluation.py -q
```

The runner writes raw JSON, explicit five-weight CSV and summary JSON only. `--check` verifies all three byte-for-byte. Determinism assumes the same mathematical/solver dependencies; no wall-clock field enters artifacts.

The `TIE` scenario has equal common profit with different allocations: `OBJECTIVE_DIFFERENCE` is qualified by `SECONDARY_TIE_SELECTION_NOT_PROFIT_FORMULA`. It describes the proposed method's explicit secondary ordering versus the legacy solver's choice among equal-profit optima, not a different primary profit formula or improvement.
