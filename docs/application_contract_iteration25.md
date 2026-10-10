# Iteration 25 — current-request application contract

Schema **1.4** is served by `POST /api/decision-sleeve`. The dashboard uses this endpoint exclusively for its primary recommendation. The existing `/api/optimize` endpoint, schema 1.3 serializer, frontend types and parser remain available unchanged for compatibility. Schema 1.3 legacy measurements are not interpreted as final policy metrics.

```json
{
  "decision_amount_0g": 1000,
  "profile": "Balanced",
  "holding_horizon_days": 90,
  "cash_deadline_days": null,
  "evidence_mode": "PRODUCTION"
}
```

The amount is this run's designated native-0G capital, whether from new capital or explicitly designated vault idle. Existing positions, LP NFTs, staking balances and prior pending exits are exogenous; the API rejects additional holdings inputs. Scope is fixed `DECISION_SLEEVE`; whole-portfolio compliance is always `NOT_ASSESSED`. Whole-portfolio acquisition is not required.

## Modes and solver adapter

`PRODUCTION` is the default. Canonical repository admission and economics providers run unchanged; no price or market fetch occurs. Valuation is `MISSING`, all positive allocations are blocked and the result is `KEEP_IDLE`. The internal unit-price placeholder exists solely to invoke the unchanged fail-closed repository solver; it is not emitted as assessed valuation or economic evidence. Final synthetic policy assessment is `NOT_ASSESSED` in production: unavailable evidence is not rescued by modelled policy inputs. Structural concentration can still be assessed from the actual zero strategy weights. A requested deadline exposes unresolved production strategy timing without preventing idle.

`SYNTHETIC_EVALUATION_ONLY` must be explicitly requested. `data/application_evaluation_config.json` contains the existing transparent modelled economic package, with no scenario matrix, benchmark rows, figures or findings. The adapter reuses the shared exact-candidate economics/admission input primitive and directly invokes `run_amount_optimizer` with the frozen `EVALUATION_POLICY_V1` evaluator. LP/risk/exit/policy configuration files are unchanged. The fixed assessment clock in this package is a replay clock, not an observation or retrieval timestamp; evidence timestamps and blocks remain null. Modelled valuation, APYs, fees, costs, admission and quote curves are not current market claims.

No objective, candidate grid, fee deduction, risk threshold, tie-breaking, gate or revalidation behavior changes. Positive recommendations require selected economics and policy revalidation. A failed revalidation exposes its errors and returns zero strategy weights / fully idle capital, without retaining proposed economics as a recommendation.

## Response dimensions

| Section | Meaning |
|---|---|
| `input` | Exact decision amount, profile, holding horizon, optional exit cash deadline, explicit evidence mode |
| `run_scope` | Decision sleeve; existing positions `EXOGENOUS_NOT_OPTIMIZED`; whole portfolio `NOT_ASSESSED` |
| `valuation` | Qualified/modelled price measurement or explicit missing value |
| `recommendation` | `POLICY_AWARE_AMOUNT_OPTIMIZER`; five allocations, idle, selected economics, revalidation state |
| `strategies` | Exactly five rows including zero allocations; candidate/gate, admission, economics, policy, stress, liquidity, reasons and provenance |
| `risk` | Concentration, underlying-staking stress, **LP absolute stress**, explicit limits and independent-budget qualification |
| `liquidity` | Holding horizon, cash deadline, time-to-cash compatibility; idle time-to-cash zero |
| `policy` | Final policy version, assessed state, bindings, unresolved required constraints, immutable-input identities |
| `solver` | Actual original grid, combinations tested and selected revalidation errors |
| `evidence` | Production versus explicit synthetic mode; unresolved runtime binding |
| `readiness` | Execution readiness and public proof independently `NOT_ESTABLISHED`; public deployment not required/planned |
| `comparison.legacy_linear` | Current-input frozen legacy selection, separately labelled `LEGACY_COMPATIBILITY` and `LIMITED` profit comparability |

Numeric measurements use a discriminated `{state, value, unit, basis}` object. `ASSESSED` contains a finite decimal string; `NOT_ASSESSED`, `MISSING`, `POLICY_UNDEFINED` and `NOT_SUPPORTED` contain null. Unavailable values cannot be rendered as zero. Exact request/candidate capital identities retain decimal strings; economic display values use the accepted 12-place half-even presentation boundary. Net APY uses the existing horizon-return annualization equation, not a new objective.

For allocated strategies, diagnostics describe the selected exact amount. Zero-weight strategies expose an explicitly labelled unselected candidate diagnostic amount, never hypothetical earnings on zero capital. Their risk and policy assessments refer to that same diagnostic candidate. Rejection reasons across tested economic points remain visible. A zero weight can mean a closed gate, unavailable evidence, policy exclusion or an eligible candidate not selected by expected-net-profit ranking; integration remains separately implemented.

Holding horizon is the intended invested duration. Time-to-cash begins at the exit decision. A cash deadline is a feasibility constraint, not an APY haircut or monetary penalty. Synthetic durations are modelled; synchronous LP operations still do not establish successful execution. Production strategy timing remains unresolved.

## Dashboard and comparison boundary

The existing visual foundation is reused for the form, allocation bar/table, expandable strategy details, economics, risk/policy, liquidity, readiness and compact comparison. The wallet/approval/execution milestone UI is removed because public deployment is neither planned nor required. Long diagnostics wrap; phone layouts use a single column. Scope and evidence banners describe the returned request, and errors remain separate from valid idle abstention.

A legacy-only comparison is deliberately used to keep the current-input interface compact. It calls the actual legacy solver through the existing reference-notional compatibility adapter, with the same synthetic package for the submitted amount/horizon. Its fixed/quote economics are linearized, LP risk is a legacy proxy, exit constraints retain old semantics and final cash deadline/range-risk policy is unsupported. Its selection profit is **LIMITED** in comparability, not a common-rescore or performance-improvement claim. In production the comparison is not assessed.

The dashboard imports no Iteration 24 figures, tables, findings, captions or benchmark statistics. Neither API nor dashboard reads committed benchmark rows or representative benchmark scenarios. Iterations 23/24 remain byte-for-byte unchanged.

## Replay and validation

```sh
python -m src.ascend_optimizer.application_contract --decision-amount-0g 1000 --profile Balanced
python -m src.ascend_optimizer.application_contract --decision-amount-0g 1000 --profile Balanced --evidence-mode SYNTHETIC_EVALUATION_ONLY --cash-deadline-days 1
python -m pytest tests/test_application_contract.py tests/test_result_contract.py
cd frontend
node --test tests/*.test.ts
npm run typecheck
npm run build
```

The frontend keeps its existing Node contract-test approach. Tests exercise actual Python/API subprocess results and render the React result component with ReactDOM's static renderer; no large framework is introduced. Next-generated environment/type configuration files are restored to their accepted versions after build. The deployment audit checks the original UI hashes at its pinned Iteration 17 commit; it continues to check canonical evidence/configuration/contracts against current files. Its historical audit artifact is unchanged.

**Iteration 25 migrates the application interface to the final decision-sleeve policy-aware optimizer contract. It does not reuse Iteration 24 benchmark findings or figures, does not change optimization semantics, and does not establish live execution readiness or public deployment proof.**
