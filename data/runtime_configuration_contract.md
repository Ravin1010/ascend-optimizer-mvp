# Actual strategy runtime configuration — Iteration 16

Canonical dataset: `data/runtime_strategy_config.json` (schema 1.0), loaded by
`src/ascend_optimizer/runtime_config.py`. Exactly five records, current execution
chain 16661. The accepted evidence baseline inspected was commit
`e624eb9823662479f92b8044c35fc729f5251fda`.

## Verification result

**No actual registered capstone route could be conclusively verified.** All five
records are UNRESOLVED, with config_identity, verification_source, verified_at and
block provenance null. This is not a claim that the protocols do not exist.
Known protocol/source-code constants are preserved as partial components, not
promoted into verified current deployment identities.

The accepted repository has no tracked deployment manifest, adapter/vault/manager
address set or StrategyManager registration capture. `hardhat.config.js` defines
compiler/test paths only. Constructors and mock contract tests demonstrate the
integration interfaces, not a deployed Mainnet instance. No concrete deployed
capstone address was supplied for an on-chain registration/immutable read; no
RPC queries were used to discover a replacement route or select a validator/pool.
An actual route requires either a provenance-backed deployed registration or an
explicit authoritative configured deployment manifest with the same verified
chain/role/code relationships. A collector's reference constants are insufficient.

| Strategy | Known components | Missing actual binding | Identity / state |
|---|---|---|---|
| Native | Native0GStakingAdapter implementation | Validator, adapter/vault/manager deployment, registration | null / UNRESOLVED |
| Gimo | Stake pool/token constants; withdrawal surface is stakePool | Actual adapter stakePool/st0g/referral and registration; chain/code role proof | null / UNRESOLVED |
| Jaine | Source-code factory/router/NPM/W0G/USDC.e; V1 ABI | Registered pool/token order/fee/spacing/ticks/sqrt bounds/target and adapter registration | null / UNRESOLVED |
| Oku | Separate factory/Router02/NPM; same repository token constants | Its own registered pool/config and adapter registration | null / UNRESOLVED |
| Ascend | SourceCore/W0G references; SourceCore ERC4626 shares as a0G | Actual adapter/source/asset/WithdrawalQueue relationship and registration | null / UNRESOLVED; allocation CLOSED |

The Gimo official app corroborates stake `0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF`
and st0G `0x7bBC63D01CA42491c3E084C941c3E86e55951404`:
https://app.gimofinance.xyz/. This is protocol-reference MATCH, not actual
capstone deployment/code verification. Official Mainnet network reference:
https://build.0g.ai/chain (16661, https://evmrpc.0g.ai). No external token/pool
address was substituted into the frozen configuration.

No VERIFIED-strategy address table exists because none passed the actual-route
standard. Every address in the current JSON is labelled through UNRESOLVED state
and pinned source provenance; no fresh on-chain role/code/block claim was invented.
Ethereum backing addresses are excluded from the user-facing Ascend identity.
Galileo/Base/Ethereum addresses were not reused. No admission/headroom was read.

## Record dictionary

| Field | Meaning |
|---|---|
| strategy_id | Exactly one frozen independent strategy |
| execution_chain_id | Current route execution chain; 16661 |
| verification_state | VERIFIED or UNRESOLVED |
| verification_source | Proof source ID; required VERIFIED, null UNRESOLVED |
| verified_at | Time verification occurred; aware ISO timestamp for VERIFIED, null UNRESOLVED |
| block_number / block_hash | Optional genuine verification block provenance |
| config_identity | Canonical complete fingerprint for VERIFIED; null UNRESOLVED |
| config_components | Route-defining fields; unresolved values null, not fabricated |
| evidence_sources | Source IDs/types/locations and findings; repository references pinned by commit and SHA256 of content |
| verification_notes | Qualifications and explicit resolution requirements |

A VERIFIED record must have complete normalized components, exact recomputed
fingerprint, identified deployment/on-chain/verified-explorer proof, proof coverage
of strategy registration and every component, correct proof chain and contract-code
verification assertions for all route addresses. Official/market/project references
alone cannot qualify an actual deployed route. These are strict evidence assertion
checks; the loader does not independently authenticate a human-supplied proof or
perform RPC calls. Future verification must provide auditable underlying artifacts.
Unknown IDs, wrong chain, duplicates, malformed schema, missing required components,
forged/mismatched fingerprints or unsupported verification claims are rejected.
Malformed/missing configuration datasets cause the provider to fail closed.

## Deterministic identity specification

Version: `RUNTIME_ROUTE_V1`. Serialize this envelope as UTF-8 JSON:
`identity_version`, `strategy_id`, `execution_chain_id`, `config_components`.
Use `sort_keys=True`, separators `(',', ':')`, `ensure_ascii=True`, no NaN.
Addresses and bytes32 registration keys normalize to lowercase `0x` hex; zero
addresses/keys reject. Numeric components must be JSON integers (no float/boolean
coercion). Strings retain exact content; empty Gimo referral is allowed, null is
unresolved. Unknown/extra/missing component keys reject. No partial fingerprint
qualifies UNRESOLVED records. Fingerprint: `sha256:` + SHA256(serialization).

Identity-defining common fields:
- adapter_address, vault_address, strategy_manager_address, manager_strategy_key,
  adapter_class (so an ID binds the actual capstone instance and registration).

Strategy-specific identity fields:
- Native: validator (the delegation/queue contract itself).
- Gimo: stake_pool, st0g, withdrawal_contract, referral.
- Jaine/Oku: factory, router, position_manager, pool, w0g, usdce, token0, token1,
  fee_tier, tick_spacing, tick_lower, tick_upper, sqrt_lower_x96, sqrt_upper_x96,
  target_usdc_bps, router_mode. Jaine V1 and Oku ROUTER02 are checked separately.
- Ascend: w0g, source_core, a0g, withdrawal_queue; no full remote backing graph.

LP token ordering must match the W0G/USDC.e pair; tick range/spacing, sqrt bound
ordering and target must be structurally valid. These structural checks do not
replace chain-state proof of the configured values or registered-range stress.
Fee/range/target/address/chain/registration/referral changes alter identity.
Description, findings, verification time/source, block and notes are provenance,
not fingerprint inputs. Limits/headroom, TVL, yields, quote amounts, timestamps
and remote risk observations are not route identity. Capacity is not introduced.

Reproduce a complete hypothetical/future record with
`config_fingerprint(strategy_id, execution_chain_id, config_components)`.
Tests independently calculate SHA256 from the canonical serialized envelope,
check key-order/address-case stability and mutate each relevant LP parameter.
Current repository records intentionally have no concrete fingerprint example:
printing an invented route hash as an actual identity would be misleading.

## Contradictions and stale claims

| Strategy / component | Repository claim | Corroboration / current limitation | Disposition |
|---|---|---|---|
| Chain | Five metadata execution chains are 16661 | Official 0G Mainnet docs agree | MATCH (network only) |
| Native | Sample validators exist | No sample is an adapter configuration | NOT_APPLICABLE as route proof; configured validator unresolved |
| Gimo | Collector/CSV stake + st0G constants | Official app labels agree; no capstone registration proof | MATCH references; actual config unresolved |
| Jaine | Wrapper pins periphery/tokens | Pool/range/target deliberately constructor inputs, no registered instance | NOT_APPLICABLE as complete route proof |
| Oku | Distinct Router02 periphery | Separate deployment inputs, no registered instance | NOT_APPLICABLE as complete route proof |
| Both LPs | README says planner/runtime and deployed allocation basis agree | Planner recomputes observed range/target; registered alignment not established | STALE_REPOSITORY_VALUE (claim of alignment), no route substituted |
| Ascend | CSV/collector SourceCore/W0G agree | Queue and capstone registration absent; external backing reference is not route proof | MATCH repository references; actual config unresolved |
| Documentation wording | 'verified' periphery / 'live execution' | Implementation/protocol reference does not establish capstone deployed configuration or transaction proof | STALE_REPOSITORY_VALUE as proof wording |

No concrete contradictory on-chain registered route was available; therefore no
pool/validator conflict is invented. UNRESOLVED here primarily means insufficient
actual binding evidence, not discovered disagreement. Resolution requirements
are retained per strategy in the JSON. README/comments were not edited.

## Context generation and admission separation

`runtime_config_contexts()` loads the canonical dataset. VERIFIED yields its
fingerprint/source; UNRESOLVED yields `config_identity=''`, UNRESOLVED and no
verification source. Missing records never become verified: the exact-five loader
rejects them. RepositoryAdmissionProvider defaults to this independent dataset
and reloads it on every candidate lookup and selected revalidation. Explicit
synthetic contexts remain test-only overrides; no identity comes from captures,
TVL, samples, rates, market notes or newly discovered pools.

A changed runtime identity Y invalidates old capture identity X: X != Y produces
CONFIG_MISMATCH and runtime UNKNOWN, including during selected revalidation.
A VERIFIED config without an admission capture still returns UNKNOWN. Freshness
uses Iteration 15 as_of policy unchanged; verification cannot open Ascend CLOSED.
Default context records all remain UNRESOLVED, so no positive support is introduced.

Schema 1.3 and TypeScript/API/dashboard contracts were not changed. No optimizer
math, policy thresholds, LP quote TTL, costs, risk, portfolio state or proposal
work was bundled. W0G remains an execution representation, not a sixth strategy.

## Repository-only baseline

`python -m src.ascend_optimizer.amount_demo --as-of 2026-10-09T11:10:00Z`
loads canonical contexts and the unchanged headers-only admission CSV. Conservative,
Balanced and Aggressive all select no positive route and retain 100% idle. There
are zero VERIFIED current contexts; no synthetic contexts are used in this run.

## Validation

- Focused configuration tests: 31 passed.
- Configuration + evidence + freshness + amount-aware tests: 168 passed.
- Full Python suite: 337 passed; one existing Gimo pandas FutureWarning.
- Python result/serialization tests: 26 passed.
- Actual API contract tests: 7 passed.
- No TypeScript types changed; typecheck/build were not required or run.
- Repository-only fixed-time baseline: all three profiles 100% idle.
- Admission CSV unchanged and headers only; git diff --check passed.
