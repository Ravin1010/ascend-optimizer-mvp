# Final Galileo deployment evidence

Galileo entry-and-allocation validation deployment successfully completed.

Status: **33/33 canonical successful transactions**, actor nonces **0–32**, Stage-2 resolution **EXACT_INTENT_REPLAY_CONFIRMED**. This documentation freeze grants no transaction permission.

## Identity and lineage

Repository: Ravin1010/ascend-optimizer-mvp. Chain: 0G Galileo, chain ID 16602. Approved deployer: 0x3e094d9068b48850f09Fc7cc70A7E24E5ed0442a.

| Identity | Frozen value |
|---|---|
| Original deployment source | 47c1123a84123a969d1ef7b8399c4788db278c2f |
| Stage-1 recovery source | d76f56dc3049a9ee08b9cfd1c27d18c5ff85fd69 |
| Successful Stage-2 source | 0d3a3d567ae5f08e9054097710fd783d838f8cbf |
| Stage-2 source branch | feature/galileo-recovery2-tooling |
| Stage-2 direct parent | d76f56dc3049a9ee08b9cfd1c27d18c5ff85fd69 |
| Stage-2 tooling SHA-256 | 010695198d71990cc348e6e09aafc75679cc56fc1ed9f42a4d89d341095b5709 |
| Plan fingerprint | 8bf82574f675e6ecff0278ae680f87dcaf9c3fb376714b6caf0c7f08714e333f |
| Artifact fingerprint | 1ff4199614bfd3a665ad99f38c0ed0b8be21c43640f28a81e402f7563ff450d1 |

Original execution confirmed steps 1–3. Stage-1 continued through step 23, then preserved a stopped nonce-23 intent without a recorded transaction hash. Stage-2 independently revalidated the 23-receipt prefix and replayed only the exact historical register0 request, then continued steps 25–33. Both predecessor files retain their original failure/pending markers. Stage-2 signed/submitted 10 new transactions; it did not retransmit steps 1–23. The historical Stage-1 stop cause remains unproven; this package does not claim expiry was proven.

| Journal | Source path | SHA-256 |
|---|---|---|
| original | galileo-local/final-galileo-receipts.json | e9e8a7b7c333e577dad322174662db20f8f94f836b55c731e3e9c5e8b946d111 |
| stage1 | galileo-local/final-galileo-recovery.json | 87fa795e04221724bbb6c8e7495c57f9907c49f580346257f5af29d76596e3fa |
| stage2 | galileo-local/final-galileo-recovery2.json | ee67047d21419b165e5946769f11e0b547a37d500e8b97c4afa5e19a16975637 |

The raw copies are byte-identical, not regenerated JSON. Source journals remain in galileo-local/ and are never edited by this freeze.

## Final accounting and state

All amounts below are integer wei unless identified as shares.

| Accounting item | Value |
|---|---:|
| Original starting wallet balance | 2109915999999853000 |
| Balance at Stage-2 start | 1946071775713125608 |
| Spend before Stage-2 | 163844224286727392 |
| Stage-2 gas/value spend | 19274416033712728 |
| Total cumulative gas/value spend | 183118640320440120 |
| Total native value transferred by actor | 10000000000000 |
| Total transaction gas cost | 183108640320440120 |
| Deployment-final wallet balance | 1926797359679412880 |
| Protected reserve | 421983199999970600 |
| Cumulative-spend ceiling | 262151789258744631 |
| Final vault idle | 6000000000000 |

Initial balance minus cumulative spend equals the deployment-final wallet balance. Spend is below the ceiling; reserve is satisfied. Allocation calls move vault-held assets internally and must not be counted again as actor transaction value.

StrategyManager and Vault owners are the approved deployer. Strategy count is 5. Validator totalDelegated is 1000000000000. Final pending/mined nonces are 33/33.

| Strategy | Active | Allocation input (wei) | Resulting vault shares |
|---|---|---:|---:|
| Native | true | 1000000000000 | 1000000000000 |
| Gimo | true | 1000000000000 | 1000000000000 |
| Jaine | true | 1000000000000 | 500000000000 |
| Oku | true | 1000000000000 | 500000000000 |
| Ascend | false | 0 | 0 |

Allocation input is not the resulting strategy share quantity, particularly for Jaine/Oku. There is no Ascend allocation. Deposit input is 10000000000000 wei; each of four allocation inputs is 1000000000000 wei.

## Planned deployed contracts

| Step | Logical name / artifact | Address |
|---|---|---|
| 1 | manager (StrategyManager) | 0x4D7C7286936325eE8b47DF7550Ce8475A7B358E7 |
| 2 | vault (AscendVault) | 0x9e00E6C4a3222CD016C95679f6FB5C965dC16523 |
| 3 | validator (Mock0GValidator) | 0x5c703372908ba956CFa2C4464fDfd05DDa4365B9 |
| 4 | nativeAdapter (Native0GStakingAdapter) | 0x13490b87030b31C5cD7D31408e59407B96e0a0Ec |
| 5 | gimoPool (MockGimoStakePool) | 0x164d402F95D95C034e87EfC376e6e9262118EC89 |
| 6 | gimoAdapter (GimoAdapter) | 0xB854a605367AA275A8DD30809B6AE269d6b8AA03 |
| 7 | w0g (MockW0G) | 0xe61AED57469976de6f3B859abaB1e85761bA83e6 |
| 8 | usdce (MockUSDCe) | 0x62Cb32546C1c843912434F238717bCf81e63c8e7 |
| 9 | factory (MockV3Factory) | 0x71A9986E3c84ca102CBA0db4B5f12c18fdCA0dD1 |
| 10 | pool (MockV3Pool) | 0x53817535BB23cBAd43E7eA2a2e937affD4490fB9 |
| 12 | npm (MockV3PositionManager) | 0x06acBb567dFee667af36a5d3E7aa82417e7Ff532 |
| 13 | v1 (MockV3RouterV1) | 0xee7Bab10B3c3991d407571bC585946e24a71dFd0 |
| 14 | r02 (MockV3Router02) | 0x9103816e5C0cCaec81b3156339D97392aBd24672 |
| 17 | jaineAdapter (V3LiquidityAdapter) | 0x78109Bc2f07Dd9B88a81681f27EcbD9168221478 |
| 18 | okuAdapter (V3LiquidityAdapter) | 0x55f0185f28b9B42A84Ad1E8e2Bb7DbB8a1cD92a7 |
| 19 | ascendW0g (MockAscendW0G) | 0xeB2E2e2E6862C4D5eB99031D1b1B50B3Ba9Bacfb |
| 20 | sourceCore (MockAscendSourceCore) | 0x08B1A935fecd2D172FCB383239cC48F8Bcccf70d |
| 21 | queue (MockAscendWithdrawalQueue) | 0x1b1035A8528bb8CF581d97EC7576eD551993f9ab |
| 23 | ascendAdapter (AscendProtocolAdapter) | 0x25339Ef4E45D9982B7c51631a5C48542210f90Ea |

Derived Gimo child st0G: 0x44b7B1358EE53FD3CfC98b63941Cb097Bb2Ecb93. It was created by the pool constructor and is **not** a twentieth planned deployment transaction. contracts.json includes runtime hashes and deployment transaction references for all 19 planned deployments, with child evidence separately.

## Fresh reconciliation

Verification block: 60458046, hash 0x34106b155f6e13c7b2ef398062a4d96ff628a7749549aa900382fd39346ce333, timestamp 1792158090. Freeze timestamp UTC: 2026-10-16T13:41:33.198Z. Current observed wallet balance: 1926797359679412880; pending/mined nonces: 33/33. Post-deployment external account activity detected: false. Deployment-final values remain distinct from current observations.

The committed verifyRecords() independently re-fetched every transaction, receipt and canonical block, checked exact bodies, CREATE addresses and gas/value accounting. verifyState() checked current ownership, registrations, configuration, runtime hashes and shares. Frozen artifact bytecode comparisons mask compiler-declared immutable ranges and pair them with exact recorded runtime hashes and configuration readbacks. Current read-only calls were sequential latest-state observations, anchored by the final verification block, not one atomic historical-state query. No credential was accessed; zero transactions were signed or submitted during the freeze.

## Scope and limitations

The evidence supports controlled 33-transaction execution, project contract deployment and StrategyManager/Vault configuration, mock Native/Gimo/Jaine/Oku allocation paths, inactive Ascend adapter deployment, deterministic final state and fail-closed recovery provenance.

- All external protocol dependencies used in this Galileo graph are mocks.
- No production deployment or production readiness claim.
- No live external-protocol integration, real Gimo staking, real Jaine liquidity provision or real Oku liquidity provision claim.
- No live Ascend allocation or Native 0G consensus staking claim.
- No withdrawal lifecycle, reward lifecycle or economic/yield performance proof.
- Ascend remains intentionally inactive with zero shares.
- Reconciliation is a sequence of read-only latest-state observations, anchored by the final verification block; it is not an atomic historical-state snapshot.

## Using this package

1. From this directory, run `sha256sum -c PACKAGE_SHA256SUMS.txt` to verify every packaged file except the checksum manifest itself. The checksum manifest is committed with the package.
2. Match each raw copy SHA-256 to manifest.json. JOURNAL_SHA256SUMS.txt uses original repository source paths; from a workspace retaining those immutable local journals, run `sha256sum -c docs/galileo-evidence/final/JOURNAL_SHA256SUMS.txt` at repository root. Raw copies make review possible without that workspace.
3. Read manifest.json for identities and claim scope; use transactions.csv for exactly 33 receipt rows and explorer links, contracts.json for runtime/deployment evidence, final-state.json for readbacks, and claim-to-proof-matrix.md for claim boundaries.
4. verification.json records the fresh credential-free read-only checks. Later chain state can evolve; the package preserves the recorded verification context and deployment-final accounting. It is not an instruction to execute, resume or broadcast.

CSV calldataHash is Keccak-256 of raw transaction calldata. Request fingerprints and journal/package file hashes use SHA-256. This is an evidence-only documentation commit; contracts, execution tooling, plan, artifacts and the capstone proposal are unchanged.
