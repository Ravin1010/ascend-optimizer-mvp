# Proposal reconciliation — Iteration 27

**PROPOSAL_RECONCILIATION_DRAFT** · **NOT_YET_APPLIED_TO_FINAL_PROPOSAL**

Accepted technical head: `4bbe78dc621036e9f6b692af386f458c7b9311f3`. This repository staging document is not the final proposal. Each row below is one audit unit with exactly one action; parent-section actions apply only to their opening prose, not an instruction to duplicate the child amendments.

## Reconciliation matrix

| Proposal section | Current state | Action | Reason | Frozen source |
|---|---|---|---|---|
| Front matter — project title/date | Partially stale | AMEND | The 0G–Symbiotic platform title overstates standalone restaking as the implemented product; June 2026 is original proposal metadata, not final completion evidence. | `docs/current_state_iteration26.md` |
| 1.0 Objectives | Materially stale | REPLACE | Current objectives promise 0G/BTC/ETH multi-asset, a0G routing and cross-chain allocations; implemented decision input is native 0G only. | `docs/current_state_iteration26.md` |
| 2.0–2.1.4 Current Market Landscape / EigenLayer | Still accurate as contextual literature | KEEP | Token lists, Ethereum restaking flows and historical reward-program tables are background, not claims about the implemented five-strategy universe; no fresh literature verification is asserted. | `data/metadata_contract.md` |
| 3.0 0G Restaking Architecture Using Symbiotic | Partially stale/editorial | AMEND | Opening text instructs how the chapter should be written; the chapter needs a dependency-context boundary rather than capstone implementation equivalence. | `docs/deployment_architecture_iteration18.md` |
| 3.1 Overview of the 0G Ecosystem | Partially stale scope | AMEND | Ethereum/0G discussion lacks distinction between external backing domains and capstone execution domain. | `docs/deployment_architecture_iteration18.md` |
| 3.2 Symbiotic-Based Restaking Architecture | Still accurate as background | KEEP | Component roles are contextual external architecture; retain without presenting factory/vault deployments as capstone deployment records. | `docs/deployment_architecture_iteration18.md` |
| 3.3 Current 0G Restaking Workflow | Partially stale applicability | AMEND | Factory/validator/Rewarder collateral workflow can be mistaken for a supported user allocation path. | `data/metadata_contract.md` |
| 3.4 Satellite Chain Support | Still accurate as architectural background | KEEP | Satellite-chain context need not be rewritten; it does not authorize multi-chain capstone execution or address substitution. | `docs/deployment_architecture_iteration18.md` |
| 3.5 Current Limitations | Partially stale scope | AMEND | Motivation culminates in a multi-asset cross-chain optimizer claim beyond final implemented scope. | `docs/current_state_iteration26.md` |
| 4.0 Proposed Strategy and Yield Optimizer for Ascend | Materially stale | REPLACE | Current text accepts 0G and a0G, includes lending/restaking and falls back to testnet; final path is five-strategy native-0G decision sleeve. | `docs/application_contract_iteration25.md` |
| 4.0.1 Asset and chain normalization boundary (new) | Missing required final content | ADD | No explicit native/W0G family, receipt-token distinction or Galileo address guard currently exists. | `docs/current_state_iteration26.md` |
| 4.1 MVP Strategy Universe | Materially stale | REPLACE | Four broad categories conflate independent Ascend restaking/lending and modelled Ascend availability; five independent strategy IDs and gates are frozen. | `data/metadata_contract.md` |
| 4.2 Net Return and Cost Model | Partially stale | AMEND | Horizon conversion and fee-basis distinction remain useful, but costs must apply to candidate amount rather than full-notional coefficients and points require realizable value. | `data/economics_evidence_contract.md` |
| 4.3 Risk Exposure Framework | Materially stale | REPLACE | Existing total LP risk uses IL and bridge paths; final LP measure is absolute range-position loss with independent stress budgets and unresolved dependencies. | `data/risk_exit_contract.md` |
| 4.3.1 Exit and cash-deadline model (new) | Missing required final content | ADD | Exit delay is conflated with horizon/economic exposure and lacks optional deadline qualification. | `data/evaluation_policy_contract.md` |
| 4.4 Risk Profiles and Optimization Model | Materially stale | REPLACE | Linear return coefficients, LP IL threshold, TVL-capacity and fixed exit limits are not final evaluation policy semantics. | `data/evaluation_policy_contract.md` |
| 4.4 Unnumbered profile-limit table | Materially stale | REPLACE | Old LP IL/bridge/slippage/exit defaults must not be relabelled as the final stress/deadline policy. | `data/evaluation_policy.json` |
| 4.5 Recommendation and Dashboard Output | Materially stale | REPLACE | Current LIVE status/portfolio language and required signing imply execution; final UI is current-request schema 1.4 with distinct proof/readiness. | `docs/application_contract_iteration25.md` |
| 5.0 Reference Multi-Asset Vault Design | Partially stale | AMEND | Source-level custody design is implemented but wording implies an operating deployed stack and full portfolio personalization. | `docs/deployment_architecture_iteration18.md` |
| 5.1 Core Smart Contracts | Partially stale | AMEND | Core relationships need constructor/authorization grounding and explicit implemented-versus-public-proof qualification. | `docs/deployment_architecture_iteration18.md` |
| 5.2 Deposit and Initial Allocation Flow | Partially stale | AMEND | Generic ERC20 support is conflated with current a0G user input and final signing is treated as a project milestone. | `docs/deployment_architecture_iteration18.md` |
| 5.3 Adapter Model and Execution Protection | Partially stale | AMEND | The current validator/pool/fee/range parameter wording suggests routes can be selected per instruction; actual adapter bindings are fixed constructor/config inputs. | `docs/deployment_architecture_iteration18.md` |
| 5.4 Live Ascend a0G Integration | Partially stale/misleading title | AMEND | External SourceCore implementation exists, but “Live” capstone route/caption and production wording imply registered runtime execution. | `docs/deployment_architecture_iteration18.md` |
| 5.5 Reward Accounting and Claims | Still accurate | KEEP | Separate claimable rewards, share-value exclusion and non-financial points distinction already match frozen no-double-count rules. | `data/economics_evidence_contract.md` |
| 5.6 Withdrawal Model | Partially stale | AMEND | Synchronous/asynchronous contract flow is valid but does not expose queue funding qualification or modelled native-cash timing. | `data/risk_exit_contract.md` |
| 5.7 Security Controls and MVP Boundaries | Partially stale | AMEND | Useful implementation controls coexist with production/live-route terminology and an implied future deployment requirement. | `docs/deployment_architecture_iteration18.md` |
| 6.0 Data Requirements and Evaluation Framework | Materially stale | REPLACE | One snapshot schema currently conflates evidence-qualified economics, technical admission, risk and runtime proof. | `data/economics_evidence_contract.md` |
| 6.1 Strategy Metadata | Materially stale | REPLACE | Execution status alone determines usability and seven-row universe conflates embedded/excluded records with independent strategies. | `data/metadata_contract.md` |
| 6.1 Unnumbered initial strategy-universe table | Materially stale | REPLACE | Ascend MODELLED, separate restaking and pending lending rows contradict canonical categories and five-strategy membership. | `data/strategies.csv` |
| 6.2 Strategy Snapshot Data | Materially stale | REPLACE | Snapshot scalar fields lack canonical return/quote/cost identities, exact applicability, observation/retrieval distinction and typed missing values. | `data/economics_evidence_contract.md` |
| 6.2.1 Freshness and qualification boundary (new) | Missing required final content | ADD | Proposal timestamp field lacks operational age/config/source/exact-amount checks and selected-point validity. | `data/admission_validity_policy.md` |
| 6.3 Data Sources | Partially stale | AMEND | Source list is useful but treats collector/protocol observations as automatically usable economics and Ascend only as assumptions. | `data/economics_evidence_contract.md` |
| 6.4 Evaluation Plan | Materially stale | REPLACE | Single user/profile sensitivity plan lacks accepted four-method matrix, capability fairness and conservative post-selection comparison. | `data/final_evaluation_contract.md` |
| 6.5 Deterministic synthetic results and interpretation (new) | Missing required final content | ADD | Current proposal has an evaluation plan but no frozen completed results, negative/zero deltas or causal distinction. | `docs/final_evaluation_findings_iteration24.md` |
| 6.6 Limitations (new) | Missing required final content | ADD | No consolidated final limitations cover empty production evidence, synthetic assumptions and capability comparability. | `docs/final_evaluation_findings_iteration24.md` |
| 7.0 Trade-Off Analysis | Missing prose/editorial scaffold | AMEND | Chapter consists of prompts, not a final scope/approximation trade-off synthesis. | `docs/current_state_iteration26.md` |
| 7.1 Chain Selection Trade-offs | Materially stale scaffold | REPLACE | “Ethereum + 0G + Base” treats dependency and KIV domains as execution networks. | `docs/deployment_architecture_iteration18.md` |
| 7.2 Asset Selection Trade-offs | Materially stale scaffold | REPLACE | “0G + ETH + BTC” promises current inputs absent from schema and implemented decision scope. | `docs/current_state_iteration26.md` |
| 7.3 Vault Design Trade-offs | Missing completed prose | AMEND | Single-versus-multiple-vault prompt should explain per-user shares and distinguish generic implementation from current solver input. | `docs/deployment_architecture_iteration18.md` |
| 7.4 Strategy Trade-offs | Missing completed prose | AMEND | Risk-versus-yield prompt needs typed economics/feasibility trade-off rather than a composite ranking. | `data/evaluation_policy_contract.md` |
| 7.5 Security Trade-offs | Missing completed prose | AMEND | Capital-efficiency/slashing notes need scope and common-severity/correlation qualification. | `data/risk_exit_contract.md` |
| 8.0 Differentiation of Ascend/0G | Missing final contribution; editorial | REPLACE | “Selling point” suggestions imply capabilities not delivered; contribution must describe demonstrable final architecture. | `docs/final_evaluation_findings_iteration24.md` |
| 8.1 AI-Native Blockchain Integration | Partially stale scaffold | AMEND | 0G context is valid but no implemented AI/compute optimization or unique measured benefit is established. | `docs/current_state_iteration26.md` |
| 8.2 Multi-Asset Vault | Materially stale contribution | REPLACE | “Beyond ETH-only restaking” overstates current multi-asset optimization. | `docs/deployment_architecture_iteration18.md` |
| 8.3 Intelligent Yield Routing | Partially stale scaffold | AMEND | “Dynamic strategy recommendations” can imply automatic live routing; final output is current-request advisory. | `docs/application_contract_iteration25.md` |
| 8.4 Cross-chain Yield Aggregation | Misleading/unsupported implemented contribution | REMOVE | No independent multi-chain user-capital routing exists; Ethereum is dependency-only and Base KIV. Preserve context in 3.0 and future work, not as a delivered differentiator. | `docs/current_state_iteration26.md` |
| 8.5 Risk-aware Optimization | Partially stale scaffold | AMEND | “Not simply highest APY” needs exact supported deterministic constraints and non-probabilistic qualification. | `data/evaluation_policy_contract.md` |
| 8.6 Conclusion and future work (new) | Missing required final content | ADD | Proposal lacks a bounded final conclusion and explicit deferred capabilities. | `docs/final_evaluation_findings_iteration24.md` |
| Trailing unnumbered income/high-budget prompt | Editorial/misleading | REMOVE | The request to generate income is unsupported by synthetic evaluation and unsuitable as a capstone conclusion. | `docs/final_evaluation_findings_iteration24.md` |
| Figure 3.1 — High-Level 0G–Symbiotic Architecture | Still accurate as background | KEEP | External dependency overview remains contextual; it must not be counted as a performed capstone deployment. | `docs/deployment_architecture_iteration18.md` |
| Figure 3.2 — Main Chain–Satellite Chain Architecture | Still accurate as background | KEEP | Satellite illustration is background rather than implemented optimizer routing; no new figure is required. | `docs/deployment_architecture_iteration18.md` |
| Figure 4.1 — Optimizer workflow | Partially stale caption | AMEND | Current caption terminates in approval before execution, not evidence/policy revalidation and deployment-independent output. | `docs/application_contract_iteration25.md` |
| Figure 5.1 — Off-chain/on-chain architecture | Partially stale caption | AMEND | Caption calls AscendProtocolAdapter live and implies registered capstone instances. | `docs/deployment_architecture_iteration18.md` |
| Figure 5.2 — Deposit and initial allocation | Partially stale caption | AMEND | Caption needs hypothetical source/local qualifier rather than proof of an operational allocation flow. | `docs/deployment_architecture_iteration18.md` |
| Figure 5.3 — Live Ascend deposit/withdrawal | Misleading title/caption | AMEND | External protocol path is confused with public capstone runtime execution. | `docs/deployment_architecture_iteration18.md` |
| Figure 5.4 — Reward accounting | Still accurate | KEEP | Caption already excludes rewards embedded in shares/NAV and preserves separate claimable accounting. | `data/economics_evidence_contract.md` |
| Figure 5.5 — Withdrawal state flow | Partially stale caption | AMEND | Two-stage flow is useful but lacks distinction from modelled cash timing and successful quote execution. | `data/risk_exit_contract.md` |
| Figure 6.1 — Data/evaluation pipeline | Partially stale/unqualified caption | AMEND | “Data and evaluation pipeline” lacks canonical-evidence versus synthetic-scenario boundary. | `data/final_evaluation_contract.md` |
| Table 5.1 — Withdrawal types | Partially stale | AMEND | LP immediate redemption cannot be interpreted as execution guarantee; queue-based Ascend needs separate stages. | `data/risk_exit_contract.md` |
| Table 6.1 — Static strategy metadata schema | Materially stale | REPLACE | Execution/technical eligibility columns alone collapse canonical category, gate, runtime and proof. | `data/metadata_contract.md` |
| Table 6.2 — Dynamic snapshot schema | Materially stale | REPLACE | Single snapshot table conflates return metrics, exact quotes, costs, risk and liquidity evidence. | `data/economics_evidence_contract.md` |
| Table 6.3 — Primary sources and usage | Partially stale | AMEND | Sources lack role qualification and may imply current verified records for Ascend or LP execution. | `data/economics_evidence_contract.md` |
| Table 6.4 — Sensitivity variables | Materially stale | REPLACE | Proposed one-factor risks/bridge knobs are not the actual accepted matrix or isolated causal tests. | `data/final_evaluation_contract.md` |

## Proposal source and audit boundaries

The read-only source is [Proposal Initial Draft](https://docs.google.com/document/d/1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4/edit), modified 2026-10-04T09:15:19.407Z. It is the current document, not a September formatting backup. The Google Docs revision read was `AHj4eMSUMTDvQ-XJl1JbQgJyCTqJXON5T8LS2KLQAV1Gc98SWoNxnOThmbMwW-lRSfqIzaAIevCjpXIlwSOsvAkYMBnccApVIlXl_J07SQU`. The normalized readable-text snapshot (UTF-8, LF line endings) SHA-256 is `9ea3332823ce100f8f75892053f80a8b649f12e533f2768a3a94fe8abd7140bb`. The snapshot is temporary audit material, not a committed replacement proposal. Native structure inspection found 15 inline-image occurrences and 19 tables. Named project captions and tables are audited above; the unnumbered literature tables and screenshots remain contextual background.

This is a text/caption and native-structure audit, not a rendered-page/layout assessment. Existing diagram artwork is not redrawn or certified for final placement; any labels inside it that conflict with the proposed caption must be checked during later human section review. Background market/protocol claims are retained in historical/contextual scope, not newly verified as current market facts. Named tables and figures retain their identifiers here; new 4.0.1/4.3.1/6.2.1/6.5/6.6/8.6 numbering is provisional and must be resolved with the final document's styles and table of contents after approval.

Technical authority is the frozen repository state, with current scope/asset/status in `docs/current_state_iteration26.md`, source-grounded architecture in `docs/deployment_architecture_iteration18.md`, evidence contracts, policy/risk/exit artifacts and schema 1.4 contract. Completed result interpretation is limited to `docs/final_evaluation_findings_iteration24.md` and the frozen manifest/artifacts. Proposal assumptions do not override these sources. No new technical or observational claim is introduced.

Audit totals: **63 units**; KEEP = 7; AMEND = 29; REPLACE = 19; ADD = 6; REMOVE = 2. Units include existing prose sections, new proposed subsections, individually audited captions/tables and two editorial removals.

### Review/application workflow

1. Review one matrix unit and its proposed text against the cited frozen basis.
2. Approve, revise or decline it explicitly; the draft has no implicit insertion authority.
3. Apply only approved changes to the real proposal in a later task, preserving original context, formatting, numbering and citations.
4. Review chosen existing figures/tables and in-image labels before placement. No new figure/statistic is produced here.

Actions KEEP preserve the existing passage within its stated background/source scope. REMOVE actions below eliminate unsupported/editorial content rather than silently rewriting it. All other actions have staged proposal-ready text. Formatting/table instructions are visibly distinguished from prose. The capstone contribution is stated as a prototype/evaluation result, not a funding or income promise.

## Staged proposal amendments

### P01 — Proposal Section Front matter — project title/date

**Action:** AMEND

**Reason:** The 0G–Symbiotic platform title overstates standalone restaking as the implemented product; June 2026 is original proposal metadata, not final completion evidence.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Suggested title: “Evidence-Qualified Strategy and Yield Optimization for Ascend in the 0G Ecosystem”. The work comprises an off-chain decision-sleeve optimizer, a reference vault/adapter implementation and a current-request dashboard. The original June 2026 proposal date should remain identifiable as proposal provenance; a later amendment date should be entered only when the revised document is actually approved.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P02 — Proposal Section 1.0 Objectives

**Action:** REPLACE

**Reason:** Current objectives promise 0G/BTC/ETH multi-asset, a0G routing and cross-chain allocations; implemented decision input is native 0G only.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The project develops an evidence-qualified, policy-aware, amount-aware optimizer for allocating a designated native-0G decision amount across five integrated strategies: Native staking, Gimo st0G staking, Jaine LP, Oku LP and Ascend a0G staking. The scope is DECISION_SLEEVE: existing staking balances, LP positions, pending exits and other holdings are EXOGENOUS_NOT_OPTIMIZED, and whole-portfolio compliance is NOT_ASSESSED. A reference vault/adapter stack and dashboard demonstrate architectural separation between recommendation, intended execution controls and evidence qualification. Evaluation is deployment-independent; public deployment is neither required nor planned. Multi-asset inputs and standalone cross-chain allocation remain future extensions.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P04 — Proposal Section 3.0 0G Restaking Architecture Using Symbiotic

**Action:** AMEND

**Reason:** Opening text instructs how the chapter should be written; the chapter needs a dependency-context boundary rather than capstone implementation equivalence.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> This chapter describes the external 0G–Symbiotic architectural context. It provides background for understanding underlying protocol and security dependencies; it does not define an independently allocatable capstone restaking route. The implemented optimizer treats embedded Ascend/Mellow/Symbiotic exposure beneath a0G once, within the Ascend strategy. Direct standalone Symbiotic allocation remains future work.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P05 — Proposal Section 3.1 Overview of the 0G Ecosystem

**Action:** AMEND

**Reason:** Ethereum/0G discussion lacks distinction between external backing domains and capstone execution domain.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The intended strategy-execution domain of the prototype is 0G Mainnet (chain ID 16661). Ethereum is an underlying protocol/security dependency where applicable, rather than a separate optimizer routing domain. Galileo (16602) is conditional development/test only and Base is deferred. These chain roles describe intended architecture and external dependencies; they do not establish a public capstone deployment.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P07 — Proposal Section 3.3 Current 0G Restaking Workflow

**Action:** AMEND

**Reason:** Factory/validator/Rewarder collateral workflow can be mistaken for a supported user allocation path.

**Frozen basis:** `data/metadata_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The validator registration, collateral synchronization and Rewarder workflow below is retained as an external restaking reference. The capstone does not create validators, submit collateral transactions to this stack or expose its Rewarder as an additional independent optimizer strategy. Embedded backing is analyzed through the Ascend/a0G dependency boundary; no operator-level state or correlation is inferred.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P09 — Proposal Section 3.5 Current Limitations

**Action:** AMEND

**Reason:** Motivation culminates in a multi-asset cross-chain optimizer claim beyond final implemented scope.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Fragmented economic evidence, heterogeneous costs and different exit mechanisms motivate a common decision model. The implemented response is a native-0G decision-sleeve optimizer that separates expected economics, technical admission, deterministic stress and liquidity timing. It does not resolve whole-portfolio acquisition or implement general cross-chain capital routing. Missing evidence remains an explicit limitation rather than a substituted estimate.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P10 — Proposal Section 4.0 Proposed Strategy and Yield Optimizer for Ascend

**Action:** REPLACE

**Reason:** Current text accepts 0G and a0G, includes lending/restaking and falls back to testnet; final path is five-strategy native-0G decision sleeve.

**Frozen basis:** `docs/application_contract_iteration25.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The optimizer is an off-chain advisory decision engine for the explicitly designated native-0G capital in the current request. Its primary method is POLICY_AWARE_AMOUNT_OPTIMIZER. It evaluates candidate allocations within a fixed five-strategy universe and leaves unallocated capital idle. Existing positions remain outside the optimized state, and no whole-portfolio compliance claim is made. Mainnet intent does not imply deployment: canonical runtime bindings remain unresolved, execution readiness and public proof remain NOT_ESTABLISHED, and public deployment is not required or planned.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P11 — Proposal Section 4.0.1 Asset and chain normalization boundary (new)

**Action:** ADD

**Reason:** No explicit native/W0G family, receipt-token distinction or Galileo address guard currently exists.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Native 0G and W0G are representations of one 0G economic asset family. Native 0G is the current user input, vault idle asset and common exit cash asset; W0G is an internal wrapped ERC-20 representation for protocol execution, not an independent yield source or sixth strategy. Direct W0G input remains KIV_FUTURE. a0G and st0G are receipt/share tokens, while USDC.e is an LP execution/position asset. ETH/BTC inputs are deferred. The frozen Mainnet W0G reference is chain-bound to 16661; Galileo W0G remains UNRESOLVED / NOT_VERIFIED, and references from other chains cannot be substituted. Representation equivalence is a wrapping relationship, not a universal price-oracle assertion.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P12 — Proposal Section 4.1 MVP Strategy Universe

**Action:** REPLACE

**Reason:** Four broad categories conflate independent Ascend restaking/lending and modelled Ascend availability; five independent strategy IDs and gates are frozen.

**Frozen basis:** `data/metadata_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The five independent integrated strategies are NATIVE_STAKE_0G, GIMO_STAKE_0G, JAINE_LP_0G_USDC, OKU_LP_0G_USDC and ASCEND_STAKE_A0G. The first four have canonical category INTEGRATED_ALLOCATABLE and allocation gate CONDITIONAL. Ascend has category INTEGRATED_GATED and gate CLOSED. All five are structurally in the candidate universe with implemented integration. Allocatable denotes conditional candidate membership, not capital-execution readiness. Ascend embedded Mellow/Symbiotic backing is EMBEDDED_NON_ALLOCATABLE; Morpho and iAI are OBSERVED_EXCLUDED. Direct standalone Symbiotic and alternate inputs are KIV_FUTURE. W0G, Bond/Zia exits and execution/reference assets are AUXILIARY_NOT_STRATEGY. Protocol availability, integration, category, gate, evidence readiness, runtime configuration and public proof remain separate dimensions.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P13 — Proposal Section 4.2 Net Return and Cost Model

**Action:** AMEND

**Reason:** Horizon conversion and fee-basis distinction remain useful, but costs must apply to candidate amount rather than full-notional coefficients and points require realizable value.

**Frozen basis:** `data/economics_evidence_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> For candidate amount A_i and holding horizon H, expected net profit equals qualified strategy return/income, including only supported economically realizable incentives, less candidate-specific execution and lifecycle costs. Annual return evidence is converted deterministically over H with its fee basis and provenance preserved. Fixed lifecycle costs are charged once when the strategy receives a positive allocation; variable costs scale with amount and LP entry/exit quote effects require exact amount and context alignment. Costs expressed in native units preserve the valuation source used for conversion to USD. Missing return, cost or required quote evidence does not become zero. Gimo exchange-rate returns already net of protocol fees do not incur a second fee deduction. Ascend embedded backing yield is counted once; LP fee/NAV growth is not duplicated as separately claimable rewards. Non-financial points do not contribute to financial APY. Net return and annualized net return are reported only when their valuation and mathematical domains are meaningful.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P14 — Proposal Section 4.3 Risk Exposure Framework

**Action:** REPLACE

**Reason:** Existing total LP risk uses IL and bridge paths; final LP measure is absolute range-position loss with independent stress budgets and unresolved dependencies.

**Frozen basis:** `data/risk_exit_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Risk is expressed through named deterministic scenarios rather than probabilities, VaR or a composite score. Native uses a modelled 5% severe staking-loss benchmark. Gimo applies underlying staking loss once; using the same severity does not imply a shared event or calibrated correlation. Independent synthetic Jaine and Oku configurations use concentrated-liquidity inventory mathematics under the versioned −20%, −10%, +10% and +20% economic 0G price shocks. The LP budget uses the worst absolute position loss across that set. Impermanent loss, defined as V_LP/V_HODL − 1, and initial-inventory HODL market loss remain attribution diagnostics and are not added again to total LP loss. Quote/slippage costs and expected fee income are excluded from mathematical position stress. Ascend analysis includes an illustrative economic haircut, while embedded backing/restaking dependency severity remains unresolved; analysis does not open its gate. Remote dependencies do not automatically establish user-capital bridge exposure. The summed independent stress-budget envelope is not a correlated joint-event estimate.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P15 — Proposal Section 4.3.1 Exit and cash-deadline model (new)

**Action:** ADD

**Reason:** Exit delay is conflated with horizon/economic exposure and lacks optional deadline qualification.

**Frozen basis:** `data/evaluation_policy_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Holding horizon measures the intended investment period. Time-to-native-0G measures the delay after an exit decision, and an optional cash deadline defines the maximum acceptable such delay. Native and Gimo have asynchronous request/wait/claim paths; Jaine and Oku have synchronously unwindable protocol-operation paths, without guaranteeing execution quotes. Ascend has separate request, epoch/queue maturity, funding and claim stages. Canonical timing may remain unresolved; synthetic durations are modelled rather than guaranteed protocol withdrawal times. Deadline states are NOT_REQUESTED, COMPATIBLE_MODELLED, INCOMPATIBLE_MODELLED or UNRESOLVED. With a requested deadline, a positive allocation exceeding it or lacking qualified timing fails feasibility. Zero-weight unresolved routes do not block the sleeve, and idle is immediately available native 0G.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P16 — Proposal Section 4.4 Risk Profiles and Optimization Model

**Action:** REPLACE

**Reason:** Linear return coefficients, LP IL threshold, TVL-capacity and fixed exit limits are not final evaluation policy semantics.

**Frozen basis:** `data/evaluation_policy_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The optimizer enumerates the frozen discrete 0.1 allocation-weight grid using exact candidate amount identities, including an explicit idle option. Candidate technical admission and economics are evaluated before typed policy feasibility. Concentration, weighted underlying-staking stress, range-aware LP absolute stress, optional cash deadline, closed gates and unresolved required inputs constrain feasibility; they are not profit penalties. Feasible candidates rank by expected net profit without changing the objective for risk or deadlines. Selected-point economics and policy/configuration identities are revalidated, with changes failing closed. Conservative, Balanced and Aggressive concentration limits remain 40%, 60% and 80%; staking budgets remain 2%, 5% and 10%. The distinct decision-sleeve LP absolute-stress limits are 5%, 10% and 20%, explicitly synthetic evaluation policy choices. The old IL-named threshold and generic LP proxy retain legacy compatibility meaning and are not reinterpreted. Pool TVL alone is not executable capacity. A fully idle allocation is a valid decision.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P17 — Proposal Section 4.4 Unnumbered profile-limit table

**Action:** REPLACE

**Reason:** Old LP IL/bridge/slippage/exit defaults must not be relabelled as the final stress/deadline policy.

**Frozen basis:** `data/evaluation_policy.json` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The final feasibility limits are evaluation-policy choices; they are not calibrated production risk limits. The cash deadline is optional and supplied per request, without a profile default. Legacy bridge, slippage, IL and exit-delay limits retain their compatibility meaning in the reference optimizer rather than being silently relabelled.
>
> | Final decision-sleeve constraint | Conservative | Balanced | Aggressive |
> |---|---|---|---|
> | Maximum strategy concentration | 40% | 60% | 80% |
> | Maximum weighted staking stress | 2% | 5% | 10% |
> | Maximum LP absolute stress | 5% | 10% | 20% |
> | Cash deadline | Optional request input | Optional request input | Optional request input |
>
> Table: Synthetic evaluation feasibility limits (SYNTHETIC_EVALUATION_ONLY).

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P18 — Proposal Section 4.5 Recommendation and Dashboard Output

**Action:** REPLACE

**Reason:** Current LIVE status/portfolio language and required signing imply execution; final UI is current-request schema 1.4 with distinct proof/readiness.

**Frozen basis:** `docs/application_contract_iteration25.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The application serves schema 1.4 through /api/decision-sleeve. Inputs are decision amount, profile, holding horizon, optional cash deadline and explicit evidence mode. The primary response includes all five strategy diagnostics and idle, exact allocations, assessed economics, policy constraints, risk, liquidity and rejection/binding reasons. Missing or unsupported values are typed nonnumeric states rather than zero. Recommendation, feasibility, runtime configuration, execution readiness and public proof are distinct. Existing positions are EXOGENOUS_NOT_OPTIMIZED and whole-portfolio compliance is NOT_ASSESSED. Production uses canonical evidence and currently returns 100% idle; synthetic current-request analysis is prominently labelled SYNTHETIC_EVALUATION_ONLY. Schema 1.3 and legacy comparison remain compatibility/reference interfaces. The dashboard renders the current request rather than the historical benchmark and does not submit transactions.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P19 — Proposal Section 5.0 Reference Multi-Asset Vault Design

**Action:** AMEND

**Reason:** Source-level custody design is implemented but wording implies an operating deployed stack and full portfolio personalization.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The contract stack is a reference implementation of custody, registration, allocation protection and reward accounting. The off-chain optimizer has no privileged execution role or private key. Source-level user-authorized execution through registered adapters describes the intended architecture; it is not a performed capstone transaction. Generic ERC-20 vault support does not expand the current native-0G optimizer input. Static validation and local/mock simulation establish prototype design behavior, while runtime bindings remain unresolved and public deployment is not required or planned.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P20 — Proposal Section 5.1 Core Smart Contracts

**Action:** AMEND

**Reason:** Core relationships need constructor/authorization grounding and explicit implemented-versus-public-proof qualification.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> StrategyManager provides the approved strategy-to-adapter registry and hard caps. AscendVault holds an immutable manager reference, records user idle and strategy shares and checks registered route, deadline, minimum shares and caps for allocations. RewardAccounting references the vault and manager; when used, it is attached before allocations begin and checkpoints independently claimable rewards around share changes. Adapters are authorized by immutable vault references. Manager, vault, accounting and Native adapter ownership are constructor roles, not selected production admin addresses. A0GToken and AscendStakingAdapter remain reference/pre-launch artifacts, not the external a0G asset. Local tests demonstrate these relationships without establishing deployed instances.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P21 — Proposal Section 5.2 Deposit and Initial Allocation Flow

**Action:** AMEND

**Reason:** Generic ERC20 support is conflated with current a0G user input and final signing is treated as a project milestone.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> In the intended contract flow, a deposit enters the user's idle balance and does not trigger allocation. A hypothetical user-authorized allocation is validated by the vault and routed through a registered adapter; returned shares are recorded per user. This source-level flow is evaluated locally and documented as intended architecture only. The optimizer accepts native 0G decision capital, including explicitly designated vault idle; generic approved ERC-20 deposit support is distinct from current optimizer inputs. No public transaction submission is required for project completion and existing positions are not automatically rebalanced.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P22 — Proposal Section 5.3 Adapter Model and Execution Protection

**Action:** AMEND

**Reason:** The current validator/pool/fee/range parameter wording suggests routes can be selected per instruction; actual adapter bindings are fixed constructor/config inputs.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Protocol-specific adapters isolate bounded deposit, withdrawal and claim behavior. The Native adapter binds one validator; Jaine and Oku bind independent pool/fee/range/target configurations, with Jaine V1 and Oku Router02 semantics. Ascend binds W0G, SourceCore and its queue relationship. These are source-fixed or unresolved deployment-time relationships, not arbitrarily selected optimizer instructions. Registered adapter/input-asset/exit-mode checks, minShares, minAmountOut, deadlines and hard caps protect intended execution. Exact-amount evidence and selected-point revalidation remain off-chain qualifications and do not establish public execution proof.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P23 — Proposal Section 5.4 Live Ascend a0G Integration

**Action:** AMEND

**Reason:** External SourceCore implementation exists, but “Live” capstone route/caption and production wording imply registered runtime execution.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> AscendProtocolAdapter represents the source-level native-0G → W0G → SourceCore/a0G share path and asynchronous request/epoch/funding/claim path returning W0G for unwrapping to native 0G. External protocol share accounting determines shares rather than a capstone 1:1 minting rule. External references are not capstone deployment records; adapter/runtime registration remains unresolved and the canonical Ascend allocation gate remains CLOSED. Embedded Mellow/Symbiotic backing is not a separately allocatable route or second return stream.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P25 — Proposal Section 5.6 Withdrawal Model

**Action:** AMEND

**Reason:** Synchronous/asynchronous contract flow is valid but does not expose queue funding qualification or modelled native-cash timing.

**Frozen basis:** `data/risk_exit_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Withdrawals distinguish synchronous protocol operations from asynchronous request/wait/claim and queue-based maturity/funding/claim stages. All five canonical paths aim to return native 0G cash, directly or after W0G unwrapping. A synchronous LP unwind is not a guarantee of quote feasibility or successful execution. Canonical durations remain unresolved; evaluation durations are modelled. Investment horizon, time-to-cash after exit and optional cash deadline must remain separate. Pending exits from earlier allocations are outside the current decision sleeve.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P26 — Proposal Section 5.7 Security Controls and MVP Boundaries

**Action:** AMEND

**Reason:** Useful implementation controls coexist with production/live-route terminology and an implied future deployment requirement.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The prototype implements registry authorization, bounded adapter calls, minimum-output protection, deadlines, hard caps, reentrancy protection and pause semantics. These controls are supported by source validation and local/mock tests, not public deployment or comprehensive production security assurance. New deposits/allocations may be paused while supported withdrawals and reward claims remain available. No optimizer custody authority or transaction-signing role is introduced. Public deployment is not required or planned; unresolved configuration, empty admission/economics evidence and closed Ascend allocation remain legitimate prototype boundaries. A generic restaking connector is a future extension point, not a sixth implemented allocation strategy.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P27 — Proposal Section 6.0 Data Requirements and Evaluation Framework

**Action:** REPLACE

**Reason:** One snapshot schema currently conflates evidence-qualified economics, technical admission, risk and runtime proof.

**Frozen basis:** `data/economics_evidence_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The system distinguishes canonical metadata, runtime configuration, technical admission, economic evidence, deterministic risk and exit timing. Each dimension has a separate qualification state and provenance. Production uses canonical evidence and fails closed; the current runtime configurations are unresolved and admission/economics datasets are empty, so every profile remains fully idle. Explicit synthetic evaluation supplies labelled modelled assumptions without writing them into canonical records or promoting runtime identity. Evidence quality does not establish technical admission, quote validity, risk clearance or public deployment proof.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P28 — Proposal Section 6.1 Strategy Metadata

**Action:** REPLACE

**Reason:** Execution status alone determines usability and seven-row universe conflates embedded/excluded records with independent strategies.

**Frozen basis:** `data/metadata_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The metadata separates strategy identity, structural optimizer membership, reconciliation category, protocol availability, integration status, allocation gate, evidence readiness, runtime feasibility and public proof. Exactly five independent rows belong to the optimizer universe; other ecosystem records retain explanatory categories without becoming allocations. Schema 1.4 derives category, structural candidacy, integration, gate and protocol availability from authoritative StrategyState metadata. INTEGRATED_ALLOCATABLE and CONDITIONAL are independent fields, and external protocol LIVE metadata is not a capstone execution claim.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P29 — Proposal Section 6.1 Unnumbered initial strategy-universe table

**Action:** REPLACE

**Reason:** Ascend MODELLED, separate restaking and pending lending rows contradict canonical categories and five-strategy membership.

**Frozen basis:** `data/strategies.csv` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The independent optimizer universe comprises the five rows below. All five integrations are implemented and structurally included; actual allocations remain conditional on evidence and feasibility. Other ecosystem records have explanatory roles outside independent allocation.
>
> | Strategy | Canonical category | Allocation gate |
> |---|---|---|
> | NATIVE_STAKE_0G | INTEGRATED_ALLOCATABLE | CONDITIONAL |
> | GIMO_STAKE_0G | INTEGRATED_ALLOCATABLE | CONDITIONAL |
> | JAINE_LP_0G_USDC | INTEGRATED_ALLOCATABLE | CONDITIONAL |
> | OKU_LP_0G_USDC | INTEGRATED_ALLOCATABLE | CONDITIONAL |
> | ASCEND_STAKE_A0G | INTEGRATED_GATED | CLOSED |
>
> Embedded Ascend/Mellow/Symbiotic backing is EMBEDDED_NON_ALLOCATABLE; Morpho/iAI are OBSERVED_EXCLUDED; standalone Symbiotic and alternate inputs are KIV_FUTURE; W0G/Bond/Zia are auxiliary. Protocol availability is distinct from capstone execution proof.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P30 — Proposal Section 6.2 Strategy Snapshot Data

**Action:** REPLACE

**Reason:** Snapshot scalar fields lack canonical return/quote/cost identities, exact applicability, observation/retrieval distinction and typed missing values.

**Frozen basis:** `data/economics_evidence_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Canonical economic records preserve evidence identity, source/role, observation and retrieval timestamps, optional measurement period/block provenance, chain and exact amount/configuration context. Return metrics remain distinct from LP execution quotes and lifecycle costs. Evidence classes preserve LIVE_OBSERVED, LIVE_DERIVED, HISTORICAL, MODELLED, STATIC_CONFIG and MISSING, while unresolved bindings retain their own state. Historical collector observations and modelled fixtures do not become current observations. Native validator benchmarks do not establish configured-validator returns; Gimo/Ascend exchange-rate histories derive annualized returns only when sufficient qualified observations exist. Missing economics, risk or capacity are never replaced with zero or unlimited headroom.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P31 — Proposal Section 6.2.1 Freshness and qualification boundary (new)

**Action:** ADD

**Reason:** Proposal timestamp field lacks operational age/config/source/exact-amount checks and selected-point validity.

**Frozen basis:** `data/admission_validity_policy.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Observation time and retrieval time have distinct meanings; absent times or blocks are not synthesized. Evidence validity includes age, source qualification, exact amount and configuration context, with typed outcomes such as VALID, STALE, CONFIG_MISMATCH, AMOUNT_MISMATCH, SOURCE_UNVERIFIED, MISSING/UNRESOLVED and POLICY_UNDEFINED. Technical admission validity does not imply LP quote validity or executable capacity. The admission operational TTL is not a universal return/quote freshness policy. Where return/cost or quote policies lack a defensible numeric freshness rule, current claims fail closed as NO_VALID_POLICY or POLICY_UNDEFINED. Explicit historical/modelled evaluation uses its declared scenario boundary rather than pretending current market freshness. Selected identities and contexts are revalidated before a recommendation is retained.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P32 — Proposal Section 6.3 Data Sources

**Action:** AMEND

**Reason:** Source list is useful but treats collector/protocol observations as automatically usable economics and Ascend only as assumptions.

**Frozen basis:** `data/economics_evidence_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Explorer/RPC, protocol contracts/documentation, pool data and incentive sources remain acquisition references. Their implementation or availability does not by itself qualify a current record, registered route or executable quote. Native sample yield is a benchmark rather than a configured validator; external Gimo and SourceCore exchange rates require qualified history and fee semantics. Historical LP liquidity/volume observations are not current range-bound return or quote evidence. Protocol references and synthetic assumptions retain their original classes, and canonical economic datasets remain empty pending a separately qualified evidence package. No fresh acquisition is part of this evaluation.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P33 — Proposal Section 6.4 Evaluation Plan

**Action:** REPLACE

**Reason:** Single user/profile sensitivity plan lacks accepted four-method matrix, capability fairness and conservative post-selection comparison.

**Frozen basis:** `data/final_evaluation_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> A versioned deterministic synthetic evaluation compares HIGHEST_YIELD_BASELINE, EQUAL_WEIGHT_ELIGIBLE_BASELINE, LEGACY_LINEAR_OPTIMIZER and POLICY_AWARE_AMOUNT_OPTIMIZER. The matrix comprises 27 core scenarios (three profiles × 100/1,000/10,000 0G × 30/90/365 days, with no cash deadline) and 22 targeted scenarios for deadlines and evidence/economic failure modes, yielding 49 scenarios and 196 method/scenario rows. Shared assumptions are identical where supported; unsupported features are explicitly reported. Highest yield ranks qualified positive annual returns up to concentration caps; equal weight uses eligible equal targets without optimizing profit. The actual legacy solver uses reference-notional linearization and compatibility risk/exit limits. The actual final solver uses exact candidate economics and policy feasibility. All inputs and results are SYNTHETIC_EVALUATION_ONLY, and Ascend remains zero for every recommendation method. Fixed-cost and quote-curve control pairs support within-model causal sensitivity; ordinary contributor annotations are diagnostic associations. Common exact-allocation post-selection rescoring enables qualified comparisons without changing method capabilities or selection objectives.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P34 — Proposal Section 6.5 Deterministic synthetic results and interpretation (new)

**Action:** ADD

**Reason:** Current proposal has an evaluation plan but no frozen completed results, negative/zero deltas or causal distinction.

**Frozen basis:** `docs/final_evaluation_findings_iteration24.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The policy-aware amount-aware optimizer selects a different allocation from the legacy linear optimizer in 27 of the 49 defined deterministic synthetic scenarios; 39 scenarios exhibit disagreement among any methods. These counts describe the defined matrix, not real-world disagreement probabilities. Under a common exact-allocation post-selection rescore, amount-aware-minus-legacy deltas are positive in 19 cases, negative in 7 and zero in 23, with a mean of +$43.40 and median $0. The common rescore is not the legacy selection objective and does not establish universal profit superiority. Controlled FIXED_100 versus FIXED_ZERO_CONTROL and QUOTE_CURVE versus QUOTE_CONSTANT_CONTROL demonstrate within-model sensitivity to charging fixed cost once and exact-amount quote assumptions. Under common LP economics, Jaine allocations of 30%, 60% and 80% across the three profiles reflect concentration, LP absolute-stress policy and the grid jointly. Modelled deadlines of 1, 8 and 15 days progressively exclude or permit asynchronous staking; they are not protocol liquidity guarantees. Negative or unresolved required economics and admission can rationally produce full idle allocation. Ordinary stress/concentration/deadline/grid contributor labels remain associated diagnostics rather than isolated causal effects.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P35 — Proposal Section 6.6 Limitations (new)

**Action:** ADD

**Reason:** No consolidated final limitations cover empty production evidence, synthetic assumptions and capability comparability.

**Frozen basis:** `docs/final_evaluation_findings_iteration24.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The evaluation uses synthetic economic inputs, modelled 0G valuation, analytical quote curves, deterministic stress assumptions and modelled exit durations. Canonical runtime configurations remain unresolved; production admission and economics are empty, and no public deployment or execution-ready proof is established. Ascend remains CLOSED. The optimizer assesses only the new decision sleeve, not existing positions or whole-portfolio compliance. The 0.1 grid restricts attainable weights, and the LP configurations are synthetic rather than optimal or registered positions. The defined matrix is not statistically representative and estimates neither event probabilities nor VaR. Independent stress budgets do not imply correlated joint events. Method capability and internal-objective differences limit comparison; common post-selection rescoring cannot establish empirical performance superiority or forecasts. Synthetic evaluation establishes no observational return/quote freshness policy or guaranteed withdrawal timing.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P36 — Proposal Section 7.0 Trade-Off Analysis

**Action:** AMEND

**Reason:** Chapter consists of prompts, not a final scope/approximation trade-off synthesis.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The implemented scope prioritizes reproducible, interpretable candidate decisions over broad multi-asset or multi-chain coverage. Explicit evidence qualification and idle abstention reduce unsupported recommendations; exact-amount economics capture fixed and amount-dependent effects at the cost of a discrete search space. Deterministic stress and modelled timing provide transparent evaluation constraints without claiming empirical calibration. General whole-portfolio rebalancing and public execution remain outside the capstone completion scope.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P37 — Proposal Section 7.1 Chain Selection Trade-offs

**Action:** REPLACE

**Reason:** “Ethereum + 0G + Base” treats dependency and KIV domains as execution networks.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> 0G Mainnet is the intended execution domain. Ethereum is retained as an external backing/security dependency where applicable; it is not an independent allocation network. Galileo supports conditional development/test, with W0G identity unresolved, and Base remains deferred. This separation prevents cross-network address substitution and avoids equating intended architecture with deployment proof.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P38 — Proposal Section 7.2 Asset Selection Trade-offs

**Action:** REPLACE

**Reason:** “0G + ETH + BTC” promises current inputs absent from schema and implemented decision scope.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Native 0G is the sole current decision input. Internal W0G wrapping provides ERC-20 protocol compatibility without creating another economic allocation. st0G/a0G represent positions rather than input aliases, and USDC.e is an LP asset. Direct W0G, ETH and BTC input normalization remains future work; the prototype demonstrates the allocation architecture without requiring general multi-asset normalization.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P39 — Proposal Section 7.3 Vault Design Trade-offs

**Action:** AMEND

**Reason:** Single-versus-multiple-vault prompt should explain per-user shares and distinguish generic implementation from current solver input.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The reference vault separates personalized user share accounting from pooled adapter positions and an owner-controlled registry. This avoids treating three risk profiles as three mandatory pooled products. Generic approved-asset support remains distinct from the native-0G decision optimizer. Hard contract caps constrain intended execution independently of evaluation policy; source/local validation does not establish deployed balances or operational headroom.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P40 — Proposal Section 7.4 Strategy Trade-offs

**Action:** AMEND

**Reason:** Risk-versus-yield prompt needs typed economics/feasibility trade-off rather than a composite ranking.

**Frozen basis:** `data/evaluation_policy_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Expected net profit ranks only feasible candidates. Staking stress, LP absolute stress, concentration, optional deadline and allocation gates separately constrain the decision. A strategy with higher modelled return may therefore receive a lower allocation or none. Jaine and Oku remain independent ranges/routes, while Ascend completeness cannot override its CLOSED gate. Idle is an intentional alternative.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P41 — Proposal Section 7.5 Security Trade-offs

**Action:** AMEND

**Reason:** Capital-efficiency/slashing notes need scope and common-severity/correlation qualification.

**Frozen basis:** `data/risk_exit_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Explicit source/amount/configuration qualification and bounded contract interfaces prioritize traceability over unqualified route availability. The deterministic 5% staking benchmark expresses severe-loss sensitivity, not a probability or protocol-specific observed slash rate. Equal Native/Gimo severity does not establish a shared event; embedded Ascend dependency severities remain unresolved. Neither local tests nor modelled risk budgets constitute production security assurance.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P42 — Proposal Section 8.0 Differentiation of Ascend/0G

**Action:** REPLACE

**Reason:** “Selling point” suggestions imply capabilities not delivered; contribution must describe demonstrable final architecture.

**Frozen basis:** `docs/final_evaluation_findings_iteration24.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The capstone contributes an evidence-qualified, amount-aware decision-sleeve optimizer that separates expected economics, technical admission, deterministic risk, liquidity timing and execution proof. Controlled synthetic evaluation demonstrates where exact candidate costs and quotes alter selected allocations relative to simpler approaches, while typed feasibility and abstention expose the limitations of available evidence. This is an architectural and within-model evaluation contribution, not empirical superiority or live capital performance.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P43 — Proposal Section 8.1 AI-Native Blockchain Integration

**Action:** AMEND

**Reason:** 0G context is valid but no implemented AI/compute optimization or unique measured benefit is established.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The prototype targets the 0G ecosystem and its integrated staking/liquidity protocols. Its contribution is the evidence-qualified allocation architecture; no separate AI-service optimization, compute-credit APY or quantified benefit from the ecosystem's AI-native positioning is claimed.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P44 — Proposal Section 8.2 Multi-Asset Vault

**Action:** REPLACE

**Reason:** “Beyond ETH-only restaking” overstates current multi-asset optimization.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The reference vault exposes a generic approved-asset custody boundary and modular adapters. The current optimizer and evaluation remain native-0G only. Multi-asset user input is an architectural extension rather than a completed allocation capability.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P45 — Proposal Section 8.3 Intelligent Yield Routing

**Action:** AMEND

**Reason:** “Dynamic strategy recommendations” can imply automatic live routing; final output is current-request advisory.

**Frozen basis:** `docs/application_contract_iteration25.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Current-request recommendations combine qualified exact-amount economics with explicit deterministic policy constraints and selected-point revalidation. The system is advisory and may retain all capital idle; it does not autonomously manage existing positions or submit public transactions.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P46 — Proposal Section 8.4 Cross-chain Yield Aggregation

**Action:** REMOVE

**Reason:** No independent multi-chain user-capital routing exists; Ethereum is dependency-only and Base KIV. Preserve context in 3.0 and future work, not as a delivered differentiator.

**Frozen basis:** `docs/current_state_iteration26.md` (accepted Iterations 1–26 at the technical head above).

**Removal recommendation:** Remove this unsupported/editorial passage after review. No replacement text is proposed.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P47 — Proposal Section 8.5 Risk-aware Optimization

**Action:** AMEND

**Reason:** “Not simply highest APY” needs exact supported deterministic constraints and non-probabilistic qualification.

**Frozen basis:** `data/evaluation_policy_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The final method separates expected-profit ranking from concentration, staking stress, range-aware LP absolute-stress and optional cash-deadline feasibility. Evidence/gate failures remain typed exclusions. This makes constraints inspectable without constructing an opaque risk score or asserting empirical probability estimates.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P48 — Proposal Section 8.6 Conclusion and future work (new)

**Action:** ADD

**Reason:** Proposal lacks a bounded final conclusion and explicit deferred capabilities.

**Frozen basis:** `docs/final_evaluation_findings_iteration24.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> The prototype demonstrates reproducible native-0G decision-sleeve allocation with exact candidate economics, evidence qualification, deterministic policy and explicit idle abstention. Synthetic comparisons establish behavior within the chosen model and show two controlled sensitivities, while capability differences and incomplete production evidence constrain interpretation. Future work may acquire qualified observational economics and address alternate inputs or whole-portfolio state; none is represented as already implemented. Public deployment is not a required capstone milestone.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P49 — Proposal Section Trailing unnumbered income/high-budget prompt

**Action:** REMOVE

**Reason:** The request to generate income is unsupported by synthetic evaluation and unsuitable as a capstone conclusion.

**Frozen basis:** `docs/final_evaluation_findings_iteration24.md` (accepted Iterations 1–26 at the technical head above).

**Removal recommendation:** Remove this unsupported/editorial passage after review. No replacement text is proposed.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P52 — Proposal Section Figure 4.1 — Optimizer workflow

**Action:** AMEND

**Reason:** Current caption terminates in approval before execution, not evidence/policy revalidation and deployment-independent output.

**Frozen basis:** `docs/application_contract_iteration25.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Figure 4.1. Intended decision-sleeve recommendation workflow. Qualified evidence and exact candidate economics feed feasibility filtering, expected-net-profit selection and selected-point revalidation before a current-request advisory result. The workflow does not establish public execution or whole-portfolio compliance.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P53 — Proposal Section Figure 5.1 — Off-chain/on-chain architecture

**Action:** AMEND

**Reason:** Caption calls AscendProtocolAdapter live and implies registered capstone instances.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Figure 5.1. Intended separation of off-chain recommendation from reference vault/adapter custody controls. AscendProtocolAdapter is the source-level external SourceCore interface; all capstone runtime bindings remain unresolved. Arrows describe design relationships, not performed public transactions.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P54 — Proposal Section Figure 5.2 — Deposit and initial allocation

**Action:** AMEND

**Reason:** Caption needs hypothetical source/local qualifier rather than proof of an operational allocation flow.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Figure 5.2. Source-level intended deposit-to-idle and user-authorized allocation flow through the registry and adapters. Local simulation validates controls; no public capstone allocation is claimed. Current optimizer inputs remain native 0G.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P55 — Proposal Section Figure 5.3 — Live Ascend deposit/withdrawal

**Action:** AMEND

**Reason:** External protocol path is confused with public capstone runtime execution.

**Frozen basis:** `docs/deployment_architecture_iteration18.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Figure 5.3. Intended Ascend adapter deposit and withdrawal architecture: native 0G is wrapped to W0G for SourceCore/a0G accounting; request, epoch/funding and claim precede W0G unwrapping to native cash. This is a source-level path with unresolved runtime binding and Ascend allocation CLOSED.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P57 — Proposal Section Figure 5.5 — Withdrawal state flow

**Action:** AMEND

**Reason:** Two-stage flow is useful but lacks distinction from modelled cash timing and successful quote execution.

**Frozen basis:** `data/risk_exit_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Figure 5.5. Intended synchronous and asynchronous request/claim withdrawal states. Queue maturity, funding and claimability are separate where applicable; successful execution and time-to-native-0G are not established by the diagram. Synthetic timing is modelled.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P58 — Proposal Section Figure 6.1 — Data/evaluation pipeline

**Action:** AMEND

**Reason:** “Data and evaluation pipeline” lacks canonical-evidence versus synthetic-scenario boundary.

**Frozen basis:** `data/final_evaluation_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Figure 6.1. Evidence-qualified production and explicit synthetic evaluation boundaries. Metadata, configuration, admission, economics, deterministic stress and exit timing are distinct inputs; synthetic assumptions do not populate canonical evidence. Frozen comparison results do not establish execution readiness.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P59 — Proposal Section Table 5.1 — Withdrawal types

**Action:** AMEND

**Reason:** LP immediate redemption cannot be interpreted as execution guarantee; queue-based Ascend needs separate stages.

**Frozen basis:** `data/risk_exit_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Table 5.1. Intended withdrawal stages and cash-output qualification.
>
> | Path | Operational type | Stages | Cash output | Qualification |
> |---|---|---|---|---|
> | Native / Gimo | Asynchronous | Request, waiting period, claim | Native 0G | Canonical timing unresolved; evaluation timing modelled |
> | Jaine / Oku | Synchronous operation | Remove liquidity, collect/swap to W0G, unwrap | Native 0G | Successful execution quotes not established by synchronous structure |
> | Ascend | Queue-based | Request, epoch maturity, funding, claim W0G, unwrap | Native 0G | Stage availability/timing unresolved; gate CLOSED |
>
> Holding horizon and optional cash deadline remain separate from time-to-cash after an exit decision.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P60 — Proposal Section Table 6.1 — Static strategy metadata schema

**Action:** REPLACE

**Reason:** Execution/technical eligibility columns alone collapse canonical category, gate, runtime and proof.

**Frozen basis:** `data/metadata_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Table 6.1. Independent metadata dimensions for strategy qualification.
>
> | Field group | Canonical fields | Meaning |
> |---|---|---|
> | Identity/domain | strategy_id, execution_chain_id, dependency_chain_ids | Intended execution versus external dependency |
> | Assets/path | input_asset, internal_assets, position_asset, capital_path | Native decision asset, execution representations and receipt/LP position |
> | Membership/category | optimizer_universe, reconciliation_category | Structural candidate versus explanatory ecosystem row |
> | External/integration | protocol_availability, integration_status | External protocol state versus capstone implementation |
> | Gate/evidence | allocation_gate, evidence_readiness | Allocation permission and evidence gaps |
> | Runtime/proof | runtime_feasibility, live_capstone_proof | Runtime/public proof, separate from protocol availability |
>
> The canonical runtime configuration is additionally assessed in a separate artifact; a scalar execution label does not establish final eligibility.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P61 — Proposal Section Table 6.2 — Dynamic snapshot schema

**Action:** REPLACE

**Reason:** Single snapshot table conflates return metrics, exact quotes, costs, risk and liquidity evidence.

**Frozen basis:** `data/economics_evidence_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Table 6.2. Separate canonical economic evidence records.
>
> | Record | Context and content | Qualification |
> |---|---|---|
> | Return evidence | Metric/unit, value, fee basis, source role, measurement period | Return semantics and qualified horizon normalization |
> | LP quote evidence | Exact amount, direction, pool/context, output/loss, quote identity | Amount/context/source/freshness validity, separate from admission |
> | Lifecycle cost evidence | Fixed/variable/quote/structural-zero basis, native amount and valuation provenance | Costs applied once or at exact amount; missing is not zero |
> | Shared provenance | Evidence class, observation/retrieval times, optional blocks, chain/config context | Preserve observation, derivation, history, model/static and missing distinctions |
>
> Risk and exit outputs belong to separate model contracts. Optional unknown fields remain null; no timestamp, block, cost or risk value is fabricated.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P62 — Proposal Section Table 6.3 — Primary sources and usage

**Action:** AMEND

**Reason:** Sources lack role qualification and may imply current verified records for Ascend or LP execution.

**Frozen basis:** `data/economics_evidence_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Table 6.3. Acquisition references and limitations.
>
> | Reference | Potential evidence role | Limitation |
> |---|---|---|
> | Native Explorer/RPC/staking interface | Validator yield/commission and staking state | Sample benchmark is not configured-validator return or headroom |
> | Gimo contracts/documentation | st0G exchange-rate and fee evidence | APY requires qualified history; net fees counted once |
> | Jaine/Oku pool/periphery data | LP return proxy and distinct execution quotes | Historical volume/liquidity does not establish current registered-range economics |
> | Incentive sources | Realizable financial reward evidence | Points/non-financial credits excluded; realization must be supported |
> | SourceCore/a0G and dependency references | Exchange-rate, fee and withdrawal/backing context | Embedded return counted once; Ascend gate remains CLOSED |
>
> These sources are acquisition leads. Canonical economics records remain empty and no fresh capture is implied by the evaluation.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

### P63 — Proposal Section Table 6.4 — Sensitivity variables

**Action:** REPLACE

**Reason:** Proposed one-factor risks/bridge knobs are not the actual accepted matrix or isolated causal tests.

**Frozen basis:** `data/final_evaluation_contract.md` (accepted Iterations 1–26 at the technical head above).

**Proposed proposal text:**

> Table 6.4. Frozen evaluation dimensions and interpretation boundaries.
>
> | Scenario group | Variation | Interpretation |
> |---|---|---|
> | Core matrix | Three profiles, three notionals, three horizons | Deterministic comparison under shared supported assumptions |
> | Fixed-cost pair | FIXED_100 / FIXED_ZERO_CONTROL | Controlled within-model causal sensitivity |
> | Quote-curve pair | QUOTE_CURVE / QUOTE_CONSTANT_CONTROL | Controlled within-model causal sensitivity |
> | Deadline/profile cases | Cash deadline and profile feasibility | Diagnostic behavior under modelled timing and joint constraints |
> | Evidence/failure cases | Missing return/cost/quote, mismatch, admission, gate, negative economics and ties | Typed abstention and method-capability behavior |
>
> Only the two controlled pairs identify isolated causal sensitivities; other contributor annotations are associated diagnostics.

**Suggested supporting artifact:** See the section-specific integration map below where applicable; source contracts/metadata are traceability evidence, not new report figures.

**Claim boundary:** Intended/source/local behavior and explicitly synthetic evaluation do not establish observed market performance, public deployment or execution readiness. Preserve any additional limitation in the proposed text.

## Recommended Table and Figure Integration

All paths below are existing frozen artifacts. Use the files exactly as committed; do not recreate images, regenerate values or truncate away qualifications. Proposed captions are staged text, not changes to frozen captions. Table numbering is provisional. The complete representative table is lengthy; treat it as optional appendix material rather than silently generating an uncommitted subset. Synthetic labels and full capability/causal limitations must remain visible. No evaluation artifact belongs in the dashboard.

| Existing frozen artifact | Target proposal section | Status | Why include / key message | Proposed caption | Claim boundary |
|---|---|---|---|---|---|
| `results/final_tables/01_capabilities.md` | 6.4 Methodology | RECOMMENDED | Fair comparison requires explicit selection-time capability differences. | Selection-time capabilities of the four methods in the deterministic synthetic comparison. | Unsupported is not passed/zero; rescoring does not grant capabilities. |
| `results/final_tables/05_disagreements.md` | 6.5 Results | RECOMMENDED | Compact disagreement and positive/negative/zero common-rescore summary. | Allocation disagreement and common post-selection rescore over the defined synthetic matrix. | 27 disagreements are not 27 improvements; mean +$43.40, median zero; LIMITED internal-objective comparability. |
| `results/final_tables/07_causality.md` | 6.5 Interpretation | RECOMMENDED | Makes controlled sensitivity versus associated diagnostics explicit. | Controlled paired sensitivities and non-isolated diagnostic contributors. | Only fixed-cost and quote-curve pairs support isolated within-model sensitivity. |
| `results/final_figures/03_fixed_cost.png` | 6.5 Economics sensitivity | RECOMMENDED | FIXED_100/FIXED_ZERO_CONTROL demonstrates fixed-cost effect; larger notionals are context. | Fixed lifecycle-cost paired ablation under identical synthetic return, notional and policy assumptions. | Causal sensitivity within the model only; larger-notional comparisons are not the controlled pair. |
| `results/final_figures/04_quote_curve.png` | 6.5 Economics sensitivity | RECOMMENDED | QUOTE_CURVE/QUOTE_CONSTANT_CONTROL changes selected Jaine amount. | Exact-amount LP quote-curve paired sensitivity in the synthetic model. | Not a captured executable quote, market effect or observed price-impact curve. |
| `results/final_figures/06_deadlines.png` | 6.5 Liquidity feasibility | RECOMMENDED | 1/8/15-day deadlines illustrate the modelled asynchronous exit boundary. | Current-request allocations under 1-, 8- and 15-day cash deadlines with modelled exit timing. | Not guaranteed withdrawal times; deadline effect is not an isolated causal risk estimate. |
| `results/final_figures/05_profiles.png` | 6.5 Profile feasibility | RECOMMENDED | Jaine 30/60/80% exposes transparent increasing policy tolerance. | Synthetic LP profile progression under concentration, absolute-stress policy and grid constraints. | Joint constraint/grid diagnostic, not LP-stress-only causal attribution. |
| `results/final_figures/07_profit_deltas.png` | 6.5 Results or appendix | OPTIONAL | Displays all positive/negative/zero deltas rather than only mean. | Common exact-allocation post-selection rescore: amount-aware minus legacy. | Different from internal selection-objective delta; no percentage superiority or forecast. |
| `results/final_tables/04_representative_scenarios.md` | Results appendix | OPTIONAL | Complete traceable method rows for controlled pairs, deadlines, gates and abstention. | Representative frozen synthetic scenarios and method-specific diagnostics. | Use complete frozen table; missing/unsupported values stay typed; main-text duplication should be avoided. |
| `results/final_figures/02_allocations.png` | 6.5 Opening example | OPTIONAL | Middle core profile/notional/horizon example illustrates method differences without profit cherry-picking. | Four-method allocations for the Balanced, 1,000-0G, 90-day synthetic core case. | Illustrative case only, not typical market behavior or proof of best-method performance. |
| `results/final_tables/02_matrix.md` | 6.4 Methodology appendix | OPTIONAL | Compact 49/27/22/196 design counts if prose alone is insufficient. | Defined deterministic synthetic experiment matrix. | Counts are design dimensions, not statistical sample representativeness. |
| `results/final_tables/03_outcomes.md` | Results appendix | OPTIONAL | Recommendation versus idle counts can show abstention as valid. | Recommendation and idle outcomes within the defined deterministic matrix. | Rates are matrix percentages, not success probabilities. |
| `results/final_figures/01_outcomes.png` | None by default | DO_NOT_INCLUDE | Redundant with optional outcome table; recommendation count is not performance success. | No insertion proposed. | Do not label recommendation frequency success or market suitability. |
| `results/final_figures/08_constraints.png` | None by default | DO_NOT_INCLUDE | Nonexclusive diagnostics are less central than controlled sensitivities; avoid frequency interpretation. | No insertion proposed. | Diagnostic counts are not probabilities or isolated causes. |
| `results/final_tables/06_constraint_diagnostics.md` | None by default | DO_NOT_INCLUDE | Keep in frozen evidence package; main report need not duplicate contributor counts. | No insertion proposed. | Associated candidate-exclusion/selected-binding counts, not empirical frequencies. |

### Existing proposal visual/table treatment

Figures 3.1/3.2 and 5.4 are retained in context. Figures 4.1, 5.1–5.3, 5.5 and 6.1 have staged caption amendments above; their embedded labels require human review before use. They are existing proposal graphics, not newly generated repository figures. Table 5.1 is amended for exit qualification. Tables 6.1–6.4 and the two unnumbered strategy/profile tables require the proposed schema/taxonomy changes. This iteration stages those textual amendments without producing replacement artwork or editing native tables. Do not include the independent-restaking/lending MVP table unchanged, generic IL proxy as final LP risk, a live-transaction milestone, duplicated full benchmark output or the high-budget/income prompt.

## Proposal consistency checklist

The checks below refer to this proposed wording, not approval or completed changes in the real proposal.

- [x] Exactly five independent strategies; no sixth W0G or embedded restaking allocation.
- [x] Native 0G only; W0G internal/auxiliary and direct W0G/ETH/BTC inputs deferred.
- [x] DECISION_SLEEVE; existing positions EXOGENOUS_NOT_OPTIMIZED; whole-portfolio compliance NOT_ASSESSED.
- [x] INTEGRATED_ALLOCATABLE / INTEGRATED_GATED remain distinct from CONDITIONAL / CLOSED; Ascend CLOSED.
- [x] Intended Mainnet 16661 is not deployment proof; Galileo W0G remains unresolved, with no address substitution.
- [x] Public deployment not required/planned; no claim of live capstone management, transaction proof or execution readiness.
- [x] Runtime configuration UNRESOLVED; execution readiness/public proof NOT_ESTABLISHED.
- [x] Production canonical evidence missing/empty and all profiles 100% idle; synthetic mode explicit.
- [x] POLICY_AWARE_AMOUNT_OPTIMIZER primary; legacy linear reference/comparison only.
- [x] Exact candidate economics/fixed cost once/quote applicability/admission/revalidation preserved.
- [x] Missing return/cost/risk/capacity never means zero or unlimited.
- [x] Schema 1.4 current-request interface; schema 1.3 compatibility-only; no benchmark report dashboard.
- [x] Range-aware LP absolute stress final; IL and HODL movement not added twice; legacy generic proxy stays compatibility-only.
- [x] Modelled staking severity and independent budgets imply no event probability, VaR or calibrated correlation.
- [x] Holding horizon, exit decision, modelled time-to-cash and optional cash deadline distinct; no guaranteed timing claim.
- [x] SYNTHETIC_EVALUATION_ONLY applies to evaluation economics, quotes, risk, timing and results; no current market APY substitution.
- [x] Four-method capabilities reported honestly; 27/49 disagreement is deterministic matrix behavior, not empirical frequency.
- [x] Common rescore is post-selection; positive/negative/zero and median zero retained; no universal or percentage superiority claim.
- [x] Only two controlled paired ablations support within-model causal sensitivity; other contributor labels are diagnostic.
- [x] Synthetic/modelled, empty evidence, unresolved configurations, grid, scope and comparability limitations explicit.
- [x] Existing frozen artifacts only; no newly generated figure, statistic or benchmark scenario.
- [x] No real proposal/Drive mutation; code, data, dashboard, contracts and frozen result artifacts unchanged.
- [ ] Human approval of each amendment, in-image label check, final numbering and later insertion remain pending.

## Validation and handoff

`python -m pytest -q tests/test_proposal_reconciliation.py` validates the staging labels, action/block coverage, sources, artifact existence and documentation-only diff. `python tools/generate_final_results.py --check` checks the frozen report package without an optimizer run. Deployment audit/preflight are read-only evidence checks. No evaluation is run under altered assumptions; the draft does not create new results. A final read-only native revision check matched the revision recorded above. Later application must re-read the proposal and re-ground any concurrently changed section rather than assuming this snapshot remains current.

Validation record: **95 reconciliation checks passed; 998 full Python tests passed**. Iteration 23 replay preserved 49 scenarios / 196 rows exactly; Iteration 24 replay preserved all 34 outputs (7 tables / 8 figures) byte-for-byte. Deployment-history audit, deployment preflight and git diff checks passed. A file-by-file comparison against the accepted technical head confirms all previously tracked repository files are unchanged; only this draft and its lightweight validation test are added. No Drive write action, export/import, proposal replacement, new result or figure generation occurred. Frontend/Hardhat builds were unnecessary because their files were untouched.

**Iteration 27 creates a repository-side proposal reconciliation draft and amendment map only. The real proposal remains untouched. All proposed amendments are staged for subsequent section-by-section human review before insertion into the final proposal.**
