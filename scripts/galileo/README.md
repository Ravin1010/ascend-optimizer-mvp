# Galileo tooling — preflight only release

Baseline: `d4fdf20bfe24ddf8c46c470a7c7bfc463d88a653`.
Technical/result freeze: `4a280b90c6c39555b99658ee7855c6bd1f3bbba2`.
This isolated tooling does not change Solidity, optimizer policy, canonical
runtime/evidence, frontend, or frozen results. It is not deployment evidence.

## Commands

```bash
npm ci
npx hardhat compile --config hardhat.galileo.config.js
npx hardhat test --config hardhat.galileo.config.js --no-compile
npx hardhat test
node scripts/galileo/run.js --preflight --out galileo-local/plan.json
node scripts/galileo/run.js --preflight --inspect-candidates --out galileo-local/candidates.json
```

No private key is required or read. `GALILEO_RPC_URL` defaults to the official
HTTPS Galileo endpoint. Existing `HTTPS_PROXY`/`https_proxy` transport settings
are supported without logging their values. RPC URLs with embedded credentials
or queries are rejected. The Hardhat network has `accounts: []`.
`GALILEO_PRIVATE_KEY` is a reserved name for a future reviewed signer; do not put
its value in config, evidence or this repository. No `.env` file is loaded.

Default/`--preflight` uses an RPC method allowlist that excludes signing and
transaction submission. Unknown options fail. `--broadcast` without
`GALILEO_ALLOW_BROADCAST=YES` fails before network access. Even with both opt-ins,
**a release seal refuses broadcasting**: a public execution/signing engine is
intentionally not implemented in this iteration. This is stronger than a default
dry-run flag and requires a separately reviewed change before any broadcast.
The local rehearsal is test-only, never imported by the CLI, requires in-process
Hardhat chain 31337 and MOCK branches, and uses local generated test accounts.

## Compiler isolation

The frozen root configuration remains unchanged (Solidity 0.8.24, 200 optimizer
runs). The isolated config explicitly selects Cancun, supported by current 0G
deployment guidance, and writes separate ignored artifacts/cache. The pre-existing
artifact metadata observed during inspection used Paris. Do not mix build sets;
preserve the exact isolated compiler settings for future source verification.
No Solidity changes or dependency-version upgrades are introduced. A direct
`https-proxy-agent@5.0.1` dependency and npm lockfile make transport reproducible.

## Plan and branch selection

`mock-plan.json` explicitly selects Native MOCK and Ascend MOCK. It is a test
plan, not canonical strategy metadata. `plan.js` builds an ordered graph with
symbolic references, constructor arguments, factory/queue setup, router mock-token
funding, five registrations, one native deposit and four allocations. It never
auto-switches a failed LIVE branch to MOCK.

Native/Gimo/Ascend use their actual project adapters. The LP paths use separate
generic `V3LiquidityAdapter` instances: V1 for Jaine-style and Router02 for
Oku-style, sharing mock W0G/USDC.e/factory/pool/NPM. Mainnet-pinned wrappers are
not presented as Galileo deployments. Gimo's pool creates its token internally.
LP mocks use the accepted local fixture's synthetic bounds, raw-unit exchange,
18-decimal USDC.e and NAV; they are not real market/pool economics. Entry router
funding mints only mock USDC.e; no unbacked W0G mint is required by the plan.

Mock allocation is 0.0001 test 0G; funding 0.001; per-route cap 0.001 and registry
ceiling 5000 bps. The gas-budget value is a preflight budget, not a guaranteed
estimate. Unrestricted mocks are unsafe for real funds and can be interfered with
on a public testnet. No rewards or withdrawals are included in the graph.

Ascend is registered inactive and receives zero allocation. The plan merely
describes the two optional future operations (activation and allocation) as
`SEPARATE_REVIEW_REQUIRED`; no executable activation step exists. Its canonical
optimizer state stays INTEGRATED_GATED / CLOSED.

Expected gated graph counts (signed transactions, not internal CREATEs):

| Native | Ascend | Deploy | Configure | Interact | Total |
|---|---|---:|---:|---:|---:|
| LIVE | MOCK | 18 | 9 | 5 | 32 |
| LIVE | LIVE | 15 | 8 | 5 | 28 |
| MOCK | MOCK | 19 | 9 | 5 | 33 |
| MOCK | LIVE | 16 | 8 | 5 | 29 |

Optional separately reviewed Ascend activation/allocation adds two transactions.

## LIVE branch configuration — no approval fabricated

Provide a separate local JSON config via `--config`; never commit secrets.
Native LIVE requires explicit `validator`, `registry`, `amount0g`,
`depositCap0g`, positive integer-string `minShares`, `approved: true`,
`forwardingMode` (`CONSENSUS_THRESHOLD` or `BELOW_THRESHOLD_INTERACTION`),
`codeHash` and `implementationCodeHash`. These approval assertions require actual
human review; the runner does not create approval evidence. There is no default
validator or live amount. Funding must cover all planned amounts and Native's
5000-bps ceiling. Recheck minimum accepted delegation, actual operational state,
withdrawal fee and validator-specific restrictions. The preflight checks registry
lookup, bonded status, conversion, fee, forwarding threshold and beacon code pins.
Verified ABI/operational review remains a blocker even when reads pass.

The earlier observed forwarding threshold was about 1 test 0G, not the mock
allocation amount. Use a threshold-sized live amount only with explicit budget
approval and funds. Otherwise choose MOCK explicitly, or obtain specific approval
for the narrower claim: **real Galileo validator-contract delegation interaction
below the confirmed consensus-forwarding threshold**. Do not claim consensus
staking from receipt/share credit alone.

Ascend LIVE requires `sourceCore`, `w0g`, positive integer-string `minShares`,
`confirmed: true` and reviewed `codeHash`, `w0gCodeHash`, `queueCodeHash`,
`implementationCodeHash`. Protocol identity/route confirmation must explain stOG
versus a0G and expected positive deposit/request/claim behavior. Relationship,
implementation-code and queue reads are checked; positive-operation review stays
mandatory. `--inspect-candidates` reads the previously discovered candidate set
as diagnostics only, independent of the selected mock branch, without promoting
approval or adding a live dependency to the plan.

## Evidence, failures and resume

Preflight pins dependency reads to the observed block and writes a new JSON file
exclusively (refuses overwrite). It records source commit, dirty-tracked-file
state, chain/block/time, explicit composition, configuration hash, graph, readback
hashes and named blockers. There are no invented contract addresses or hashes:
future deployments remain symbolic references and `transactions` is empty.
Add public `deployer` and `user` addresses to check balances and estimate the
manager constructor. Private keys are not needed. Remaining constructors and
allocations depend on future state, so they remain explicitly unassessed until
local validation and subsequent per-step live estimates. A missing wallet is an
explicit broadcast blocker, not a presumed sufficient balance.

`--resume previous.json` accepts only matching source/config/version/chain and a
transaction-free preflight manifest. It refreshes observations into a different
output file. Transaction-bearing resume is rejected in this release. The manifest
lists the future receipt schema (hash/block/gas/price/events/readbacks/explorer/error)
but does not pretend to implement resumable public execution. A later executor
must verify every persisted receipt/code/owner before skipping any operation,
sequence pending nonces, enforce budgets, wait for receipts and stop on ambiguity.

`BLOCKED_FOR_BROADCAST` is expected for this preflight-only release. Exit 0 means
the requested inspection completed, not broadcast approval. Invalid config or a
failed check returns nonzero; RPC/setup errors return 1 with sanitized output.
STOP on wrong chain, missing branch/approvals, zero or changed dependency code,
relationship/identity/state mismatch, inadequate funds, failed estimates,
conflicting resume evidence, or unexpected mock mutation. Never silently fall back.
