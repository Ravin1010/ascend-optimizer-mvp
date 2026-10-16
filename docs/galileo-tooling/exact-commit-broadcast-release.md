# Exact-commit Galileo execution candidate

Parent: `dea8e5bb3e968b0f2b00a11678bc1fd10a87a6c1` on
`feature/galileo-deployment-tooling`. This supersedes the previous unconditional
public-submission barrier. The candidate is broadcast-capable **only after future
explicit approval of its exact final commit**. Implementing/testing this candidate
provides no permission to transact. No real signing credential is used for review.

## Frozen graph and claim boundary

Galileo chain 16602; owner/user
`0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a`. Native/Gimo/Jaine-style/Oku-style
are active with MOCK external dependencies; Ascend is MOCK and inactive with zero
allocation. No Native LIVE or other live external route can be substituted.
The same 33-step graph remains: 19 deployments, 9 configuration/registration and
5 interactions. Deposit is 10^13 wei; each of four allocations 10^12 wei; expected
idle 6 × 10^12 wei. Cap 10^15 wei, maximum allocation 5000 bps, Native/Gimo minimum
shares 10^12, each V3 minimum liquidity 5 × 10^11, and each mock-router USDC.e mint
10^12 raw units. Deadlines are generated per allocation from the current block.
Default reserve/gas margin are 20%; fee multiplier is 2×. No economics/policy,
contract, strategy-universe, canonical configuration/evidence or dashboard change
is made. Ascend's canonical gate stays INTEGRATED_GATED / CLOSED.

Plan fingerprint:
`8bf82574f675e6ecff0278ae680f87dcaf9c3fb376714b6caf0c7f08714e333f`

This is entry-and-allocation validation against mocks, not live Gimo/Jaine/Oku/
Ascend execution, consensus staking, reward/withdrawal lifecycle proof, Mainnet
readiness or production readiness. Mocks have unrestricted setters/mints; any
unexpected state causes a stop. No optimizer automatically authorizes transactions.

## Three independent requirements

| Requirement | Meaning |
|---|---|
| `--broadcast` and `GALILEO_ALLOW_BROADCAST=YES` | Deliberate operator selection of execution mode |
| `--approved-source` and `GALILEO_USER_APPROVED_SOURCE` | Explicit user approval of one exact reviewed commit |
| `GALILEO_PRIVATE_KEY` | Signing credential, read only after every preceding check |

Mandatory equality:

`current HEAD == --expected-source == --approved-source == GALILEO_USER_APPROVED_SOURCE`

An ancestor/descendant relationship never substitutes for equality. Any new commit,
even documentation-only, invalidates the old approval and requires review again.
The existing lineage check remains an additional constraint. Source must be clean
and on the tooling branch. Source/tooling/artifact/plan fingerprints, chain,
deployer, nonce, externally bounded current fee quote and short review expiry
remain mandatory. No condition is supplied internally on the operator's behalf.

## Ordered authorization and credential boundary

1. Parse exactly one execution flag and external acknowledgement. Reject unknown,
   duplicate, missing or mismatched arguments; key/seed/mnemonic CLI inputs are not
   supported. Validate exact CLI/environment source approval before any key getter.
2. Bind actual clean repository HEAD, tooling hash and compiler/artifact bundle to
   the expected values. Require chain 16602, frozen configuration/graph and the
   exact reviewed deployer. Artifacts use Solidity 0.8.24, Cancun, optimizer 200,
   matching current compiler inputs and no external linking.
3. Take an exclusive journal lock for execution, validate resume state if selected,
   then refresh balance, pending/mined nonce, block/time and fees. Nonces must match
   the reviewed nonce and each other. Reject stale blocks, expired reviews and
   reviews longer than 15 minutes. Validate current affordability plus fixed reserve,
   remaining modeled graph, fee ceiling and material-growth allowance. Freshly
   estimate the initial unsigned Manager deployment; later dependent transactions
   are freshly estimated against actual state by the shared engine.
4. Recheck source, approval, nonce, fees, deadline and balance. A successful review
   grants a one-use credential-access token; the low-level loader refuses direct
   calls without that token. Only then may the single `env.GALILEO_PRIVATE_KEY`
   getter run. No environment enumeration or environment-file reading is used.
5. The loader accepts only a 0x-prefixed 32-byte hex key. It creates an ethers Wallet
   only at this boundary and sanitizes constructor/credential errors. The one-use
   token is consumed before reading the credential. In a `finally` block, the local
   temporary is cleared and `GALILEO_PRIVATE_KEY` is deleted from the actual execution
   environment, on success and failure. Deletion failure or any remaining own/inherited
   property stops execution. Verify the
   derived address equals the reviewed deployer before granting a submission permit.
   There is no mnemonic/seed support. The key never enters hashes, logs, journal,
   calldata, exception details or serialized readiness data.
   Before permission is granted, verify credential absence, rerun source integrity
   and exact approval checks, and verify the signer address. Every subsequent
   permission check also rejects a reintroduced credential. Operator/source approval
   metadata remains available; the signer does not reread the credential.
6. Arm the controlled HTTP provider with the verified permission and invoke
   `runGalileo()`, which calls the existing shared engine with chain 16602 and mode
   GALILEO. There is no separate allocation engine. Per-step approval checks reject
   changed HEAD/tooling, revoked environment approval or expired review. The public
   wrapper fixes the reviewed initial nonce and external fee ceiling. Existing
   estimate, margin, reserve, cumulative spend, nonce, calldata, deadline, artifact,
   runtime, ownership/registration and inactive-Ascend checks remain in force.
7. Before raw submission, the transport rechecks the live permission. Only
   `eth_sendRawTransaction` is permitted for submission; node-account signing,
   `eth_sendTransaction`, `eth_sign` and `personal_sign` remain forbidden. HTTP
   retries are disabled. Any uncertain submission halts rather than resending.

The production entry does not accept injected signer/loader/engine/integrity
options. Tests use a separate dependency-injected orchestration kernel, fake
loaders/factories and generated local Hardhat accounts. A real key must not be
shared through chat or placed in repository files or command history.

## Read-only inspection and review — safe without approval or key

```bash
node scripts/galileo/release-run.js --inspect
node scripts/galileo/controlled-preview.js
```

To perform the complete current-state release review, use the same expected
identity/nonce/fee/expiry arguments below, but use **`--review-only` instead of
`--broadcast`**, omit `--approved-source`, and supply no approval/key environment
variables. Review mode cannot carry an approval or execution flag, uses a strictly
read-only provider, creates no journal or signer, and returns
`READ_ONLY_REVIEW_PASSED`. It never calls any credential/approval getter.

## Future execution command — placeholders only

The following documents an eventual separately authorized command. It is not an
instruction or approval to run it now. Provision the credential securely as an
environment variable outside chat/CLI history; the secret placeholder is not a key.

```bash
GALILEO_ALLOW_BROADCAST=YES \
GALILEO_USER_APPROVED_SOURCE=<EXACT_FINAL_COMMIT_SHA> \
GALILEO_PRIVATE_KEY=<SECRET_NOT_SHOWN> \
node scripts/galileo/release-run.js \
  --broadcast \
  --approved-source <EXACT_FINAL_COMMIT_SHA> \
  --expected-source <EXACT_FINAL_COMMIT_SHA> \
  --expected-chain 16602 \
  --expected-deployer <REVIEWED_PUBLIC_ADDRESS> \
  --expected-plan <REVIEWED_PLAN_FINGERPRINT> \
  --expected-tooling <FINAL_TOOLING_FINGERPRINT> \
  --expected-artifacts <FINAL_ARTIFACT_FINGERPRINT> \
  --expected-nonce <CURRENT_REVIEWED_NONCE> \
  --max-fee-quote-wei <CURRENT_REVIEWED_FEE_LIMIT> \
  --review-expires-at <SHORT_LIVED_UNIX_EXPIRY> \
  --journal galileo-local/final-galileo-receipts.json
```

A future user must approve the final reported source SHA explicitly. Existing
approvals, funds, tests, acknowledgement alone or merely running a review never
satisfy exact-commit approval. No further source edit is required to execute once
all genuine external conditions are provided. This candidate is deliberately
capable; do not run execution mode during no-broadcast review.

## Evidence, resume and recovery

The public journal is restricted to an isolated JSON file under ignored
`galileo-local/`, with no symlink escape. Fresh execution refuses an existing file;
continuation requires explicit `--resume` and the same path. Exclusive locks prevent
concurrent writers. Atomic journal replacement now fsyncs both data and directory,
so intent is durably recorded before sending and hash is recorded immediately after
a send returns. A crash/timeout/failed receipt leaves a stopped/pending journal for
manual investigation. Never delete a lock or pending intent merely to retry.

Every confirmed step retains order/name, hash/nonce, block/hash, gas estimate/limit/
used/price/cost, value, deployed address, constructor/call arguments and calldata,
runtime hash, events, mandatory readbacks, cumulative spend, wallet balance and
Galileo explorer link. Failures retain sanitized error/stop state and pending hash
when available. No receipt data is fabricated when the network outcome is unknown.

Read-only resume validation verifies the complete successful contiguous prefix,
canonical receipts, sender/nonce/target/value/calldata, deployment address derivation,
artifact/runtime hashes including immutable handling, ownership/configuration,
registrations/shares/idle, historical gas cost/balance and source/tooling/config
identity. The original reserve and cumulative fee envelope remain fixed from the
first run. Remaining-graph affordability is recalculated without redeploying a
confirmed prefix. Unavailable historical RPC state is a stop. A completed run is
verified and returned as ALREADY_COMPLETED before key loading; it submits nothing.

Tests retain confirmed-prefix/completed resume, duplicate prevention, ambiguity,
failed/reorged receipt and evidence-tampering protection. An expired review can be
renewed for the same approved commit with fresh nonce/fees/expiry; it never
permits an uncertain intent to be resent automatically.

## Validation and freeze discipline

Run all Galileo tooling tests, the unchanged contract suite, relevant Python
application/result/asset regressions, compile/syntax checks, local 33-step rehearsal
and both deterministic result checks. The exact-approval tests use fake environment
objects, injected factories/signers and mocked HTTP; **no real ethers Wallet is
created from a public credential during testing**. Real Galileo review uses only
`--review-only`, with no source-approval or key environment values.

Validation results:

| Check | Result |
|---|---|
| Isolated compile/build-specification checks | Passed |
| Complete Galileo tooling suite | **148 passed**, 0 failed (133 previous + 15 credential-isolation tests) |
| Existing Hardhat contract suite | **72 passed**, 0 failed |
| Relevant Python application/result/asset regressions | **109 passed**, 0 failed |
| Local shared-engine rehearsal | **33 successful steps**, only four allocations, Ascend inactive/zero, idle 6 × 10^12 wei |
| Confirmed-prefix and completed-run resume | Passed; no duplicates |
| HTTP submission retry test | One attempt using fake transport; no network/signing |
| Evaluation check | **49 scenarios / 196 rows; exact replay** |
| Final-results check | **7 tables / 8 figures / 34 files; exact replay** |
| JavaScript syntax / whitespace checks | Passed |

These are local checks, not GitHub CI-success claims. Public review of the final
committed candidate uses only read-only Galileo RPC and cannot access the key.

After the single final commit is created, record that commit plus the plan,
tooling and artifact fingerprints from `--inspect`, verify the clean committed
read-only review, and publish the tooling branch. Do not make another commit after
reporting the candidate. Main, canonical project state and frozen results remain
unchanged. This iteration itself authorizes **zero Galileo transactions**.


## Credential-isolation correction (parent e960fca858822dd9f30c3bfc2b04630c32dc6f92)

`subprocess-env.js` supplies a fresh explicit allowlist (`PATH`, `SystemRoot`,
`WINDIR`, `PATHEXT`, `LANG`, `LC_ALL`, `TZ`). It never enumerates the parent
environment and never reads the signing credential. No approval or signing
variables, Git environment overrides, preload variables or proxy settings are
passed to Git. Approval variables remain intact in the parent execution environment.
The helper itself is pinned by the release tooling fingerprint.

Complete child-process audit of `scripts/galileo/`:

| File | Child operations | Explicit environment |
|---|---|---|
| `release-integrity.js` | Git HEAD, branch, status, lineage (four calls per source check, including repeated execution checks) | `sanitizedChildEnv()` |
| `run.js` | Legacy preflight Git HEAD and status | `sanitizedChildEnv()` |
| `controlled-local.js` | Local rehearsal Git HEAD | `sanitizedChildEnv()` |

There are no other `exec`, `execFile`, `spawn` or `fork` call sites in the Galileo
JavaScript tooling. No contract, reviewed graph, amount, registration, authorization,
transport, receipt or resume semantics are changed by this correction.

`CredentialIsolation.test.js` uses synthetic fixtures and injected factories only:
a single getter read; removal on success, malformed/missing input, throwing getter
and constructor failure; failure on undeletable/inherited credentials; no permission
for an uncleared or mismatched signer; repeated source/approval checks; reintroduction
rejection; parent approval preservation; continued fake-signer usability; no credential
in engine evidence. A fake Git process rejects any credential-bearing child environment,
and an actual harmless local Node child verifies absence. Existing exact-release tests
use credential-free environments for injected signers; early-read traps remain.

No real credential is accessed, no public signer is instantiated and no Galileo
transaction is signed or submitted during correction validation. The final committed
candidate is reviewed with `--review-only`; this does not authorize future execution.
