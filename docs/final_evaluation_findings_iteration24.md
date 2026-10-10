# Capstone findings — CAPSTONE_FINDINGS_V1

SYNTHETIC_EVALUATION_ONLY. Derived exclusively from accepted FINAL_EVALUATION_V1 artifacts at `7abfa1a347f35985052bee617e1bd82165f471f0`. This document freezes interpretation for later proposal work; the proposal itself is unchanged.

## 1. Evaluation scope

The evaluation is deterministic, synthetic and DECISION_SLEEVE only. It compares exactly four methods over 49 scenarios / 196 rows, covering exactly five independent MVP strategies. Existing holdings/LP NFTs/pending exits remain exogenous and whole-portfolio compliance is NOT_ASSESSED. Ascend is canonically CLOSED and has zero recommendation weight in every row. No public deployment is required or planned; these results make no execution-readiness or public deployment claim.

## 2. Different allocation behavior

The policy-aware amount-aware optimizer produced a different allocation from the legacy linear optimizer in 27 of the 49 defined deterministic synthetic scenarios. This is a result over the defined experiment matrix, not an estimate of real-world disagreement probability. Any-method allocation disagreement appears in 39 scenarios. An allocation disagreement does not itself establish profit improvement.

## 3. Economics nonlinearity

**Fixed-cost controlled paired ablation:** FIXED_100 versus FIXED_ZERO_CONTROL holds notional, return, horizon and policy constant while removing the fixed lifecycle charge. The frozen final-method allocation changes from idle to positive Native exposure. Charging fixed costs once at the actual candidate amount can make small allocations uneconomic. FIXED_1000 and FIXED_10000 provide additional notional sensitivity context. This is causal sensitivity within the synthetic model only.

**Quote-curve controlled paired ablation:** QUOTE_CURVE versus QUOTE_CONSTANT_CONTROL holds return, notional and policy constant while removing the amount slope of the synthetic LP quote curve. The chosen Jaine amount changes. Exact candidate quote assumptions can change selected LP allocation within this model. This is the second supported paired causal sensitivity; neither pair establishes an observed market effect.

## 4. Profile and risk feasibility

LP_PROGRESSION_CONSERVATIVE, LP_PROGRESSION_BALANCED and LP_PROGRESSION_AGGRESSIVE select Jaine 30.0%, 60.0% and 80.0%, respectively, under the same LP economics. Profile-dependent feasibility changes exposure through the combination of concentration limits, LP absolute-stress policy and the discrete grid. The entire progression cannot be attributed to LP stress alone. Absolute LP loss is the total position-loss measure; IL and HODL market loss remain diagnostics and are not added again.

## 5. Liquidity and cash deadlines

An explicit cash deadline can make an otherwise economically attractive asynchronous strategy infeasible. DEADLINE_STAKING_1 excludes Native/Gimo from the final allocation; DEADLINE_STAKING_8 permits Native but not Gimo; DEADLINE_STAKING_15 permits both. The underlying durations are MODELLED / SYNTHETIC_EVALUATION_ONLY. They are not guaranteed withdrawal times or observations of live liquidity. Holding horizon, time-to-cash after an exit decision and cash deadline are distinct.

## 6. Abstention is a valid decision

Keeping capital idle is a first-class optimizer outcome rather than a failure state. NEGATIVE, MISSING_RETURN, MISSING_COST, QUOTE_MISMATCH, ADMISSION_FAILURE and DEADLINE_STAKING_1 show different reasons for abstention. Risk feasibility can also exclude positive candidate allocations without forcing all scenarios idle. Missing required return/cost/quotes never become zero evidence. Canonical production runs remain 100% idle for all three profiles because runtime binding/admission/economics are unresolved, separately from synthetic evaluation outcomes. Idle causes must remain distinguishable.

## 7. Legacy comparison

The unchanged legacy optimizer is a simpler/reference approximation, not characterized as wrong. It uses reference-notional linearization, fractionally scales reference effects that are actually fixed/amount-dependent, uses the legacy LP stress proxy and legacy exit limits, and lacks final cash-deadline/range-risk semantics. The final method uses exact candidate economics, fixed cost once, exact-amount LP quotes, range-aware LP absolute stress, cash-deadline feasibility and selected-point economics/policy revalidation. These capability differences are explicit in Table 1; common rescoring does not retrofit capabilities into a baseline.

## 8. Profit comparison

Under the common exact-allocation rescore used solely for comparison, the defined matrix has a positive mean amount-aware-minus-legacy profit delta ($43.40), while the median is zero ($0.00). Across 49 comparable cases, 19 deltas are positive, 7 negative and 23 zero. Not all disagreements improve profit. Common post-selection rescore is not the legacy optimizer's own objective; selection-objective comparability is LIMITED. 4 simple-baseline rows lack qualified common economics and are separately LIMITED. No percentage-return superiority, forecast accuracy or production-performance claim follows. TIE has equal common profit and different secondary selection behavior.

## 9. Causal sensitivity versus diagnostic association

Only the controlled fixed-cost and quote-curve paired ablations support isolated causal sensitivity within this synthetic model. Ordinary contributor annotations for LP stress, staking stress, concentration, deadline, grid, fixed cost and quote effects are diagnostic association, not isolated causal effects. MULTIPLE classifications retain more than one contributor. Table 7 and figure captions preserve this distinction. The constraint counts concern candidate exclusion or selected binding and are nonexclusive deterministic scenario counts, not probabilities or real-world frequencies.

## 10. Limitations

- Synthetic economic inputs and modelled 0G valuation.
- Synthetic analytical quote curve, not captured executable market quotes.
- Modelled deterministic stress assumptions and modelled exit durations.
- Ascend gate CLOSED; hypothetical economic analysis does not make it allocatable.
- No public deployment, no live admission and no execution-ready proof.
- No observational freshness policy is established by this evaluation; canonical evidence remains empty.
- No whole-portfolio optimization or compliance assessment.
- Discrete 0.1 amount grid limits attainable weights.
- Legacy selection objective is only partially comparable to final exact economics.
- The deterministic matrix is not statistically representative; it provides no probabilities, confidence intervals or forecasts.
- Independent stress budgets do not imply correlated joint events.
- Findings cover the chosen synthetic ranges and assumptions, not optimal or deployed LP positions.

## 11. Contribution

The capstone contributes an evidence-qualified, amount-aware decision-sleeve optimizer that separates expected economics, technical admission, deterministic risk, liquidity timing and execution proof, and demonstrates through controlled synthetic evaluation where exact candidate economics and explicit feasibility constraints alter recommendations relative to simpler allocation approaches.

## Reproduction and source integrity

Run `python tools/generate_final_results.py` and `python tools/generate_final_results.py --check`. The generator verifies pinned source SHA-256 hashes and counts without invoking an optimizer. The manifest lists sources, outputs, figure data, captions and this document's hash. CSVs retain accepted numerical precision; Markdown/figure labels round percentages to one decimal and currency to cents. Matplotlib Agg / DejaVu Sans PNGs have fixed metadata and no timestamp. Exact figure bytes require the renderer/font versions fingerprinted in the manifest; check mode fails on drift. Install the optional pinned renderer with `python -m pip install -r requirements-results.txt` when needed.

Iteration 24 presents and interprets the frozen Iteration 23 deterministic synthetic evaluation. Its figures and findings describe behavior within the defined experiment matrix and do not constitute empirical market probabilities, forecasts, live execution results or proof of production performance.
