# Iteration 23 — final evaluation harness

The four-method contract is frozen in `data/final_evaluation_config.json` and `data/final_evaluation_contract.md`. The dedicated harness invokes the actual legacy linear solver and actual Iteration 22 policy-aware amount solver. Transparent simple baselines live separately. No production, optimizer, API, profile, policy, LP config or canonical evidence file was modified.

## Matrix and results

49 deterministic synthetic scenarios produce **196 normalized rows**. The core is 27 scenarios / 108 rows; 22 targeted scenarios cover deadlines, fixed-cost/quote ablations, profile progression, missing evidence, admission, gate, negative economics and ties. These are enumerated inputs, not random samples or market observations.

| Method | Main capability | Main limitation | Positive recommendation rows | 100% idle rows |
|---|---|---|---:|---:|
| HIGHEST_YIELD_BASELINE | Ranked positive apparent APY with capped fill | No fixed-cost/quote/risk/deadline selection | 45 | 4 |
| EQUAL_WEIGHT_ELIGIBLE_BASELINE | Equal capped allocation over eligible returns | No economics-aware weight optimization | 45 | 4 |
| LEGACY_LINEAR_OPTIMIZER | Actual frozen linear constraints | Reference-cost/quote linearization; legacy LP/exit limits | 35 | 14 |
| POLICY_AWARE_AMOUNT_OPTIMIZER | Exact amount economics and final policy feasibility | Discrete grid; synthetic inputs only | 36 | 13 |

39 scenarios have some method disagreement; **27** have amount-aware versus legacy allocation differences.

| Primary difference driver | Count | Qualification |
|---|---:|---|
| MULTIPLE | 26 | Multiple supported diagnostic contributors; not isolated causal attribution |
| OBJECTIVE_DIFFERENCE | 1 | Equal primary profit, different secondary tie selection |

Common exact-allocation rescoring permits 49 amount-versus-legacy profit deltas. Mean is **$43.395279634804**, median **$0** in this defined matrix. This rescoring is separate from each method's selection objective. Legacy selection-profit comparisons remain `LIMITED`; **4 simple-baseline rows** have unavailable common economics and are also `LIMITED`. No missing cost/quote is substituted by zero, and no improvement percentage is reported.

Amount-method candidate exclusions or selected-binding diagnostics occur in 34 scenarios for LP absolute stress, 31 for concentration, 13 for staking stress and 4 for cash deadline. These are distinct scenario counts over explored candidates/selected boundaries, not assertions that every selected constraint equals its limit. Gate exclusions appear in all 49 scenarios; admission/evidence exclusions in 12. Deadline diagnostics exclude potential modelled Native exits in 2 cases and Gimo exits in 4. The amount method idles while another invests in 9 cases, and invests while another idles in 4.

## Representative reproducible behavior

| Input | Policy-aware result | What it demonstrates |
|---|---|---|
| FIXED_100: Native 20% APY, $25 lifecycle charge, 100 0G / 365 days | 100% idle | Small positive gross income cannot cover the fixed charge |
| FIXED_1000 / FIXED_10000, same economics | Native 60%, idle 40% | Actual allocated amount changes cost viability |
| FIXED_ZERO_CONTROL at 100 0G | Native 60% | Explicit paired fixed-cost sensitivity |
| LP_PROGRESSION: same Jaine-only attractive return | Conservative 30%, Balanced 60%, Aggressive 80% | Separate LP absolute-loss namespace and concentration/grid |
| QUOTE_CURVE vs QUOTE_CONSTANT_CONTROL | Jaine 10% vs 60% | Exact-amount synthetic quote curve changes selection |
| DEADLINE_STAKING_1 | 100% idle | Both async staking exits fail the one-day deadline |
| DEADLINE_STAKING_8 | Native 60%, idle 40% | Native 7.1 modelled days fits; Gimo 10.1 does not |
| DEADLINE_STAKING_15 | Native 60%, Gimo 40% | Both modelled exit delays fit |
| NEGATIVE / MISSING_RETURN / ADMISSION_FAILURE | All methods idle | Idle is a legitimate outcome |
| MISSING_COST / QUOTE_MISMATCH | Final and legacy idle; simple baseline rescore unavailable | Unsupported screening and missing economics remain explicit |
| ASCEND_ATTRACTIVE | All methods idle | Attractive hypothetical economics cannot open CLOSED gate |
| TIE | Different legacy/final allocation with $0 common-profit delta | Secondary selection behavior is not profit improvement |

Risk, economics, quote validity, technical admission and public proof remain distinct. All five recommendation weights are explicit; Ascend is zero in every row. Expected profit is still the final solver objective; policy only filters feasibility. Range-aware absolute LP loss enters risk once, while quote/slippage/cost effects stay in economics. Deadlines measure delay from an exit decision, separately from holding horizon.

## Artifacts and reproducibility

- `results/final_evaluation_iteration23.json`: full scenario package, dependency fingerprints, normalized rows, method diagnostics, common rescoring and frozen production baseline.
- `results/final_evaluation_iteration23.csv`: one row per scenario/method, explicit weights, typed unsupported values and selection capability fields.
- `results/final_evaluation_iteration23_summary.json`: deterministic counts, paired sensitivity counts, qualified profit deltas and disagreement attribution.

Run `python tools/run_final_evaluation.py --check` for byte-for-byte verification of all three. No figures are generated. No RPC, market fetch, hidden clock, random values or observed timestamps/blocks are introduced.

Production replay at the fixed inherited analysis clock remains 100% idle for Conservative/Balanced/Aggressive. Runtime configs remain UNRESOLVED; admission remains headers-only; canonical return/quote/cost records stay empty. Ascend stays CLOSED. No public deployment is required or planned, and whole-portfolio compliance is NOT_ASSESSED.

Iteration 23 evaluates deterministic synthetic scenarios. Differences between algorithms describe behavior within the defined experiment matrix; they are not empirical probabilities, market-return forecasts, or evidence of live execution performance.

Validation: **59** focused harness tests; **233** prior iteration tests (45 policy + 52 risk/exit + 64 LP + 72 economics); **708** full Python tests; **10** result-contract tests; **7** API contract tests. All three artifacts replay byte-for-byte, including `PYTHONHASHSEED=23`. Iteration 17 audit replay, Iteration 18 deployment preflight and `git diff --check` pass. The full suite retains one existing pandas collector FutureWarning. Solidity/frontend/types were untouched; Hardhat and frontend build/typecheck were not needed.
