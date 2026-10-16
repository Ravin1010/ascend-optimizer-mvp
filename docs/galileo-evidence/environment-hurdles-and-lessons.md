# Galileo Testnet Deployment — Environment Hurdles and Lessons Learned

## 1. Purpose of the Testnet Exercise

Deploying the optimizer/vault flow to 0G Galileo put the allocation path into an actual blockchain environment. Compilation and local Hardhat tests established important prerequisites, but did not establish how the deployment would behave with a public RPC endpoint, network confirmation delays, account nonces and operational authorization boundaries.

This exercise responds directly to the supervisor’s guidance that allocation should be put to test on testnet/mainnet and that environment-related hurdles, deployment/runtime failures and operational problems should be recorded. The emphasis here is on **testnet deployment/runtime hurdles**, their diagnosis and their engineering implications.

“Galileo entry-and-allocation validation deployment successfully completed.”

That scope is deliberately bounded. All external protocol dependencies in this graph were mocks; this was not a production deployment. The [frozen evidence package](final/README.md), particularly its [manifest](final/manifest.json), [transaction ledger](final/transactions.csv), [final state](final/final-state.json), [verification record](final/verification.json) and [claim-to-proof matrix](final/claim-to-proof-matrix.md), supports the completed execution and state claims below. Its three raw journals preserve the stopped prefixes and completed recovery. Earlier pre-journal credential and RPC diagnostic events are described from the operational history supplied for this retrospective; the frozen journals alone cannot establish their exact exceptions.

## 2. Final Outcome

The exercise completed **33/33 canonical successful transactions**, with nonce sequence **0–32** and **19 planned deployment transactions**. Five strategies were registered: Native, Gimo, Jaine and Oku active; Ascend inactive. `depositNative` completed, followed by four allocations. There was no Ascend allocation. The derived Gimo child token was not counted as another planned deployment transaction.

| Deployment-final measure | Recorded result |
|---|---:|
| Vault idle | 6000000000000 wei |
| Mock validator delegation | 1000000000000 |
| Cumulative gas/value spend | 183118640320440120 wei |
| Wallet balance | 1926797359679412880 wei |
| Pending/mined nonce | 33/33 |

Native and Gimo each ended with 1000000000000 vault strategy shares. Jaine and Oku each ended with 500000000000 shares; Ascend had zero. Each allocation input was 1000000000000 wei, so input amounts must be distinguished from resulting shares.

This result followed multiple fail-closed deployment/recovery stages, rather than one uninterrupted run. Fresh reconciliation at block 60458046 found the recorded final balance and nonces unchanged. These are frozen observations, not a claim that the account or chain can never change later.

## 3. Chronological Environment Hurdles

| Stage | Observed hurdle | Effect | Diagnosis / evidence | Resolution | Lesson |
|---|---|---|---|---|---|
| A — Initial credential/signer boundary | Credential availability/format or signer/deployer validation failed before execution. The retained history does not isolate one precise subcause. | 0/33 confirmed, zero signed/submitted; nonce stayed 0; no journal or uncertain transaction. | Pre-journal operational history; there is no receipt proving a pre-signing failure. | Improved credential isolation and exact signer validation; kept secrets out of subprocess environments. | Validate secret handling and signer identity before public transactions. |
| B — Three-step partial deployment | Execution stopped before Native0GStakingAdapter, after StrategyManager, AscendVault and Mock0GValidator. | Three confirmed receipts; nonces 0–2 consumed. | Original journal; public reconciliation found canonical receipts, pending/mined nonce 3 and no code at the next CREATE address. | Preserved the prefix and designed recovery instead of restarting. | A deployment is not atomic; reconcile confirmed chain state. |
| C — Historical RPC state | Normal resume validation encountered a missing-trie-node style failure because required historical archive state was unavailable. | Historical balance validation could not complete; this did not invalidate the prefix. | RPC diagnostic history; current canonical receipt/runtime evidence remained available. | Added a separate recovery-specific accounting/current-state validation path; normal resume stayed strict. | Provider capability affects recovery architecture. |
| D — Stage-1 registration stop | Recovery continued through step 23, then stopped at step 24, `register0`, nonce 23. | All 19 planned contracts deployed; 23/33 confirmed; durable intent but no returned hash recorded. | Stage-1 journal retained the intent and generic failure; public state showed nonce 23/23, strategyCount 0, no deposit/allocation. | Preserved evidence and diagnosed before considering further execution. | Retain sanitized phases and timestamps, not only a generic failure code. |
| E — Authorization timing | The stop timing was compatible with the review expiry threshold. | Possible permission rejection; causation remained unproven. | Historical timestamps below; pending-intent time and original exception were unavailable. | Classified as CONSISTENT_BUT_UNPROVEN; used a fresh, longer bounded window later. | Authorization duration must accommodate public-chain latency. |
| F — Nonce-23 ambiguity | A pending intent existed without a recorded transaction hash. | Signing or brief submission could not be excluded. | No mined nonce-23 transaction or pending-nonce evidence; 23 canonical receipts, nonce 23/23, zero registrations; exact request reconstructed. | Restricted Stage-2 to exact-intent replay or exact canonical adoption. | No recorded hash does not prove no submission. |
| G — Exact-intent continuation | Stage-2 validated nonce 23/23, zero registrations, historical identity and fresh estimate/fees. | Exact replay confirmed step 24; steps 25–33 then completed. | Stage-2 journal and final reconciliation; step-24 receipt details below. | Continued from verified state without duplicating steps 1–23. | Preserve valid work and constrain recovery to independently verified transitions. |

The three-step stop must not be described as a submitted step-4 transaction. The evidence established the confirmed prefix and absence of nonce-3 deployment code; it did not provide a step-4 transaction receipt. Likewise, the historical archive-state failure concerned the provider’s ability to answer a verification query, not a demonstrated contract failure. Recovery substituted canonical transaction/receipt accounting, runtime checks and exact current balance/state checks, without weakening ordinary resume validation.

The historical authorization timing was:

| Event | Unix timestamp |
|---|---:|
| Last confirmed block | 1792149632 |
| Permission rejection threshold | 1792149657 |
| Review expiry | 1792149662 |
| First known stop observation | 1792149674 |

Classification: **CONSISTENT_BUT_UNPROVEN**. Neither the pending-intent persistence timestamp nor the underlying thrown exception was retained, so this sequence cannot prove expiry caused the stop. A block timestamp also does not identify the exact wall-clock time of every off-chain operation.

The ambiguous request was deterministically reconstructed without searching for arbitrary gas values. Its SHA-256 request fingerprint matched the preserved intent exactly:

`3706666393264b23ac829814f9f8c1612c5405cfe6b4aa7792c0e3919ca8ca05`

Public observations supported the absence of a currently visible mined/pending nonce-23 transaction; they did **not** prove the request had never been signed or submitted. Stage-2 therefore allowed only replay of the same historical request, or adoption if that exact transaction appeared canonically. A modified replacement was not permitted.

Stage-2 selected exact replay. Step 24 confirmed as transaction `0x328e1c1521d64c0760cab3928645c044fed4f8c888c49d37a3a1407488ce4830`, in block **60456013**, using **147636 gas**. The [transaction ledger](final/transactions.csv) connects this receipt to the remaining registrations, deposit and allocations. The resolution was `EXACT_INTENT_REPLAY_CONFIRMED`.

## 4. What Local Testing Did Not Fully Expose

Extensive local tests remained valuable for checking contract behaviour and recovery invariants. The real Galileo exercise additionally tested RPC behaviour and archive-state availability, confirmation and block timing, authorization-window expiry, externally observable nonce state, partial-deployment recovery, and uncertainty between durable intent and a returned transaction hash.

It also required real wallet balance/gas accounting, execution against an actual network endpoint and operational credential boundaries. Local fixtures can model these conditions, but cannot establish every behaviour of a particular public provider or the elapsed duration of a public transaction sequence.

Local tests established deterministic application behaviour; testnet execution tested operational assumptions around that application behaviour. The lessons are complementary: environmental findings should become targeted tests and deployment checks, while deterministic local tests remain the foundation for interpreting unexpected network results.

## 5. Key Engineering Lessons

### 5.1 Treat deployment as a state machine

A deployment may stop after any transaction. Track confirmed transitions, the next intended action and uncertainty explicitly. Confirmed state must be reconcilable rather than assuming the whole graph succeeds atomically. Recovery here used separately reviewed paths; this does not imply unrestricted automatic resume is safe.

### 5.2 Never blindly redeploy after partial success

Starting again from transaction 1 could duplicate contracts, consume different nonces and break evidence continuity. Preserve canonical work and establish exactly what remains. The three-receipt and 23-receipt prefixes were useful state, not failed attempts to discard.

### 5.3 Durable intent before signing is valuable

The persisted intent established which request was about to be sent, allowing later deterministic identity comparison. However, intent persistence and receipt confirmation are different events. Retain sanitized phases and timestamps that distinguish permission checks, signing, submission and receipt verification without recording credentials or signed payloads.

### 5.4 Public evidence must override assumptions

Combine transaction receipts, canonical block hashes, nonces, runtime bytecode, state readbacks, request hashes and wallet accounting. Each constrains a different uncertainty. Neither a successful receipt alone nor an unchanged nonce alone proves the entire intended application outcome.

### 5.5 Authorization expiry is both a safety control and operational parameter

Bounded approval limits execution authority, but its duration must accommodate public-chain confirmations and repeated validation. Generate fresh windows for execution and stop when they are invalid. Lengthening a later window is an operational improvement, not proof of the historical stop’s cause.

### 5.6 RPC capability is an environmental dependency

Check required historical and current-state queries before deployment. A provider can serve canonical receipts yet lack historical trie data. Any alternative validation method needs explicit assumptions and equivalent evidence checks; silently bypassing a failed historical check would lose assurance.

### 5.7 Separate execution identity from development identity

Exact source commits and plan, artifact and tooling fingerprints identified which reviewed code produced the evidence. Later documentation is a separate activity and does not retroactively change execution identity. New recovery code required new review and approval rather than inheriting approval of an earlier commit.

### 5.8 Preserve immutable evidence across recovery stages

The original, Stage-1 and Stage-2 journals remained separate. Earlier stopped journals were not rewritten to look successful; their hashes and byte-identical copies remain in the frozen package. This preserves a traceable account of how completion was reached and what uncertainty existed at each boundary.

### 5.9 Test allocation outcomes, not only transaction success

Final verification checked registrations, active flags, shares, validator delegation and vault idle. In particular, Jaine/Oku input amounts differed from their resulting share amounts. Checking these outcomes showed that allocation was exercised, while avoiding an unsupported inference that transaction success proves rewards, withdrawals or economic performance.

## 6. Implications for Future Mainnet Deployment

The exercise identifies further deployment-engineering work; it does not establish mainnet readiness. Before any future mainnet deployment:

- Validate RPC/provider capabilities in advance, including recovery queries.
- Use sufficiently long but bounded authorization windows, with confirmation latency budgeted.
- Retain sanitized failure phases and timestamps across operational boundaries.
- Design prefix-aware deployment and recovery processes that safely tolerate repeated checks without blindly repeating confirmed transactions.
- Reconcile ambiguous transactions before any retry; do not infer safety from a missing hash.
- Verify runtime and state after every critical transaction.
- Maintain reserve floors and cumulative gas/value budgets.
- Independently confirm real protocol addresses and configurations.
- Replace mock dependencies with reviewed live integrations before making integration claims.
- Separately test withdrawal and reward lifecycles.
- Conduct another formal deployment review before mainnet.

Mainnet remains future/KIV unless separately approved. Public-testnet experience informs that review, but cannot replace integration validation or establish safety under different assets, protocols, provider behaviour and network conditions.

## 7. Scope of What This Testnet Exercise Proved

| Supported by Galileo evidence | Not established by this exercise |
|---|---|
| Controlled public-testnet deployment | Production readiness |
| 33-transaction execution | Mainnet safety |
| Project contract deployment | Live external-protocol integration |
| StrategyManager/Vault registration flow | Real Gimo staking |
| Mock Native/Gimo/Jaine/Oku allocation execution | Real Jaine/Oku liquidity provision |
| Inactive Ascend registration | Live Ascend allocation |
| Recovery from partial deployment | Native consensus staking |
| Final allocation state verification | Withdrawals or rewards |
| Actual Galileo gas/nonce/RPC operational experience | Economic/yield performance |

The key value of the Galileo exercise was not simply that all 33 transactions eventually succeeded. It exposed deployment-environment assumptions that local testing could not fully validate and forced the deployment process to handle partial execution, RPC limitations, authorization timing and transaction ambiguity safely. The final successful allocation state therefore provides both functional testnet evidence and concrete engineering lessons for any future mainnet deployment.
