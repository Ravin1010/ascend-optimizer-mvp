# Iteration 20: synthetic LP range evaluation

The Iteration 20 LP range/stress results are synthetic evaluation results, not observations of deployed Jaine/Oku positions or predictions of future market returns. No public deployment is performed, required or planned. Runtime/admission/economics datasets and all portfolio-risk limits remain unchanged.

## Synthetic configuration matrix

Full stable config IDs are in data/lp_evaluation_config.json and the results JSON. Both share existing token references as an explicit scenario choice; fee, range, composition, reference price and router metadata are independently chosen. Jaine is narrower to exercise full conversion at ±20%; Oku is wider with inverse ordering to test orientation and asymmetry. Neither range is claimed optimal.

| Strategy | Config ID suffix | Venue | Token order | Economic orientation | Fee | Tick spacing | Tick range | Target USDC | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| JAINE_LP_0G_USDC | edbd3f5f802496df0f287b97ebaedf6ada257b74f47e4dc7f8710731000cac97 | JAINE | W0G / USDC.e | USDC.e per W0G | 0.3% | 60 | [-277800, -275400] | 61.17% rounded range-implied | MODELLED / SYNTHETIC |
| OKU_LP_0G_USDC | c3bfea639baf4e1b2e6124a6e29697e302e0ae889fc37f9a07013653fc369550 | OKU | USDC.e / W0G | USDC.e per W0G | 0.05% | 10 | [273000, 279000] | 59.75% rounded range-implied | MODELLED / SYNTHETIC |

Notional is 1,000 modelled USDC.e value per position. Jaine reference price is 1; Oku is 1.1 USDC.e/W0G. Target is descriptive; exact initial inventory is calculated rather than rounded to the target. Bound values and full precision initial amounts are in the JSON.

## Per-strategy stress results

| Strategy | Shock | Range state | W0G | USDC.e | LP value | HODL value | IL | Absolute LP loss | HODL market loss |
|---|---|---|---|---|---|---|---|---|---|
| JAINE_LP_0G_USDC | -20% | BELOW_RANGE | 1046.851495 | 0.000000 | 837.481196 | 922.349912 | -9.201358% | 16.251880% | 7.765009% |
| JAINE_LP_0G_USDC | -10% | IN_RANGE | 853.418749 | 170.452155 | 938.529029 | 961.174956 | -2.356067% | 6.147097% | 3.882504% |
| JAINE_LP_0G_USDC | +10% | ABOVE_RANGE | 0.000000 | 1018.357573 | 1018.357573 | 1038.825044 | -1.970252% | 0.000000% | 0.000000% |
| JAINE_LP_0G_USDC | +20% | ABOVE_RANGE | 0.000000 | 1018.357573 | 1018.357573 | 1077.650088 | -5.502019% | 0.000000% | 0.000000% |
| OKU_LP_0G_USDC | -20% | IN_RANGE | 752.282495 | 217.358919 | 879.367514 | 919.500161 | -4.364616% | 12.063249% | 8.049984% |
| OKU_LP_0G_USDC | -10% | IN_RANGE | 542.975691 | 412.721903 | 950.267837 | 959.750081 | -0.987991% | 4.973216% | 4.024992% |
| OKU_LP_0G_USDC | +10% | IN_RANGE | 213.572136 | 773.249542 | 1031.671826 | 1040.249919 | -0.824619% | 0.000000% | 0.000000% |
| OKU_LP_0G_USDC | +20% | IN_RANGE | 80.698818 | 941.175343 | 1047.697783 | 1080.499839 | -3.035822% | 0.000000% | 0.000000% |

All losses use the definitions in data/lp_evaluation_contract.md. Positive price shocks can yield positive absolute value change with negative IL. Downside LP loss includes market exposure and the rebalancing effect; IL alone is not the total loss.

## Legacy migration audit

| Legacy field | Current use | New replacement | Migrated now? | Future action |
|---|---|---|---|---|
| MODELLED_LP_STRESS_20PCT | lp_execution.py defines generic [0.8P0,1.2P0] worst IL; pipeline.py:resolve_runtime_lp_exposures and amount_optimizer.py:evaluate_candidate supply missing proxy values | lp_range_stress.py versioned config-specific inventory/shock outputs | No | Iteration 21 must choose how explicit LP-value stress participates in five-strategy aggregation, without substituting absolute loss for IL silently |
| lp_stress_loss_20pct | exposure_engine.py resolves the snapshot field; optimizer.py evaluates and constrains its weighted sum; amount_optimizer.py candidate exposure and portfolio constraint use it against max_portfolio_lp_il_stress | Separate IL, absolute LP loss and HODL market loss per config/scenario | No | Preserve compatibility until aggregation/serialization migration is explicitly designed and tested |
| lp_stress_loss_20pct (transport) | data_loader.py columns, readiness.py runtime-resolvable diagnostics, live_optimize.py schema/display; collector/ascend-model rows emit missing values; source_registry.csv documents generic model provenance | New results artifact with typed StressResult; no schema 1.3 change | No | Reconcile risk readiness, serialized labels and UI only with the later aggregation contract |

The generic proxy is legacy compatibility only, not the final methodology. New range evaluation never imports it. Existing baseline and synthetic optimizer compatibility behavior remain intact.

## Reproduction

```bash
python tools/lp_range_stress_preflight.py
python tools/lp_range_stress_preflight.py --check results/lp_range_stress_iteration20.json
python -m pytest -q tests/test_lp_range_stress.py tests/test_economics_evidence.py
python -m pytest -q
python tools/economics_preflight.py
python tools/audit_deployment_history.py --check
python tools/deployment_preflight.py
git diff --check
```

The replay tool is read-only and has no RPC, wallet or transaction path. stdout can regenerate the committed results JSON. No observation/retrieval timestamp or block is fabricated.

## Frozen baseline

At the Iteration 19 explicit as_of=2026-10-09T14:30:00+00:00, Conservative, Balanced and Aggressive remain 100% idle under canonical repository evidence. All three economics datasets remain empty, five runtime configs UNRESOLVED, admission CSV headers-only and Ascend CLOSED. This is a replay time, not a new evidence capture.

Broader five-strategy stress aggregation is deferred to Iteration 21. No optimizer solver, profile, frontend, Solidity, dashboard or proposal change is included.

## Validation record

- New LP range suite: **64 passing tests**.
- Iteration 19 economics regression: **72 passing tests**; combined focused suite **136**.
- Full Python regression: **552 passing tests** (one existing Gimo/pandas FutureWarning).
- Result-contract regression: **10 passing tests**.
- API contract regression: **7 passing tests**.
- Synthetic replay: **2 configurations / 8 shock results**, exact JSON equality.
- Iteration 17 audit replay and Iteration 18 deployment preflight: passed.
- Frozen dataset comparison against accepted b9c8bf972ec14d75ab390d0691d0a862e9fefcde: unchanged.
- `git diff --check`: passed.

Solidity/contracts and frontend/types were untouched, so Hardhat and frontend build/typecheck were not run. Result/API checks were run as additional compatibility regression; no result schema or route changed.
