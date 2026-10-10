# Iteration 22: final synthetic decision-sleeve policy

Iteration 22 freezes synthetic decision-sleeve evaluation policy. Its profile stress limits and deadline checks are capstone evaluation constraints, not empirically calibrated production risk limits or live liquidity guarantees.

The scope, policy matrix, deadline contract, algorithm sequence and legacy separation matrix are in data/evaluation_policy_contract.md. Whole-portfolio state acquisition is no longer a required capstone completion dependency. Existing holdings and prior pending exits remain exogenous; whole_portfolio_compliance stays NOT_ASSESSED. Public deployment remains neither required nor planned.

## Reproducible feasibility examples

All examples are MODELLED / SYNTHETIC_EVALUATION_ONLY, with a 1,000 decision value. They use existing synthetic LP and risk/exit model configurations, not canonical live evidence.

| Example | Main condition | Expected policy state |
|---|---|---|
| All pass | Conservative, Native .2 + Jaine .1, deadline 8 days | PASS |
| Concentration failure | Native .5 exceeds Conservative .4 | FAIL |
| Staking failure | Native .3 + Gimo .3; independent weighted budget .03 exceeds .02 | FAIL |
| LP absolute failure | Jaine .4 + Oku .4; total LP loss budget exceeds .05 | FAIL |
| Deadline failure | Native .2, 7-day deadline below modelled 7.1 days | FAIL |
| Unresolved exit | Native .2, deadline requested, exit input missing | UNRESOLVED / infeasible |
| Zero-weight unresolved | Jaine .1 with zero Native and missing Native exit | PASS |
| Ascend prohibited | Positive .1, even with explicit analysis-only diagnostics | FAIL |
| Partial idle | Native .2 with idle .8 | PASS |
| All idle | No positive strategies, deadline 0 | PASS |

The results JSON contains full typed checks, limits, bindings, input identities and actual allocation-scaled risk contributions for these examples. Additional tests cover missing positive LP risk, exact deadline boundaries, invalid inputs and original admission/economics failures.

## Focused amount-aware checks

These six targeted search examples exercise the integration; they are not the final benchmark matrix or four-algorithm comparison.

| Example | Feasibility result | Objective behavior |
|---|---|---|
| Jaine / Conservative | .3 selected; profitable .4 point fails absolute LP budget | Profit unchanged; failing sleeve removed |
| Jaine / Balanced | .6 selected under explicit .10 LP limit and existing concentration | Same ordinary economics |
| Jaine / Aggressive | .8 selected under explicit .20 LP limit and existing concentration | Same ordinary economics |
| Native / tight deadline 1 day | Async positive allocations removed; 100% idle | No APY or monetary penalty |
| Native / relaxed deadline 8 days | .8 restored as feasible | Same candidate profits as tight-deadline run |
| Native/Jaine / unequal modelled APY | Feasible higher-profit Native points rank ahead of LP | Existing net-profit objective and tie-breaking retained |

Selected recommendations revalidate policy version/provenance, risk scenarios, LP config identities, exit config identities and deadline. Tests deliberately change each source between stages and confirm that recommendation becomes null. This is independent of existing admission/economics revalidation, which is retained.

## Frozen baseline and reproduction

The results artifact contains the canonical Conservative/Balanced/Aggressive production replay at the existing explicit as_of=2026-10-09T14:30:00+00:00. All remain 100% idle with unresolved runtime configurations and empty admission/economics. That time is a replay context, not an evidence observation or invented block.

```bash
python tools/evaluation_policy_preflight.py --check results/evaluation_policy_iteration22.json
python -m pytest -q tests/test_evaluation_policy.py
python -m pytest -q tests/test_risk_exit.py tests/test_lp_range_stress.py tests/test_economics_evidence.py
python -m pytest -q
python -m pytest -q tests/test_result_contract.py
npm --prefix frontend run test:contract
python tools/audit_deployment_history.py --check
python tools/deployment_preflight.py
python tools/economics_preflight.py
git diff --check
```

Without --check, the focused validation tool emits the committed JSON to stdout. It uses temporary test-only economics/admission assumptions and never writes into canonical evidence. There are no new observation timestamps, blocks, market captures or transaction paths. No final experiment harness, dashboard/proposal/README rewrite, whole-portfolio acquisition or Iteration 23 work is included.

## Validation record

- New policy suite: **45 passed**.
- Iteration 21 risk/exit: **52 passed**; Iteration 20 LP: **64 passed**; Iteration 19 economics: **72 passed** (combined prior suites **188**).
- Full Python suite: **649 passed**, with one existing Gimo/pandas FutureWarning.
- Result-contract tests: **10 passed**; API tests: **7 passed**.
- Exact replay: **10 feasibility examples / 6 focused amount-aware examples**.
- Iteration 17 audit replay, Iteration 18 deployment preflight and frozen dataset comparison: passed.
- `git diff --check`: passed.

Solidity/contracts and frontend/types were untouched. Hardhat and frontend build/typecheck were not run. The API entry points/default transport remain unchanged; result/API regressions were run because the optional Python result adds synthetic policy diagnostics.
