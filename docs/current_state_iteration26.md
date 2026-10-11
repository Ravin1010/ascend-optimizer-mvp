# Current project state — Iteration 26

This current-facing status supersedes the milestone descriptions in historical Iteration 13/17/18/19/20/21 documents where later iterations have added policy, evaluation or schema functionality. Their evidence/results remain scoped to their original freeze points. No frozen result or canonical dataset is rewritten.

## Architecture/status dimensions

| Dimension | Current meaning/state |
|---|---|
| Decision asset | Native 0G only; explicit decision amount |
| Scope | DECISION_SLEEVE; existing positions EXOGENOUS_NOT_OPTIMIZED |
| Whole-portfolio compliance | NOT_ASSESSED; state acquisition not required for completion |
| Strategy universe | Exactly Native, Gimo, Jaine, Oku and Ascend |
| Canonical category | First four INTEGRATED_ALLOCATABLE; Ascend INTEGRATED_GATED |
| Structural candidate / integration | All five true / IMPLEMENTED |
| Allocation gate | First four CONDITIONAL; Ascend CLOSED |
| Protocol availability | Canonical metadata describes external protocols; not capstone deployment |
| Evidence readiness | Required canonical admission/economics missing; no current market claim |
| Runtime configuration | All five UNRESOLVED |
| Current recommendation | Request-specific; canonical production 100% idle |
| Execution readiness / public proof | NOT_ESTABLISHED / NOT_ESTABLISHED |
| Public deployment | NOT_REQUIRED_NOT_PLANNED |
| Application | Schema 1.4 /api/decision-sleeve; schema 1.3 compatibility-only |
| Method | POLICY_AWARE_AMOUNT_OPTIMIZER primary; legacy linear reference/compatibility |

`INTEGRATED_ALLOCATABLE` denotes structural membership subject to qualified evidence, admission, economics, policy and current-request feasibility. It does not clear an allocation gate or establish execution readiness. Production fails closed on canonical evidence; positive modelled results require explicit `SYNTHETIC_EVALUATION_ONLY`. No transaction proof is required to complete this prototype capstone.

The final evaluation path uses exact candidate economics, fixed cost once, exact-amount LP quotes, selected-point revalidation and expected-net-profit ranking among feasible candidates. Risk/deadline limits are feasibility constraints rather than monetary penalties. LP absolute stress has evaluation-only limits 5% / 10% / 20%; the IL proxy is legacy compatibility only. Independent staking/LP stress budgets do not assert simultaneous correlated events. Holding horizon, exit time-to-native-0G and optional cash deadline are separate. Modelled exit durations are not protocol guarantees.

## Normalization contract — ASSET_NORMALIZATION_V1

`src/ascend_optimizer/asset_normalization.py` is a semantic helper, deliberately outside solver, API request parsing and valuation logic. It performs no wrapping transaction, fetching, balance conversion or price derivation. `normalize_to_economic_asset(NATIVE_0G)` and `normalize_to_economic_asset(W0G)` both return family `0G`; the enum representations remain distinct. Unknown representations and receipt tokens fail closed. Economic-family equivalence does not assert an independently observed price or remove execution costs.

`w0g_identity` accepts only a positive integer chain ID. On 16661 it returns the frozen Mainnet address as `EXTERNAL_PROTOCOL_REFERENCE`, sourced from existing strategy/architecture evidence, not a VERIFIED capstone record. On Galileo 16602 it returns no address and `UNRESOLVED_NOT_VERIFIED`. Other chains are unsupported by this narrow helper; existing external references on Ethereum/Base are not reclassified or substituted. Supplying any address for Galileo/unsupported chains, or a mismatched Mainnet address, raises an error. No RPC/network verification is performed.

Native 0G remains decision input, idle and common exit cash. W0G is `AUXILIARY_NOT_STRATEGY`; direct W0G input is `KIV_FUTURE`. a0G/st0G are receipt/share assets, and USDC.e is an LP execution/position asset. None becomes an alias or extra strategy. Embedded Mellow/Symbiotic exposure stays `EMBEDDED_NON_ALLOCATABLE`; Morpho/iAI stay `OBSERVED_EXCLUDED`; direct standalone Symbiotic and ETH/BTC inputs stay `KIV_FUTURE`; Bond/Zia stay auxiliary.

### Conceptual source-backed capital paths

These descriptions are derived from `data/strategies.csv` by `strategy_execution_paths()`. They explain intended architecture, not executed transactions.

| Strategy | Native-0G cash path |
|---|---|
| Native | 0G → validator delegation/shares → undelegation queue → claim → native 0G idle |
| Gimo | 0G → Gimo stake → st0G → unstake/delayed withdrawal → native 0G idle |
| Jaine | 0G → W0G → independent fixed-range W0G/USDC.e LP → liquidity removal/collection → USDC.e to W0G → unwrap → native 0G idle |
| Oku | 0G → W0G → its own fixed-range W0G/USDC.e LP → liquidity removal/collection → USDC.e to W0G → unwrap → native 0G idle |
| Ascend | 0G → W0G → SourceCore → a0G → withdrawal request/epoch funding → claim W0G → unwrap → native 0G idle |

Jaine V1 and Oku Router02 remain independent. No live pool/range or Native validator is selected. Ascend embedded backing/restaking dependency severity remains unresolved; it is not a direct LP range path and its gate remains CLOSED.

## Reproduction and boundaries

```bash
python -m pytest -q tests/test_asset_normalization.py tests/test_repository_documentation.py
python -m pytest -q tests/test_application_contract.py tests/test_result_contract.py
python -m pytest -q
cd frontend
node --test tests/*.test.ts
npm run typecheck
npm run build
```

From repository root, replay frozen artifacts with `python tools/run_final_evaluation.py --check` and `python tools/generate_final_results.py --check`. Deployment audit/preflight are read-only validation, not deployment. The dashboard remains current-request only; Iteration 24 report artifacts stay outside it.

Iteration 26 changes documentation and an isolated semantic helper/tests only. It adds no user input, does not modify schema 1.4/1.3 or optimizer/economics/risk logic, and leaves runtime/admission/economics/LP/policy/exit configuration and Iteration 23/24 outputs unchanged. No proposal edits, fresh evidence, public deployment or Iteration 27 work is included.
