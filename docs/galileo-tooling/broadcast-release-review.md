# Galileo release review — public submission remains disabled

Parent: `c2a48978e5d7baa1806a75fc0444a71bf8875afd`, branch
`feature/galileo-deployment-tooling`. This updates release authorization only.
The controlled executor's transaction, spending, receipt, state-verification and
resume engine is unchanged. The earlier controlled-executor document records the
previous sealed release; this document supersedes its public-entry description.

## Frozen exercise

Chain 16602; public owner/user
`0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a`. Native, Gimo, Jaine-style and
Oku-style use mocked external dependencies and are active; Ascend is MOCK,
inactive, with zero allocation. The graph remains 19 deployments, 9 configuration/
registration calls and 5 interactions (33 total). Deposit is 10^13 wei; four
allocations are 10^12 wei each; final idle is 6 × 10^12 wei. Per-strategy cap is
10^15 wei and maximum allocation 5000 bps. Native/Gimo minShares are 10^12;
V3 minimum liquidity and each LP execution-data minimum are 5 × 10^11; router
funding is 10^12 raw mock-USDC.e units per router. Transaction deadlines are
refreshed by the unchanged engine. No rewards or withdrawals are exercised.

The reviewed configuration and plan fingerprint remain:

`8bf82574f675e6ecff0278ae680f87dcaf9c3fb376714b6caf0c7f08714e333f`

No real Gimo/Jaine/Oku/Ascend execution, consensus staking, full lifecycle,
Mainnet readiness or production readiness is established. Canonical Ascend remains
INTEGRATED_GATED / CLOSED. There is no optimizer-to-chain automation.

## Authorization sequence

1. `release-policy.js` requires exactly one external `--broadcast` flag and reads
   **only** `GALILEO_ALLOW_BROADCAST` for acknowledgement. It compares that external
   value with `YES`; it never supplies acknowledgement internally. Duplicate,
   missing or unknown arguments fail closed.
2. Require explicit expected chain 16602, exact deployer, reviewed plan hash,
   source commit, tooling fingerprint and artifact fingerprint. Require a reviewed
   pending nonce, maximum acceptable gas-price quote and short review expiry.
3. `release-integrity.js` verifies clean tracked/untracked repository state,
   approved tooling branch/lineage, source commit and a hash of all release-critical
   files. Artifacts/build output, compiler sources, no linking, Solidity 0.8.24,
   Cancun and optimizer enabled/200 are checked and fingerprinted. No private
   key, environment file or mnemonic is read.
4. `release-review.js` binds integrity from the actual repository, not caller
   assertions. Exact configuration, graph and inactive Ascend are verified.
5. Read actual chain, balance, latest/pending nonce, latest block and fee quote.
   Latest and pending nonce must match the explicit reviewed nonce. Reject stale
   network blocks (over 180 seconds from the local clock), expired reviews and
   review windows beyond 15 minutes. Correct local system time is required.
6. Calculate reserve (20% of current starting balance), fee ceiling (2× current
   quote), 20% gas-margin full-graph envelope and its 20% material-growth allowance.
   The whole requirement including reserve must fit the live wallet balance.
   No historical balance or fixed 0.01/0.1 budget is used.
7. Construct and freshly estimate the unsigned StrategyManager deployment. Use
   the existing guard for current-step cost plus the complete remaining modeled
   graph. Failure is a stop; no local estimate is substituted. Dependent future
   transactions cannot all be publicly estimated before their contracts exist;
   the unchanged engine must estimate each immediately before any future send.
8. Refresh balance, pending/mined nonce, fees, deadline and source/tooling state
   immediately before the final gate. Incompatible changes stop the review.
9. **Always throw:**

   `STOP: public transaction submission requires separate user broadcast approval`

   This is after readiness checks but before private-key loading, signer creation,
   signing or submission. The command exits with status 2 even when all checks pass.
   Its public-only readiness JSON explicitly records `signerAccessed=false` and
   `transactionsSubmitted=0`.

The old internal `broadcastGuard(["--broadcast"], { ...: "YES" })` call has been
removed from `publicExecution()`. The old legacy preflight runner's independent
seal remains unchanged. The new public entry always ends at the final review
barrier and cannot reach the execution engine.

## Command structure — placeholders only

First inspect the current committed identity and read-only funding preview:

```bash
node scripts/galileo/release-run.js --inspect
node scripts/galileo/controlled-preview.js
```

Inspection is explicitly **not authorization**. Obtain the current pending nonce
from read-only Galileo RPC, and derive a review expiry within 15 minutes of its
latest block time. Review the exact values before using the following structure:

```bash
GALILEO_ALLOW_BROADCAST=YES node scripts/galileo/release-run.js \
  --broadcast \
  --expected-chain 16602 \
  --expected-deployer <reviewed-public-address> \
  --expected-plan <reviewed-plan-fingerprint> \
  --expected-source <exact-committed-source-sha> \
  --expected-tooling <exact-tooling-fingerprint> \
  --expected-artifacts <exact-artifact-fingerprint> \
  --expected-nonce <current-reviewed-pending-nonce> \
  --max-fee-quote-wei <reviewed-current-gas-price-limit> \
  --review-expires-at <short-lived-unix-expiry>
```

Despite the explicit flag, **this release refuses execution at the final barrier**.
Neither that command, acknowledgement, previous approval, available funds nor
passing tests means user permission to transact. Actual public submission requires
a separate future user decision and separately reviewed implementation.

## Signer boundary

`release-boundary.js` defines the final refusal and a future loader interface.
The loader is unreachable before the refusal. No concrete private-key loader,
mnemonic/seed support or public signer creation is added. `GALILEO_PRIVATE_KEY` is
only a reserved future environment-variable name, not read in this release.
A later explicitly approved implementation must require human approval immediately
before invoking a loader, keep secrets out of logs/evidence/errors, and compare
the returned signer address with the reviewed deployer before any transaction.
Simply deleting a throw is not an acceptable release procedure.

The command uses ReadonlyProvider, which rejects signing/send methods (including
batches) before network transport. It accepts no signer/key/config overrides.
Only allowlisted public readiness data may be printed. Raw provider errors and
environment contents are not printed or persisted.

## Existing execution/evidence protections retained

The original 33-step local engine and all per-transaction checks remain unchanged:
fresh estimate/fee/balance/nonce, reserve and cumulative-cost limits, refreshed
deadlines, deterministic target/calldata, pinned artifacts, code/immutable checks,
state readbacks and inactive Ascend. Receipt journals still have exclusive locks,
atomic replacement, intent-before-submission, receipt/hash/nonce evidence and
strict resume verification. Pending/uncertain intents stop for manual review;
no automatic resend occurs. Confirmed-prefix and completed-run resumes retain
receipt, canonical-block, transaction, runtime, ownership/configuration, historical
balance and cost checks. Public mocks remain vulnerable to arbitrary external
setters/mints; unexpected state is a stop, not live-protocol proof.

## Review validation

Run the complete tooling suite, existing contracts, relevant Python regressions,
local 33-step rehearsal and both deterministic result checks. The release tests
cover missing/wrong intent/acknowledgement, identity/configuration/fingerprint
drift, insufficient funds/reserve, fee spikes, nonce/deadline/balance changes,
stale RPC, failed estimates, projected-spend growth and final barrier enforcement.
A trap loader/secret getter verifies no key or signer access. A clean-commit,
read-only Galileo invocation must reach the final barrier before publication;
any pre-signing failure prevents a readiness conclusion.

Validation results for this implementation:

| Check | Result |
|---|---|
| Isolated compile | Passed; pinned artifacts up to date |
| Galileo tooling tests | **107 passed**, 0 failed (36 new release tests) |
| Existing contract suite | **72 passed**, 0 failed |
| Python application/result/asset regressions | **109 passed**, 0 failed |
| Full local graph | **33 successful steps**, four positive allocations, Ascend inactive, idle 6 × 10^12 wei |
| Confirmed-prefix/completed resume | Passed; no duplicate transactions |
| Evaluation check | **49 scenarios / 196 rows; exact replay** |
| Final-results check | **7 tables / 8 figures / 34 files; exact replay** |
| JavaScript syntax / diff whitespace | Passed |

Python checks use the existing isolated validation environment and repository
requirements, including matplotlib 3.10.8. No dependency/configuration file changes
are needed. These are local validation results, not a GitHub CI-success claim.

No existing project contract, optimizer policy, evidence/configuration, dashboard,
accepted result or proposal is changed. All actual deployment remains deferred to
separate explicit user authorization.
