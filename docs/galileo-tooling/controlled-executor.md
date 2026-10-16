# Controlled Galileo executor — no-broadcast release

Parent: `aa3afe4a514fe636f1b8062e64aa5cd351124d91` on
`feature/galileo-deployment-tooling`. This adds isolated tooling only. No existing
repository file, Solidity, optimizer, canonical evidence/configuration, frontend,
proposal or frozen result is changed. No public deployment is authorized.

## Reviewed configuration and entry points

`reviewed-execution.json` fixes the public owner/user to
`0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a`, target chain 16602, and all external
dependencies to MOCK. Native/Gimo/Jaine-style/Oku-style registrations are active;
Ascend is inactive and has no allocation step. Native uses the actual project
adapter with Mock0GValidator; LP routes use separate generic V3LiquidityAdapters,
V1 and Router02 modes. No unverified Galileo W0G or external protocol is used.
Canonical Ascend remains INTEGRATED_GATED / CLOSED.

| Setting | Reviewed value |
|---|---:|
| Vault deposit | 0.00001 test 0G / 10^13 wei |
| Each of four allocations | 0.000001 test 0G / 10^12 wei |
| Ascend allocation | 0 |
| Final vault idle | 0.000006 test 0G / 6 × 10^12 wei |
| Each registration cap | 0.001 test 0G |
| Each maximum allocation | 5000 bps |
| Native/Gimo minShares | 10^12 |
| Each V3 minimum liquidity | 5 × 10^11 |
| Mock USDC.e mint per router | 10^12 raw units |
| Allocation deadline | latest block time + 3600 seconds, regenerated per call |

`controlled-plan.js` constructs the accepted graph through the unchanged original
plan builder. Its legacy required `maxGasBudget0g` argument is syntax compatibility
only, never used by the controlled budget guard. `controlled-executor.js` loads
all artifacts/build information, resolves confirmed dependencies and implements
the sequential state machine. `controlled-state.js` verifies code and state.
`evidence-store.js` supplies a single-writer, atomic journal.

Commands (from repository root):

```bash
npx hardhat compile --config hardhat.galileo.config.js
npx hardhat test --config hardhat.galileo.config.js --no-compile
npx hardhat test
node scripts/galileo/controlled-preview.js
npx hardhat run --config hardhat.galileo.config.js --no-compile scripts/galileo/controlled-local.js
```

The preview is read-only, accepts no execution flags, and rejects signing/send RPC
methods, including in batches. It reads no wallet secret. The local runner only
accepts the in-process Hardhat network, verifies chain 31337 and Hardhat metadata
before obtaining generated local accounts. It substitutes a generated local
owner/user explicitly; it does not impersonate the public user. Its exclusive
output is ignored `galileo-local/controlled-local.json`; an existing journal is
never silently overwritten. Local receipts have no Galileo explorer links.

## Exact graph

The child st0G lookup after transaction 5 is read-only and adds no transaction.

| Tx | Action |
|---:|---|
| 1–2 | Deploy StrategyManager, AscendVault |
| 3–4 | Deploy Mock0GValidator, Native0GStakingAdapter |
| 5–6 | Deploy MockGimoStakePool, GimoAdapter using child st0G |
| 7–10 | Deploy MockW0G, MockUSDCe, MockV3Factory, MockV3Pool |
| 11 | Attach factory pool |
| 12–14 | Deploy mock position manager, V1 router, Router02 |
| 15–16 | Mint mock USDC.e to the two routers |
| 17–18 | Deploy Jaine-style and Oku-style V3LiquidityAdapters |
| 19–21 | Deploy MockAscendW0G, MockAscendSourceCore, MockAscendWithdrawalQueue |
| 22 | Attach withdrawal queue |
| 23 | Deploy AscendProtocolAdapter |
| 24–28 | Register Native, Gimo, Jaine, Oku, Ascend (inactive) in that order |
| 29 | Deposit native test 0G |
| 30–33 | Allocate Native, Gimo, Jaine, Oku in that order |

Total: **19 deployments + 9 configuration/registration + 5 interactions = 33**.
RewardAccounting is not configured. No activation, reward or withdrawal call is
part of this exercise.

## Spending and transaction guards

Every step checks chain, actor, pending nonce, code/configuration, fresh balance,
fresh fees and fresh unsigned gas estimation. Failure to estimate stops; no local
measurement substitutes for a failed estimate. Constructor/calldata comes only
from the fingerprinted plan and pinned artifacts. Confirmed transaction fields
are compared with the prepared request. Deadlines are checked again after
estimation. Every deployment uses Solidity 0.8.24, Cancun, optimizer 200 artifacts;
unexpected linking/build settings fail.

Default safety policy is a 20% gas-limit margin, twice the current gas-price quote,
and a reserve of 20% of the balance at execution start. Reserve is retained across
resume and cannot shrink with spending. Configurable ranges require at least 20%
reserve and gas margin; fee multiplier is 1–2×. No 0.01 or 0.1 fixed budget applies.

The historical 22,755,179-gas reference is a planning input, not a promised fresh
estimate. The engine recomputes current-step maximum cost plus remaining graph
cost at the initial fee ceiling, and includes actual cumulative gas/value spent.
It stops above a **20% material-growth allowance** on the fee-derived initial
full-graph envelope, or at a fee spike above the initial ceiling, or on either
fresh-balance or cumulative-reserve breach. The initial affordability check also
includes that growth allowance. LP estimates can exceed historical gas *used*
because estimation needs additional internal-call headroom; fresh estimates are
used with the margin, not replaced or mistaken for gas used.

Read-only observation during validation: block **60389792**, hash
`0x156798000da691cf61341171d810f7c74045b3abffdb37664d545fc5dcab6627`,
timestamp **1792125045**, balance **0.61 test 0G**, fee quote **4.000000007 gwei**.
The preview computed an initial envelope of **0.218459824382287192 test 0G**
(including deposit), reserve **0.122**, and growth-inclusive funding requirement
**0.384151789258744631**. This is an observation, not an execution price promise;
the next review must refresh it. Projected remaining wallet balance at the growth
limit is **0.347848210741255369**, including the protected reserve.

## Receipt journal and strict resume

Evidence records step/order, hash/nonce, block number/hash, constructor and call
arguments/calldata, gas estimate/limit/used/effective price/cost, value, deployed
address/runtime hash (including Gimo child), events, mandatory readbacks, cumulative
spend and wallet balance. Local records are explicitly LOCAL_ONLY; public receipt
fields/links cannot be fabricated by preflight. Errors persist a sanitized stop
code, never raw provider errors/secrets.

A durable intent is written **before** submission; its hash is recorded immediately
after submission. Any pending/failed/ambiguous intent stops resume for manual
review instead of resending. A lock blocks concurrent writers; a crash may leave
a lock requiring manual investigation. Atomic replacement protects the journal.

Resume requires identical source, executor fingerprint, plan/config and artifacts;
contiguous unique steps/nonces; canonical successful receipts; actual transaction
sender, chain, target, value and calldata; derived deployment addresses; full code
hashes and artifact runtime matches (immutable slots handled explicitly); cost,
argument and historical balance evidence; and current ownership/configuration,
registrations and balances/shares. Unknown pending/unrelated transactions or any
ambiguity stop. A completed resume submits nothing. A confirmed prefix continues
at exactly the next step. Pruned/unavailable historical RPC data stops verification.

State readbacks cover owners, vault/manager, all adapter dependencies, Gimo child
minter/rate, factory/pool/router/NPM identities, LP range/router modes, router token
funding, five registrations/caps/active states, per-strategy shares, idle and zero
Ascend allocation. Public mocks have unrestricted setters/mints: interference is
a stop condition and no security/real-protocol claim is made.

## Validation performed

| Check | Result |
|---|---|
| Isolated compile | Passed; existing artifacts up to date, build settings checked |
| Isolated Galileo tooling suite | **71 passed**, 0 failed (47 new + 24 existing) |
| Existing root Hardhat suite | **72 passed**, 0 failed |
| Python application/result/asset regressions | **109 passed**, 0 failed |
| Standalone controlled local CLI | **33 confirmed receipts**, 33 unique hashes |
| Local gas used | **22,693,247** total; not a public gas quote |
| Final shares | Native/Gimo 10^12 each; each V3 5 × 10^11; Ascend 0 |
| Final idle / Ascend | **6 × 10^12 wei** / inactive |
| Read-only Galileo preview | Passed; `broadcastReady=false`, `transactionsSubmitted=0` |
| JS syntax checks | Passed |
| Evaluation check mode | **49 scenarios / 196 rows; exact replay passed** |
| Final-results check mode | **7 tables / 8 figures / 34 files; exact replay passed** |
| Existing-file invariance | **All 249 baseline tracked files byte-identical** |

Guard tests include wrong chain/deployer, insufficient balance/reserve, estimate
failure/material growth, fee spike, nonce/deadline/branch drift, activation,
bytecode/ownership/config mismatch, failed receipts, altered evidence, pending
intent, duplicate-step prevention, confirmed-prefix/completed resume, forbidden
RPC batches and unconditional public release gate.

Python initially could not start because this workspace lacked requests. Validation
used an isolated `/tmp/galileo-validation-python` environment with the repository
requirements and pinned matplotlib 3.10.8; no repository dependency file changed.

## Release boundary and next review

`publicExecution()` unconditionally invokes the existing release seal before
accessing caller options, signer/provider factories or secrets. The shared engine
has a future chain-16602 path, but it is unreachable. The old runner and seal
remain unchanged. No real private key was requested/read and no public signer was
created. **Zero Galileo transactions were signed, deployed or submitted.**

A separate final public-network no-broadcast rehearsal/review must validate the
committed tooling, current balance/fees, reviewed plan fingerprint, state-estimation
strategy and receipt/resume behavior before any separately authorized release-gate
change. This document grants no broadcast permission. Disposition:
**READY_FOR_FINAL_NO_BROADCAST_REHEARSAL**.
