# Claim-to-proof matrix

Galileo entry-and-allocation validation deployment successfully completed.

| ID | Claim | Evidence source | Relevant step / transaction / readback | Result | Scope / limitation |
|---|---|---|---|---|---|
| A | Exact reviewed execution identity | manifest.json; raw/stage2-recovery-journal.json | Frozen source/tooling/plan/artifact pins | PASS | Identity evidence; approval lineage is preserved, not a new approval. |
| B | 33/33 canonical successful transactions | transactions.csv; verification.json | All 33 re-fetched successful canonical receipts | PASS | Proves recorded execution and current canonical inclusion. |
| C | Nonce sequence 0–32 | transactions.csv; verification.json | 33 unique hashes, consecutive actor nonces | PASS | Actor-specific sequence. |
| D | 19 project/mock contract deployments | contracts.json; verification.json | 19 DEPLOY receipts and runtime checks | PASS | Derived Gimo child is recorded separately. |
| E | Native registration active | final-state.json | [24: register0](https://chainscan-galileo.0g.ai/tx/0x328e1c1521d64c0760cab3928645c044fed4f8c888c49d37a3a1407488ce4830); exact registration readbacks | PASS | Mock adapter configuration. |
| F | Gimo registration active | final-state.json | [25: register1](https://chainscan-galileo.0g.ai/tx/0xe1774125cea3c296b3c6525292a19a330840cc3ea3c91a38552ed3a7a5d3d644); exact registration readbacks | PASS | Mock adapter configuration. |
| G | Jaine registration active | final-state.json | [26: register2](https://chainscan-galileo.0g.ai/tx/0x893a9086d1cbcb8104d368a41ee2e85be3348758180248cb085a928436b11163); exact registration readbacks | PASS | Mock adapter configuration. |
| H | Oku registration active | final-state.json | [27: register3](https://chainscan-galileo.0g.ai/tx/0x8440c5d0dd7eeb04c3a165a7c0c61c9e79e4129cca18111e4ec6e24ec4b3943b); exact registration readbacks | PASS | Mock adapter configuration. |
| I | Ascend registration inactive | final-state.json | [28: register4](https://chainscan-galileo.0g.ai/tx/0x25cbe12682ee56714fca5170bf63880f3ff2e162c97b790bba905d81a6cd7a27); active=false | PASS | Adapter deployed; no Ascend allocation. |
| J | depositNative completed | transactions.csv; final-state.json | [29: deposit](https://chainscan-galileo.0g.ai/tx/0x43bdee02536f16e875da439236be065ce693ee60d8466c879a19709927cf7c5c); value=10000000000000 wei | PASS | Test native value; final idle is after allocations. |
| K | Native allocation completed | transactions.csv; final-state.json | [30: allocate0](https://chainscan-galileo.0g.ai/tx/0x1038a82eadcbd083f9870f22224945a24d6b0549a6aeee6d24e70e9677b4e4f7); input=1000000000000 wei | PASS | Input amount differs from V3 resulting shares. |
| L | Gimo allocation completed | transactions.csv; final-state.json | [31: allocate1](https://chainscan-galileo.0g.ai/tx/0x44b4d80c8270b6fbac22c4845ae8c54dd6252cf4de58697063e8ca3d9b4f67e0); input=1000000000000 wei | PASS | Input amount differs from V3 resulting shares. |
| M | Jaine allocation completed | transactions.csv; final-state.json | [32: allocate2](https://chainscan-galileo.0g.ai/tx/0x332ea3095176fbe73333954fba88639a69e6d2d04263b9fc9ca0009c665efdb7); input=1000000000000 wei | PASS | Input amount differs from V3 resulting shares. |
| N | Oku allocation completed | transactions.csv; final-state.json | [33: allocate3](https://chainscan-galileo.0g.ai/tx/0x54327f10b25568ba8cc12d4b3ad5fbb0dd7e54db7f246d090c2f7460a04c552d); input=1000000000000 wei | PASS | Input amount differs from V3 resulting shares. |
| O | No Ascend allocation | transactions.csv; raw/stage2-recovery-journal.json | Exact frozen 33-step graph; final Ascend shares=0 | PASS | Claim limited to this graph and observed final state. |
| P | Final Native shares | final-state.json | 1000000000000 | PASS | Contract accounting shares, not yield or market value. |
| Q | Final Gimo shares | final-state.json | 1000000000000 | PASS | Contract accounting shares, not yield or market value. |
| R | Final Jaine shares | final-state.json | 500000000000 | PASS | Contract accounting shares, not yield or market value. |
| S | Final Oku shares | final-state.json | 500000000000 | PASS | Contract accounting shares, not yield or market value. |
| T | Final Ascend shares = 0 | final-state.json | 0 | PASS | Contract accounting shares, not yield or market value. |
| U | Validator delegation | final-state.json | Mock0GValidator.totalDelegated=1000000000000 | PASS | Mock validator accounting; no consensus staking proof. |
| V | Final vault idle | final-state.json | idleBalanceOf(actor, zero asset)=6000000000000 wei | PASS | Current readback corroborates completed graph. |
| W | Final reserve satisfied | manifest.json; verification.json | 1926797359679412880 >= 421983199999970600 wei | PASS | Deployment-final wallet balance. |
| X | Predecessor journals preserved | JOURNAL_SHA256SUMS.txt; raw/; verification.json | Exact original and Stage-1 byte hashes unchanged | PASS | Original stopped/pending markers retained. |
| Y | Stage-2 exact-intent replay provenance | manifest.json; raw/stage2-recovery-journal.json | [24: register0](https://chainscan-galileo.0g.ai/tx/0x328e1c1521d64c0760cab3928645c044fed4f8c888c49d37a3a1407488ce4830); historical requestHash pinned | PASS | No duplicate steps 1–23; signing permission is not inferred from receipts alone. |
| Z | Proof limitations | README.md; manifest.json | All external dependencies are mocks; Ascend inactive | PASS | No production/live integration, withdrawal, reward or performance proof. |
