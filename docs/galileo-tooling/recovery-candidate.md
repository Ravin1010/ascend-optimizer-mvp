# Exact safe-stop recovery candidate

This is a separately reviewed recovery release for the three confirmed deployments
from source `47c1123a84123a969d1ef7b8399c4788db278c2f`. It grants no execution
approval. Implementation and tests use fake providers and local Hardhat only.

## Immutable original evidence

The original `galileo-local/final-galileo-receipts.json` is opened only for reading.
Its exact byte SHA-256 must be
`e9e8a7b7c333e577dad322174662db20f8f94f836b55c731e3e9c5e8b946d111`.
The policy additionally checks original source/execution/plan/artifact fingerprints,
actor, chain, start nonce, all original funding limits, exactly three ordered
confirmed receipts and the exact stopped `nativeAdapter` failure marker. Neither
normal resume validation nor the original failure marker is changed.

The public receipt fixture in `test-galileo/recovery-fixture.js` contains compressed
public evidence bytes for exact-hash tests. Tests materialize this evidence only in
temporary directories. It contains no credential or signed raw transaction.

## Dedicated non-archive verification

`recovery-validator.js` independently fetches all three transactions, receipts and
canonical blocks; compares exact deployment calldata, arguments, sender, nonce,
value, target and fees; verifies CREATE addresses and current artifact/runtime
hashes; and checks current ownership and configuration with `verifyState()`.
It recomputes every receipt cost and cumulative spend. Recorded wallet balances
must equal the original balance minus each cumulative spend. Current balance must
be exactly `2077236815942664428` wei, pending and mined nonces must both be 3, and
the predicted nonce-3 address must contain no code. No historical balance query
is used. Any different current balance, nonce, state, code or canonical evidence
stops recovery; there is no automatic reconciliation.

Normal `validateResume()` retains its historical balance verification and rejects
failed/ambiguous journals. Its default use by normal fresh and resume execution is
unchanged. The shared engine has one explicit validator injection seam for the
separate recovery path, whose production caller supplies only the validated
three-receipt recovery journal and reconstructed state.

## Review, authorization and future execution

The separate entrypoint is `scripts/galileo/recovery-run.js`. `--inspect` prints
local identity only. `--review-only` accepts the existing explicit identity,
nonce, fee-quote and short expiry arguments, with expected nonce 3 and the NEW
recovery source/tooling fingerprint. It never creates a recovery journal, loads a
signer or arms submission. It validates the complete prefix twice, budgets the
remaining graph using the original envelope, and freshly estimates and guards
step 4. It rejects existing recovery journals, locks and temporary files.

A future broadcast requires all three independent requirements: explicit
`--broadcast` plus `GALILEO_ALLOW_BROADCAST=YES`; matching exact NEW recovery HEAD,
`--expected-source`, `--approved-source` and
`GALILEO_USER_APPROVED_SOURCE`; and a provisioned signing credential. The recovery
branch must be `feature/galileo-recovery-tooling`, with the original deployment
source as its direct parent. Original deployment approval cannot authorize it.
All production recovery files participate in the tooling fingerprint.

The shared credential boundary still reads once, clears the execution environment,
verifies absence and signer identity, and repeatedly rejects reintroduced
credentials. Child Git environments remain credential-free. Permission checks
recheck source, approval, original evidence bytes and expiry before execution and
raw submission. The controlled provider retains one-attempt raw submission and
blocks node-account signing or sends.

Recovery persistence follows this strict order:

validation → exact approval → credential/signer boundary → step-4 state,
construction, fresh estimate and funding guards → durable pending intent → signing.

Store construction revalidates the original bytes, prefix and current state but
keeps `GALILEO_RECOVERY_V1` entirely in memory. `load()` returns a defensive clone;
`close()` before persistence is a no-op. Review never writes. Credential/signer,
approval, source, expiry and pre-intent step-4 failures create no recovery journal,
lock or temporary file.

The first genuine `nativeAdapter` / nonce-3 pending-intent save is the only point
that may create `galileo-local/final-galileo-recovery.json`. That save rejects
changed provenance, budgets, prefix or arbitrary first content, requires an exact
pending-intent shape with no transaction hash, rechecks execution permission and
original evidence, confirms target/lock/tmp absence, then acquires the existing
exclusive writer and atomically writes/fsyncs the intent. No signer call can
precede successful durable persistence. The shared engine's immediate pre-signing
permission recheck remains unchanged. A partial persistence failure is terminal;
no automatic retry is allowed.
The new journal retains original provenance/failure, original receipt evidence,
all original reserve/fee/cumulative limits, new source/tooling identity and the
non-archive validation method. It cannot overwrite the original or an existing
recovery target. Original bytes are checked again on every recovery journal save.
The shared engine starts with the three retained receipts and nonce 3, then runs
the unchanged remaining graph and per-step estimate, budget, runtime and readback
controls. It persists intent before signing and hash immediately after submission.
It does not redeploy the confirmed prefix or allocate to inactive Ascend.

This first recovery candidate deliberately does not accept `--resume`, including
resume of a subsequently interrupted recovery. Any new interruption or ambiguous
intent requires separate investigation and policy review; it is never retried
implicitly. No real recovery journal is created by this implementation iteration.

## Validation performed for this candidate

| Check | Result |
|---|---|
| Complete Galileo tooling suite | 249 passed, 0 failed: 148 existing + 64 recovery + 37 persistence corrections |
| Existing contract suite | 72 passed, 0 failed |
| Python application, result, asset, final-results and evaluation regressions | 238 passed, 0 failed |
| Normal confirmed-prefix/completed resume and ambiguity/reorg/duplicate checks | Passed in the complete Galileo suite |
| Shared local 33-step rehearsal and three-step recovery continuation | Passed; no duplicate prefix deployments, exact final idle |
| JavaScript syntax and whitespace checks | Passed |
| Original journal byte hash and original branch reference | Unchanged |

All test processes ran without the provisioned credential. No Galileo RPC was
called, no real recovery journal was created, and no Galileo transaction was
signed or submitted during implementation or validation. These are local test
results, not a GitHub CI claim.
