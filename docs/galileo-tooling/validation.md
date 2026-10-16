# Galileo tooling implementation and dry preflight — no broadcast

Date: 16 October 2026. Branch: `feature/galileo-deployment-tooling`.
Parent/main synced and verified at `d4fdf20bfe24ddf8c46c470a7c7bfc463d88a653`.
Accepted technical/result freeze: `4a280b90c6c39555b99658ee7855c6bd1f3bbba2`.
Initial working tree was clean. No merge to main, deployment, public signing,
transaction broadcast, wallet funding, real private-key access or protocol approval
was performed. All transaction execution in tests used local Hardhat 31337.

## Implementation

- Separate Cancun/0.8.24/optimizer-200 config, isolated cache/artifacts, empty
  public-network accounts. Frozen root config and Solidity remain unchanged.
- Ordered symbolic deployment/configuration/allocation graph, explicit branches,
  secret-free configuration, fixed mock amounts and validator-dependent Native LIVE
  values. Five IDs use ethers.id; LP routes have distinct adapters/router modes.
- Read-only RPC allowlist, actual chain-ID guard, current block observation,
  pinned dependency reads, optional code hashes and relationship checks, public
  balance/manager estimate path, explicit unresolved future-state blockers.
- No silent LIVE/MOCK fallback. No default approved Native validator/amount or
  Ascend confirmation. Ascend registration is inactive, with no executable
  activation step. Canonical optimizer gate remains CLOSED.
- Default preflight never reads GALILEO_PRIVATE_KEY. Broadcast requires both the
  explicit flag and acknowledgement, then encounters an intentional release seal.
  Public execution/signing is not implemented in this preflight-only release.
- Transaction-free resumable plan/evidence with source/config/graph/tooling
  fingerprints and overwrite refusal. Public receipt resume is rejected, not
  falsely represented as implemented. Future receipt fields are documented.
- Explicit proxy transport support through pinned https-proxy-agent 5.0.1;
  no proxy values or raw secret-bearing errors are logged.

## Validation actually run

| Check | Result |
|---|---|
| npm ls --depth=0 | Passed; declared packages resolved |
| Isolated compile | 45 Solidity files compiled successfully, Cancun |
| Original root Hardhat suite | 72 passing, 0 failing, approximately 4 seconds |
| Same existing suite against isolated Cancun artifacts | 72 passing, 0 failing, approximately 4 seconds |
| New tooling suite, final run | 24 passing, 0 failing, approximately 1 second |
| Mock graph rehearsal | 33 local transactions; 19 deployments, 9 configuration, 5 interactions |
| Rehearsal readbacks | Five registrations; four positive allocations; separate V3 token IDs; Ascend inactive/zero; native idle 0.0006; accounting unconfigured |
| JavaScript syntax checks | Passed for isolated config and runner modules |
| git diff --check | Passed |

Tests cover default non-broadcast mode, no secret getter access, missing
acknowledgement, unconditional release seal, forbidden signing/submission RPCs,
wrong chain before further reads, unresolved LIVE selections, missing amounts,
unconfirmed Ascend, funding/cap validation, unknown config fields, exact graph/IDs,
resume mismatches, dependency/readback failures, public insufficient balance,
and refusal of public-chain local rehearsal.

Existing root dependency versions were preserved. The new direct proxy dependency
is pinned and a package lock is added. Generated build/cache files are ignored.
No new lint framework was added; this repository has no root lint script.

Supplemental Python result replay commands were attempted but could not start
because this session's Python environment lacks `requests`. They are not reported
as passing tests, and no accepted result was regenerated. This is outside the
required contract/tooling test set; frozen paths are checked unchanged directly.

## Read-only Galileo results

Command:

```bash
node scripts/galileo/run.js --preflight --out galileo-local/final-plan.json
```

Captured full plan: [preflight-plan.json](preflight-plan.json).
Chain ID 16602; block 60373346, timestamp 1792117069, hash
`0x33f6ecbb545ddf630c65329b18c52f562c0594a448f864bfe68a8905f3568234`.
Exit 0: inspection completed, NOT broadcast approval. Planned MOCK graph is
19/9/5 transactions. Actual submitted transactions: zero. Deployed addresses and
transaction arrays are empty, with symbolic references for future deployments.
Manifest source SHA is the parent and explicitly records tracked local changes;
the tooling hash captures the implementation used before this branch commit.

Expected blockers: no public wallet/balance assessment, remaining constructor and
allocation live estimates unavailable until future state exists, release seal.
No signer was supplied or requested. No funding sufficiency claim is made.

Supplemental command used `--inspect-candidates`; summary is
[candidate-check.json](candidate-check.json). It remains separate from the MOCK
selection. Ascend candidate checks failed at `currentEpoch()` at pinned block
60373147 (`CALL_EXCEPTION`). Independent read-only corroboration returned:

- Same queue/currentEpoch at `latest`: successful, 318.
- Same call at block 60373147: RPC -32000, missing trie node / state unavailable.

This demonstrates a historical-state availability hurdle at the official RPC,
not a confirmed protocol ABI mismatch. The strict check failed closed and did not
silently switch to latest-state reads. A future LIVE-readiness review needs a
reliable pinned-state RPC/snapshot strategy and must repeat all dependency checks.
No new protocol identity approval, W0G verification promotion or live eligibility
is inferred from these observations. An earlier Node transport attempt also
failed before proxy support; it submitted no transaction.

## Boundaries and disposition

Native LIVE still needs selected-validator operational/ABI approval, current
minimum/forwarding/fee readbacks, explicit amount/cap/funding and code pins.
Ascend LIVE still needs protocol vault/share identity and positive-path confirmation.
Gimo/Jaine/Oku remain explicit mocked external protocols. Mock public setters and
minting are unsuitable for real capital; no withdrawal/reward lifecycle is proved
by this entry-only plan. The existing intended Mainnet architecture and canonical
production 100%-idle state are not changed or reconfigured.

`contracts/`, `src/`, `frontend/`, `data/`, `results/`, existing contract tests and
root Hardhat configuration remain byte-for-byte unchanged against the parent.
No Google proposal or accepted result artifact was edited.

Tooling disposition: **READY FOR BROADCAST-READINESS REVIEW**. This is not
permission to broadcast. Live confirmations, public funding assessment, estimates,
release-seal/executor review and any Ascend test-instance activation remain future
review requirements. No public deployment or CI-success claim is made here.
