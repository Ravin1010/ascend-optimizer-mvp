# Iteration 17 — historical capstone deployment recovery audit

Accepted baseline: `cd92cb957ebcd0d24637347875b822fe108e6bc6`.
Audit performed 2026-10-09. Machine-readable register and pinned Git inventory:
[`data/deployment_recovery_audit.json`](../data/deployment_recovery_audit.json).

**Overall verdict: NO_RECOVERABLE_CAPSTONE_DEPLOYMENT.** Every core component and
all five strategy routes are **NOT_FOUND** as actual public capstone deployments.
Implementation, protocol references, mock fixture deployments and registration
code exist. No actual capstone contract address/receipt/registration was recovered.
This is bounded to accessible evidence, not proof that no private deployment ever
occurred. No canonical runtime config was promoted and no admission evidence added.

## A. Historical search coverage

| Source area | Scope searched | Relevant findings |
|---|---|---|
| Current tree | All 123 tracked paths at accepted head; local non-dependency project files | No extra untracked deployment/config/receipt artifacts |
| Full commit history | All 304 reachable commits, including complete tree/blob history; zero merge commits | 365 unique textual file versions; all scanned for component/deploy/register/address/transaction/network terminology |
| Deleted historical files | Every historical tree plus `git log --all --diff-filter=D --summary` | No deleted-file events or historical-only paths; old versions of surviving files were still scanned |
| Local recovery objects | All local reflogs; `git fsck --full --no-reflogs --unreachable` | One extra commit `15909a34` has exactly the accepted Iteration 10 `ff7c269` tree. Four unreachable staging/frontend tree fragments contain only already-scanned blobs. 305 accessible commit identities total |
| Branches | Fetch all advertised heads; `git ls-remote --heads --tags origin`; GitHub branch collection | Only local/remote `main`; no accessible stale/feature/merged branch refs or additional history |
| Tags/releases/PRs | Local tags, advertised remote tags, GitHub releases and all-state PR collection | All empty. Tag REST fetch was tool-rejected; Git tag inventory and ls-remote establish no tags |
| Runtime-evidence commits | Complete diffs and trees of all ten requested commits | Diagnostics, demo assertions, types, UI/CSS; no deployment or registration proof |
| Documentation/config history | 34 README versions; 11 strategy CSV versions; 15 source-registry versions; 2 Hardhat/package versions; 2 LP planner versions; contracts/fixtures/frontend/config history | External protocol constants and future deployment parameters; no project manifest/receipt/exported capstone address set |
| Address/transaction search | All 365 versions, including references and tests | 36 unique 20-byte address literals: 21 protocol/sample references, 15 synthetic/sentinel values; no literal `0x` 32-byte tx hash. Unprefixed 64-hex tokens only occur as 14 provenance content hashes in runtime config JSON |
| Deployment artifact paths | Historical deploy scripts, deployments, broadcast, Ignition and environment paths | None ever tracked in accessible trees; no saved planner output |
| Public-chain verification | Only project-linked deployment candidates would be checked | No capstone candidate address/tx to verify. No random alternative contract discovery or fresh RPC evidence was used |

The pinned scan preserves commit IDs, historical blobs, first-containing commits,
content hashes, every address occurrence and corpus digest. The term search is a
lead inventory, not automatic proof classification. The interpretation register
records the manual source/fixture review. Network values on protocol references
are **repository claims**, not fresh independent verification.

Coverage limitations: inaccessible deleted remote refs, personal wallets,
uncommitted laptop logs, external/private storage and unavailable generated logs
cannot be ruled out. No proposal file exists in any accessible tree; README and
runtime/config documentation were inspected. Dependency/build/cache folders are
excluded from the local working-file scan, not mistaken for persisted deployments.

## B. Core deployment matrix

| Component | Outcome | Deployed chain | Address | Tx/block/deployer | Strongest evidence found | Sources |
|---|---|---|---|---|---|---|
| AscendVault | NOT_FOUND | null/unknown | null | null | SOURCE_CODE_REFERENCE | `b3e1924` implementation; `test-contracts/AscendVault.test.js` local mocks |
| StrategyManager | NOT_FOUND | null/unknown | null | null | SOURCE_CODE_REFERENCE | `b616308` registry implementation; `4b2f51d` local registry tests |
| RewardAccounting | NOT_FOUND | null/unknown | null | null | SOURCE_CODE_REFERENCE | `a15eaa6` implementation; `e34d59b` local accounting tests |

No public constructor arguments, deployed core linkage or actual manager address
was found. `ethers.getSigners()`, `Factory.deploy()`, `registerStrategy()` and
`tx.wait()` inside Hardhat fixtures establish test behavior, not a reusable public
instance. Hardhat configuration has compiler/test paths, no configured public
network; package scripts only compile/test. Tests were not used to deploy anything
during this audit.

## C. Strategy recovery matrix

| Strategy | Outcome | Adapter recovered? | Registration recovered? | Actual route config recovered? | Deployed chain | Primary evidence / missing binding |
|---|---|---|---|---|---|---|
| NATIVE_STAKE_0G | NOT_FOUND | No | No | No | null/unknown | `9c2e84b`: validator constructor; `6a1d2ef`: Mock0GValidator fixture. Actual validator/adapter/core binding absent |
| GIMO_STAKE_0G | NOT_FOUND | No | No | No | null/unknown | `bff4f84`: stakePool/st0g/referral inputs; `a735da2`: mock pool/st0G and test referral `ascend`. Public constructor/registration absent |
| JAINE_LP_0G_USDC | NOT_FOUND | No | No | No | null/unknown | `c68a33b` wrapper plus shared V3 mocks/preflight. No actual pool/token order/fee/spacing/ticks/sqrt bounds/target/adapter registration |
| OKU_LP_0G_USDC | NOT_FOUND | No | No | No | null/unknown | `2348fff` independent Router02 wrapper; `a70583f` NPM pin. Its own deployed range/pool/target/registration absent |
| ASCEND_STAKE_A0G | NOT_FOUND | No | No | No | null/unknown | `e287d3f` implementation; `353711d` MockAscendSourceCore/queue fixtures. Actual adapter/SourceCore/W0G/queue/core binding absent |

Intended current execution chain remains **16661**, but intended chain is not the
chain of a proven deployed capstone instance. Partial **protocol reference
components** do not warrant PARTIALLY_RECOVERED for a deployed capstone route.
Native samples were not selected as configured validators. Shared V3 test ticks
(-600,600), fee 3000 and target 5000 are mock inputs, not Jaine/Oku registrations.
No actual adapter deployment event, code check, constructor receipt, manager key
mapping or registration transaction was recovered for either wrapper.

Ascend's external SourceCore is not `AscendVault`. Earlier `AscendStakingAdapter`,
`A0GToken` and `RestakingAdapter` fixtures are reference/pre-launch/mock material,
not production deployment proof. Ethereum target references are dependencies.
Ascend remains CLOSED regardless of historical source implementation.

## D. Artifact register

The JSON contains **38 interpreted artifact groups**, each with exact commit/path,
Git blob ID, SHA256 and source URL. Every historical literal address is accounted
for; transaction/block fields remain null when unavailable.

| Artifact IDs | Evidence class | Network | Address/config content | Interpretation |
|---|---|---|---|---|
| CORE_VAULT / CORE_MANAGER / CORE_REWARDS | SOURCE_CODE_REFERENCE | Public deployed network unknown | Constructors, role/linkage interfaces | Source implementation only |
| LOCAL_CORE / LOCAL_NATIVE / LOCAL_GIMO / LOCAL_V3 / LOCAL_ASCEND | SOURCE_CODE_REFERENCE | Local Hardhat fixture only; public chain null | Mock deployments, registrations, withdrawal receipt parsing | No persisted public deployment or registration proof |
| REFERENCE_PRELAUNCH | SOURCE_CODE_REFERENCE | Local Hardhat fixture only | Reference a0G and generic restaking mocks | Superseded/reference architecture, not production Ascend deployment |
| NATIVE_IMPLEMENTATION / GIMO_IMPLEMENTATION / JAINE_WRAPPER / OKU_WRAPPER / ASCEND_IMPLEMENTATION | SOURCE_CODE_REFERENCE | Intended 16661 | Route constructor surface, immutable parameters | Missing actual deployed instance and manager binding |
| LP_PREFLIGHT | SOURCE_CODE_REFERENCE | Intended 16661 | Discovered pool and planned fee/ticks/sqrt/target; constructor args without vault | Planner does not deploy/register; no captured plan output found |
| TOOLCHAIN | SOURCE_CODE_REFERENCE | Local test context | Hardhat compiler/test paths, compile/test package scripts | No public network/deployer/deploy script |
| README_EXECUTION_CLAIMS | DOCUMENTATION_CLAIM | Intended 16661 | “Executable live path,” “verified” periphery, deployment instructions | Not deployment proof |
| METADATA_HISTORY | PROTOCOL_REFERENCE | Claimed 16661 | CSV external stake/token/factory/router/SourceCore references | `contract_address` is not a capstone instance export |
| REF_* records below | PROTOCOL_REFERENCE | Claimed 16661 or 1 | External protocol contracts, samples | No capstone ownership/deployment/registration proof |
| ASCEND_TARGET_RUNTIME_REFERENCE | RECORDED_RUNTIME_REFERENCE | Claimed Ethereum 1 | Source-registry historical probe identifiers | No committed response/block/receipt; dependency claim only |
| SYNTHETIC_ADDRESSES | SOURCE_CODE_REFERENCE | Synthetic/sentinel, public chain null | 15 zero/tiny/repeating-digit values | Tests/null address, not actual deployments |

### External reference address inventory

These are retained repository reference claims, not newly verified chain state.

| Role / artifact | Address | Claimed chain |
|---|---|---|
| W0G | `0x1cd0690ff9a693f5ef2dd976660a8dafc81a109c` | 16661 |
| USDC.e | `0x1f3aa82227281ca364bfb3d253b0f1af1da6473e` | 16661 |
| Gimo stake pool | `0xac06d1df23a4fa00981afac0f33a5936bd2135af` | 16661 |
| Gimo st0G | `0x7bbc63d01ca42491c3e084c941c3e86e55951404` | 16661 |
| Jaine factory | `0x9bdca5798e52e592a08e3b34d3f18eef76af7ef4` | 16661 |
| Jaine V1 router | `0x8b598a7c136215a95ba0282b4d832b9f9801f2e2` | 16661 |
| Jaine NPM | `0x8f67a30ed186e3e1f6504c6de3239ef43a2e0d72` | 16661 |
| Jaine quoter | `0xd00883722cecad3a1c60bca611f09e1851a0be02` | 16661 |
| Oku factory | `0xcb2436774c3e191c85056d248ef4260ce5f27a9d` | 16661 |
| Oku Router02 | `0x807f4e281b7a3b324825c64ca53c69f0b418de40` | 16661 |
| Oku NPM | `0x743e03cceb4af2efa3cc76838f6e8b50b63f184c` | 16661 |
| Oku QuoterV2 | `0xaa52bb8110fe38d0d2d2af0b85c3a3ee622ca455` | 16661 |
| Native network staking delay reference | `0xea224dbb52f57752044c0c86ad50930091f561b9` | 16661 |
| Native validator sample 1 | `0xec856948cf28a7c36e4c0d7877d027ba0a8af17d` | 16661 |
| Native validator sample 2 | `0x33f59323858ee0f29f5cc9e5abc05d42a424225f` | 16661 |
| Native validator sample 3 | `0x54c2a4ca7742175f297946c28beaa69540f88867` | 16661 |
| Native validator sample 4 | `0x77d9f3a83cc0af0a4f7e9dcd78ebae967248f494` | 16661 |
| External Ascend SourceCore/a0G | `0x4b3c2f55fa67679b382c979a082df1b32079b4cb` | 16661 |
| Ascend TargetCore dependency | `0xd46e464c82643e6937838a94d40fd8d014a2ea26` | 1 |
| Mellow MultiVault dependency | `0x0ff6ea4cad58b9e54535ae1ea2452cdbffb9bfab` | 1 |
| Mellow OFT dependency | `0xe42215bd71e190b3864267569c2f66077260eae4` | 1 |

There is no recovered capstone Galileo 16602 or Base 8453 address/transaction.
Those chain mentions occur in test/migration/KIV semantics. No address was moved
between Mainnet/Galileo/Base/Ethereum. No SourceCore queue address or actual LP
pool registration was recovered. Source review dates are not deployment dates.

## E. Requested runtime-evidence commit audit

Complete diff hashes and full SHAs are in the JSON. All ten contain neither
public deployment proof nor registration proof nor recorded public address/tx.

| Commit | Actual contents | Classification |
|---|---|---|
| b6c2ead9 | Python per-strategy headroom, constraints, JSON schema 1.2 | Optimizer diagnostics only |
| b4772590 | Demo/synthetic diagnostic assertions | Runtime tests only |
| 6174a6b9 | TypeScript diagnostic types | Contract types only |
| 217ca44c | Near-limit strategy UI | Presentation only |
| fbb6e66a | At-limit label rename | Presentation only |
| 400f68d9 | Headroom CSS | Presentation only |
| b790c2d8 | Demo headroom correction Native 40% / Gimo 60% | Runtime tests only |
| eb0eb0e1 | Profile allocation explanations | Presentation only |
| a756cc2d | Profile constraint CSS chips | Presentation only |
| dec71d72 | Pass optimizer data into explanation function | Presentation only |

Their ancestor trees include the same protocol constants and local fixtures,
not hidden receipts. Earlier Ascend “live probe” commits (`bc01873`, `a8d62df`,
`1a3dbc0`) implement/read external SourceCore/target dependencies; the registry
records identifiers, not a deployed capstone instance or transaction lifecycle.
“Deployment preflight” (`a96866b`) generates parameters without submission.

## F. Contradictions and stale references

| Subject | Claim A | Claim B / stronger boundary | Strength | Resolution |
|---|---|---|---|---|
| Public deployment vs fixtures | Implementation “executable/live”; fixture deploy/register calls | Local mock tests, no persisted public instance | Documentation vs source code | NOT_APPLICABLE — different layers, not a public deployment contradiction |
| LP registered alignment | README claims runtime and deployed adapter use same allocation basis | No deployed route recovered; planner selects observed pool/range/target | Documentation vs source code | STALE_REFERENCE — alignment unproven |
| Ascend “vault” | CSV SourceCore called vault; older locally issued reference a0G | External SourceCore differs from capstone AscendVault; production adapter only implemented | Protocol reference vs historical documentation | STALE_REFERENCE — not a conflicting capstone address |
| Oku NPM | Initially a constructor argument | `a70583f` pins protocol NPM, `d80c009` records periphery | Source/protocol references | MATCH — source evolution, not proven redeployment |
| Network roles | Current intended execution 16661; target references on Ethereum | Galileo/Base are test/KIV; no capstone deployed-chain evidence | Source/protocol references | MATCH — no cross-chain promotion |

No two actual public capstone instances were found to compare. Therefore no
UNRESOLVED_CONFLICT between deployed addresses is fabricated; insufficient proof
remains the blocker. Competing architecture/source versions are retained rather
than presented as a recovered deployment.

## G. Final recovery verdict and next branch

| Component / route | Verdict |
|---|---|
| Core/Vault | NOT_FOUND |
| StrategyManager | NOT_FOUND |
| RewardAccounting | NOT_FOUND |
| Native | NOT_FOUND |
| Gimo | NOT_FOUND |
| Jaine | NOT_FOUND |
| Oku | NOT_FOUND |
| Ascend | NOT_FOUND |

**NO_RECOVERABLE_CAPSTONE_DEPLOYMENT.** Next recommended branch: **prepare a new
deployment plan in the next explicitly approved iteration**. No plan, route
selection, deployment, admission capture or runtime config promotion is performed
here. If private receipts/manifests are later supplied, reassess them as new
recovery evidence before deciding to deploy.

## Validation and unchanged behavior

Reproduce the pinned history and provenance checks:

```bash
python tools/audit_deployment_history.py --check
python -m pytest -q tests/test_deployment_recovery_audit.py
python -m pytest -q
python -m src.ascend_optimizer.amount_demo --as-of 2026-10-09T12:00:00Z
git diff --check
```

- Focused audit tests: **17 passed**.
- Full Python suite: **354 passed**, one existing Gimo pandas FutureWarning.
- History/provenance replay: passed. Duplicate/weak-proof/network/sufficiency
  safeguards tested with synthetic assertions only.
- All production Python, contracts, frontend files and the frozen runtime config,
  strategy metadata and admission CSV are hash-pinned unchanged.
- No API/TypeScript change; no separate API/build/typecheck was needed or run.
- No Hardhat test deployment or public transaction was run during this audit.

Repository-only amount-aware baseline uses **no synthetic admission**. Demo
return/price inputs remain assumptions, not current live financial evidence.

| Profile | Amount-aware allocation | Idle | Reason |
|---|---|---|---|
| Conservative | None | 100% / 1000 native 0G | Empty admission captures; runtime configs unresolved |
| Balanced | None | 100% / 1000 native 0G | Same |
| Aggressive | None | 100% / 1000 native 0G | Same; Ascend also CLOSED |

Existing linear benchmark remains unchanged on the same synthetic economics:
Conservative Native 40% / Gimo 40% / idle 20%; Balanced Jaine 60% / Gimo 40%;
Aggressive Jaine 80% / Oku 20%. These demo results are regression checks, not
execution/admission proof. Selected-point revalidation and all earlier
configuration, decimal, freshness and amount-aware tests remain green.
