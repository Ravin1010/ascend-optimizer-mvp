# Ascend Optimizer MVP

An evidence-qualified, policy-aware, amount-aware decision-sleeve optimizer for exactly five integrated MVP strategies in the 0G ecosystem. This capstone evaluates a prototype implementation and optimizer architecture, not live capital management.

## Current scope and status

`DECISION_SLEEVE`: only the explicitly supplied native-0G decision amount is optimized. Existing staking balances, LP NFTs, pending exits and other holdings remain `EXOGENOUS_NOT_OPTIMIZED`. Existing vault idle is included only when designated as this run's decision capital. Whole-portfolio compliance is `NOT_ASSESSED`; whole-portfolio state acquisition is not required for capstone completion.

Public deployment is **not required and not planned** (`NOT_REQUIRED_NOT_PLANNED`). No public capstone deployment has been established. Runtime configurations remain `UNRESOLVED`, admission evidence is headers-only, and canonical return/quote/cost evidence is empty. Production runs fail closed and currently keep **100% idle**. Runtime bindings may remain unresolved and public transaction proof is not a completion requirement.

| Independent strategy | Canonical category | Allocation gate |
|---|---|---|
| Native 0G staking (`NATIVE_STAKE_0G`) | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| Gimo st0G staking (`GIMO_STAKE_0G`) | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| Jaine 0G/USDC.e LP (`JAINE_LP_0G_USDC`) | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| Oku 0G/USDC.e LP (`OKU_LP_0G_USDC`) | INTEGRATED_ALLOCATABLE | CONDITIONAL |
| Ascend a0G staking (`ASCEND_STAKE_A0G`) | INTEGRATED_GATED | CLOSED |

All five integrations are implemented and structurally in the candidate universe. `INTEGRATED_ALLOCATABLE` means subject to runtime evidence, economics, admission, policy and current-request feasibility; it does not establish live-capital readiness. Ascend remains CLOSED even when hypothetical economics or risk diagnostics are available.

Other ecosystem roles stay outside independent allocations:

| Category | Role |
|---|---|
| EMBEDDED_NON_ALLOCATABLE | Ascend embedded Mellow/Symbiotic backing; yield counted once via a0G |
| OBSERVED_EXCLUDED | Morpho and iAI; not integrated allocation candidates |
| KIV_FUTURE | Direct standalone Symbiotic allocation, direct W0G user input, future ETH/BTC inputs |
| AUXILIARY_NOT_STRATEGY | W0G, Bond/Zia exits and execution/reference assets |

## Native 0G and W0G

Native 0G and W0G belong to one **0G economic asset family**. Native 0G is the user decision asset, vault idle asset and common cash asset after exit. W0G is an internal ERC-20 execution representation, **not a strategy**, not a sixth allocation and not an independent yield source. Direct W0G user input remains `KIV_FUTURE`; the current request accepts native 0G only. Representation equivalence is a wrapping relationship, not a universal 1:1 token-price oracle.

Intended strategy execution is 0G Mainnet (`16661`). Its frozen W0G external reference is `0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c`. Galileo (`16602`) is conditional development/test only; its W0G identity remains `UNRESOLVED / NOT_VERIFIED`. Never substitute a Mainnet/Ethereum/Base address into Galileo. Ethereum (`1`) remains an underlying dependency domain; Base (`8453`) remains KIV.

See [current state and normalization boundary](docs/current_state_iteration26.md) and [intended architecture](docs/deployment_architecture_iteration18.md). Contract topology and addresses are design/protocol references, not deployment records.

## Final optimizer and evidence modes

The primary method is `POLICY_AWARE_AMOUNT_OPTIMIZER`. It enumerates the existing discrete 0.1 weight grid, evaluates exact candidate amounts/economics, charges fixed lifecycle costs once, uses exact-amount LP quote effects and explicit technical admission, and keeps idle as a valid option. Policy constraints filter feasibility; feasible candidates rank by expected net profit. Selected economics and policy inputs are revalidated.

- **PRODUCTION**: canonical repository evidence only; unresolved required evidence fails closed. Current baseline is 100% idle for Conservative, Balanced and Aggressive.
- **SYNTHETIC_EVALUATION_ONLY**: explicitly requested modelled valuation, returns, costs, quote curves, stress and exit timing support architecture/evaluation tests. They are not current market evidence, live execution evidence, empirical forecasts or production recommendation proof.

Staking stress is deterministic. Final LP risk is **range-aware LP absolute stress loss**, with independent evaluation-only profile limits of Conservative 5%, Balanced 10% and Aggressive 20%. IL and HODL market loss remain diagnostics and are not added again to total LP loss. These limits are not empirically calibrated production risk limits, probabilities or VaR. `MODELLED_LP_STRESS_20PCT`, `lp_stress_loss_20pct` and the old IL threshold remain `LEGACY_COMPATIBILITY` only.

Holding horizon is the intended investment duration. Time-to-native-0G is the delay after an exit decision; an optional cash deadline is the maximum acceptable such delay. Synthetic durations are `MODELLED`, not guaranteed protocol withdrawal times. A synchronous LP operation does not prove quote feasibility or successful execution.

The legacy linear optimizer and collector-based CLIs remain **REFERENCE / COMPATIBILITY**, not the final primary recommendation path. Collector observations, historical snapshots and planner pools cannot establish a registered capstone route or satisfy canonical admission/economics automatically. Native sampled validator yields are benchmarks, not configured-validator return proof. Gimo net exchange-rate yield must not deduct protocol fees twice; Ascend embedded backing and LP fee/NAV growth must not be duplicated as separate reward income.

## API and dashboard

The primary interface is schema **1.4**, `/api/decision-sleeve`: decision amount, profile, holding horizon, optional cash deadline and explicit evidence mode. Responses contain exactly five strategy diagnostics plus idle, LP absolute-stress policy, modelled time-to-cash and separate readiness/proof states. Schema **1.3** and `/api/optimize` remain compatibility-only.

Protocol availability, integration, canonical category, allocation gate, evidence readiness, runtime configuration, current recommendation, execution readiness and public proof are separate dimensions. Canonical protocol `LIVE` metadata describes an external protocol only. Execution readiness and public proof remain `NOT_ESTABLISHED`, independently of any synthetic recommendation.

```bash
pip install -r requirements.txt
python -m src.ascend_optimizer.application_contract --decision-amount-0g 1000 --profile Balanced --holding-horizon-days 90
# Explicit synthetic current-request analysis:
python -m src.ascend_optimizer.application_contract --decision-amount-0g 1000 --profile Balanced --holding-horizon-days 90 --cash-deadline-days 8 --evidence-mode SYNTHETIC_EVALUATION_ONLY
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The dashboard renders the current request only; report figures/findings and benchmark statistics are not imported. [Schema 1.4 contract](docs/application_contract_iteration25.md) defines typed missing values and status separation.

## Reproducibility and implementation

The Solidity prototype includes AscendVault, StrategyManager, RewardAccounting and strategy adapters, with local/mock tests. It has no required public deployment milestone. Adapter pool/range/validator/runtime bindings remain unresolved; static and local tests are not Mainnet proof.

```bash
python -m pytest -q
python tools/deployment_preflight.py
python tools/audit_deployment_history.py --check
python tools/run_final_evaluation.py --check
python tools/generate_final_results.py --check
# Local contract tests only:
npm install
npm run contracts:compile
npm run contracts:test
```

A frozen deterministic synthetic four-method evaluation is documented in [Iteration 23](docs/final_evaluation_iteration23.md); report-ready outputs and interpretation are in [Iteration 24](docs/final_evaluation_findings_iteration24.md) and `results/`. Historical iteration documents describe their freeze points; [current state](docs/current_state_iteration26.md) is the present status. No fresh evidence is acquired by replay checks. Never commit secrets or private keys.
