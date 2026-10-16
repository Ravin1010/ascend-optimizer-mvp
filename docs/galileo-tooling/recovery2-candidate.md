# Stage-2 Galileo recovery candidate

This candidate is a new child of the already-used Stage-1 source
`d76f56dc3049a9ee08b9cfd1c27d18c5ff85fd69`, on
`feature/galileo-recovery2-tooling`. It does not rewrite either execution source
or grant permission to transact. Implementation and validation use public receipt
fixtures, fake providers and in-process Hardhat only; no Galileo RPC is invoked.

## Why another recovery stage exists

The original deployment confirmed steps 1–3. Stage-1 confirmed steps 4–23,
including all 19 planned deployments, then retained a stopped `register0` intent
at nonce 23 without a transaction hash. Read-only reconciliation found no mined
nonce-23 transaction and no pending-nonce evidence across five new blocks. The
unsigned request was reconstructed exactly, but this cannot prove it was never
signed or submitted. Review expiry is consistent with the stop and remains
unproven: step-23 block timestamp 1792149632, permission expiry threshold starting
1792149657, expiry 1792149662, first known stop observation 1792149674. No pending
persistence timestamp or original thrown guard exception was retained.

Both old journals are immutable evidence, opened only for reading:

| Evidence | Path | Exact SHA-256 |
|---|---|---|
| Original deployment | `galileo-local/final-galileo-receipts.json` | `e9e8a7b7c333e577dad322174662db20f8f94f836b55c731e3e9c5e8b946d111` |
| Stage-1 recovery | `galileo-local/final-galileo-recovery.json` | `87fa795e04221724bbb6c8e7495c57f9907c49f580346257f5af29d76596e3fa` |

Stage-1 must retain exactly 23 confirmed receipts, nonces 0–22, last step
`ascendAdapter`, original provenance and funding limits, the preserved nonce-23
intent, and its exact STOPPED failure marker. The Stage-2 validator independently
refetches every transaction, receipt and canonical block; checks exact request
fields and accounting; verifies CREATE addresses and current runtime hashes for
all deployments and the pool-created token; and uses the committed `verifyState`.
It does not need historical balance trie state.

## Exactly two allowed modes

`EXACT_INTENT_REPLAY` requires pending/mined nonces 23/23, balance exactly
1946071775713125608 wei, strategy count zero, Native inactive/unregistered, zero
vault idle and all five shares, and zero validator delegation. Current ownership,
runtimes and every other prefix readback must match. The only allowed nonce-23
request is reconstructed from the frozen plan and ABI:

- Target StrategyManager `0x4D7C7286936325eE8b47DF7550Ce8475A7B358E7`.
- Sender `0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a`, chain 16602, nonce 23, value 0.
- Native registration with the original adapter, cap, 5000 bps and active/async flags.
- Gas limit 182778 and gas price 8000000014 wei, with no substitution.
- Calldata hash `0xc565e52633af0f99716ce6b73be4ff7f31ca2ad9fb9755c90909e402189aa9a1`.
- Request hash `3706666393264b23ac829814f9f8c1612c5405cfe6b4aa7792c0e3919ca8ca05`.

The calldata fingerprint is **Keccak-256**, matching the committed tooling and
frozen value (the request called it “SHA-256 / committed calldata hash”). The
request fingerprint is SHA-256 of the committed JSON serialization, and journal
fingerprints are SHA-256 of exact bytes. No hash or gas-value search is used.

Fresh estimation must fit the historical limit including the committed 20% gas
margin. Quote must be at most 4000000007 wei and within the fresh external quote
limit; current base fee cannot exceed the preserved price. Affordability uses the
fixed historical gas fields even when current quotes decrease. There is no
modified replacement transaction.

`EXACT_MINED_ADOPTION` requires pending/mined 24/24 and exactly one actor nonce-23
transaction found by a complete canonical full-transaction block scan from block
60440605 through the latest validation snapshot. Fetches are bounded to six
parallel read-only requests. The transaction must match every preserved request
field, successful canonical receipt and exact Wallet fee-envelope semantics.
Native must be the sole registration with exact configuration and active=true;
vault idle/shares and delegation remain zero. Balance must equal the step-23
balance minus the actual receipt cost. The appended receipt is marked
`ADOPTED_EXACT_HISTORICAL_INTENT`; nonce 23 is never signed by this path.

Pending 24/mined 23, any other nonce state, missing/multiple/different candidates,
failed/reorged receipts, drift or different balance all stop. A transition from
replay to exact adoption during any pre-signing recheck follows adoption instead
of signing. A reviewed adoption that disappears or changes canonical identity
stops. Full state/evidence validation follows the final estimate immediately
before the last synchronous permission check and signer call.

## Authorization, persistence and continuation

`recovery2-run.js --inspect` prints local identity only. `--review-only` performs
readiness checks and returns `RECOVERY2_READ_ONLY_REVIEW_PASSED`, selected mode,
nonce, funding/fee/expiry values and remaining graph. It never loads a credential,
arms submission or creates evidence. Expected nonce is 23 for replay or 24 for
adoption; a newly observed exact adoption can supersede a reviewed replay.

Future broadcast requires explicit `--broadcast`, `GALILEO_ALLOW_BROADCAST=YES`,
matching NEW Stage-2 HEAD / expected source / approved source / external
`GALILEO_USER_APPROVED_SOURCE`, and the signing credential. Neither predecessor
source can authorize this candidate. Branch and direct parent are mandatory.
The existing one-use credential boundary is reused through a dedicated Stage-2
approval wrapper, retaining cleanup, credential absence checks, signer identity
and credential-free child environments. The existing controlled transport still
allows only one raw submission attempt and blocks node-account signing/sending.

The third journal is `galileo-local/final-galileo-recovery2.json`, version
`GALILEO_RECOVERY2_V1`. Store construction validates both predecessors and current
mode, then keeps all state in memory. It creates no journal, lock or tmp. Review
and credential failures never materialize it. In replay mode the first durable
save is exactly the nonce-23 historical pending intent without a transaction
hash, followed by an immediate permission/state recheck before signing. In
adoption mode the first save may contain 24 confirmed receipts and the exact
adoption marker only after approval, signer boundary and revalidation.

The new file preserves both predecessor hashes, sources, fingerprints, failure and
pending markers, exact public historical request, all 23 immutable receipts,
original budgets, Stage-2 identity and the initial validation snapshot. Every save
repins both old byte hashes and protects provenance, confirmed prefix and limits.
No overwrite is allowed, and an uncertain/failed persistence or submission is not
retried. Sanitized phase codes identify validation, approval, signer boundary,
ambiguity checks, estimation/fees, intent persistence, pre-sign permission,
submission, receipt, state verification and shared-engine failures. They contain
no key, signed raw transaction, environment dump or raw stack trace.

After confirmed replay or exact adoption, the unchanged shared engine receives
24 verified receipts and starts at step 25 / nonce 24: Gimo, Jaine, Oku and
inactive Ascend registration; deposit 10000000000000 wei; four allocations of
1000000000000 wei; final idle 6000000000000 wei. No prefix transaction or Ascend
allocation can be sent. Original initial balance 2109915999999853000, reserve
421983199999970600, fee ceiling 8000000014 and cumulative ceiling
262151789258744631 remain fixed; new spend starts at 163844224286727392.

Stage-2 `--resume` is deliberately rejected. Any later stop preserves all three
journals and requires separate investigation. Normal fresh/resume behavior,
Stage-1 validation and its no-resume policy remain unchanged. All six Stage-2
production modules are included in the tooling fingerprint.

## Validation scope

Dedicated tests cover exact journal/provenance pins, both modes and their negative
cases, immutable request reconstruction, gas/fee bounds, canonical adoption,
late races, deferred persistence, credential isolation, authorization and the
controlled transport. Two full local rehearsals combine immutable public prefix
fixtures with local contracts at the same deterministic addresses. A test-only
adapter maps local chain/block identities; every actual test transaction ends at
in-process Hardhat. Replay sends nonce 23 once; adoption sends only nonces 24–32.
Both reach 33 receipts, four active mock strategies, inactive Ascend and exact idle.

This remains mock-only entry/allocation validation. It proves no live external
protocol integration, withdrawals, rewards, consensus staking or production
readiness. No real Stage-2 journal or Galileo transaction is created by this work.

Local regression results for this candidate: 375 Galileo tooling tests passed
(148 original, 101 Stage-1/recovery correction, 126 Stage-2), 72 contract tests
passed, and 238 relevant Python regressions passed. Both full local Stage-2
rehearsals passed, as did the existing shared-engine 33-step rehearsal and normal
resume/ambiguity regressions. JavaScript syntax and whitespace checks passed.
These are local results; no GitHub CI result is claimed.
