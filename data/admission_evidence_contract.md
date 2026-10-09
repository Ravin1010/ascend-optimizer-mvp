# Per-capture technical-admission evidence — Iteration 14

Canonical dataset: `data/admission_evidence.csv`. One CSV row per point or explicit bound. Current committed baseline is headers only: zero captures and zero qualified positive support. No source references, historical market values or demo assumptions were converted into admission captures. The separate source registry remains a reference catalogue, not this dataset.

The strict loader is `admission_records.load_admission_records`; the provider is `admission_provider.RepositoryAdmissionProvider`. The amount-aware runner defaults to this provider when no explicit admission function is supplied. The legacy optimizer/API path is unchanged. Explicit Iteration 13 synthetic mode remains non-default.

## A. Canonical field dictionary

All columns are required in the header, in this order. Cells follow the requirements below. Examples are hypothetical syntax illustrations only, not repository captures.

| Field | Meaning | Cell required? | Illustrative example |
|---|---|---|---|
| evidence_id | Unique stable capture ID | Yes | EXAMPLE-001 |
| strategy_id | Frozen independent strategy | Yes | GIMO_STAKE_0G |
| chain_id | Strategy execution chain | Yes | 16661 |
| evidence_type | Point versus explicit bound | Yes | EXACT_POINT |
| admission_status | Captured assertion, not absence | Yes | SUPPORTED / UNSUPPORTED |
| amount_0g | Captured point quantity; optional sample quantity for bound | Point: yes | 200 |
| amount_usd | Optional value of amount_0g at captured valuation | No; requires valuation | 400 |
| scalar_headroom_0g | Explicit maximum additional native-token admission | Bound: at least one headroom unit | 500 |
| scalar_headroom_usd | Explicit USD headroom, not TVL | Bound: at least one headroom unit | 1000 |
| source_id | Identified capture source; not an implicit verification claim | Yes | EXAMPLE-SOURCE |
| source_role | Explicit strategy admission mechanism role | Yes | GIMO_PROTOCOL_ADMISSION |
| mechanism | What actually established admission | Yes | Verified deposit-limit read |
| evidence_class | Measurement/assumption class | Yes | LIVE_OBSERVED |
| observation_timestamp | When underlying state applied | Required for usable admission | 2026-01-01T00:00:00Z |
| retrieval_timestamp | When capture was retrieved | Required for usable admission | 2026-01-02T00:00:00Z |
| block_number | Optional on-chain block reference | No | 123 |
| block_hash | Optional 32-byte hex reference | No | 0x followed by 64 hex digits |
| config_identity | Opaque route/config identity supplied by capture | Required for usable current-route admission | deployment:example-1 |
| config_required | Whether the mechanism requires config binding | Yes; TRUE for current five routes | TRUE |
| tested_amount_0g | Optional explicit test amount, equal to amount_0g | No | 200 |
| tested_amount_usd | Optional tested amount valuation | No; requires native counterpart/price | 400 |
| valuation_price_usd | Explicit capture valuation when USD fields used | Conditional | 2 |
| capture_status | Capture completeness/source/config disposition | Yes | CAPTURED |
| notes | Capture qualifications/context | No | Manual capture qualifications |

Evidence classes: LIVE_OBSERVED, LIVE_DERIVED, HISTORICAL, MODELLED, STATIC_CONFIG. Capture statuses: CAPTURED, NO_FRESH_CAPTURE_SUPPLIED, SOURCE_UNVERIFIED, CONFIG_UNRESOLVED, INVALID. No UNKNOWN repository rows and no TTL-based STALE status.

Malformed schema, duplicate IDs, non-independent/unknown strategy, wrong chain, invalid numbers/timestamps/blocks, contradictory units or tested amount, absent source/mechanism/class and non-admission source roles raise SchemaValidationError. The provider treats a missing/malformed dataset as unusable and returns UNKNOWN with diagnostics; it never skips malformed rows to select optimistic support.

Missing observation/retrieval time or required config is retained as an explicit usability gap; these records cannot support admission, even if capture_status says CAPTURED. Non-CAPTURED statuses are also unusable. Timestamps require full timezone-qualified ISO syntax; retrieval cannot precede observation. Original timestamp strings remain distinct. No timestamp is synthesized and retrieval never refreshes observation age.

Numbers are finite non-negative decimal text; point/test amounts and supplied price must be positive. Exact matching uses decimal equality, not nearest-point tolerance. USD values require explicit price and exact unit consistency; USD-dependent lookup also requires candidate valuation consistency. Missing values remain blank, never zero. Bounds can be zero. Optional block references are not required if the source cannot supply them.

## B. Evidence types

| Type | Meaning | Matching/use rule | Does not prove |
|---|---|---|---|
| EXACT_POINT | Assertion for one exact native-0G amount | Same strategy, chain, config and decimal amount; optional tested amount must agree | Any smaller/larger amount, continuous capacity or exit liquidity |
| SCALAR_BOUND | Explicit additional technical-admission maximum/region | Same context; SUPPORTED within bound, UNSUPPORTED above a captured supported maximum | A bound inferred from observed TVL, quote size, deposit history or points |

An UNSUPPORTED scalar record rejects candidates within its stated region; it supplies no assertion above it. An explicit UNSUPPORTED point returns UNSUPPORTED. Absence/unusable/mismatched evidence returns UNKNOWN.

For USD-only bounds, the captured valuation converts the explicit bound to token quantity; this is unit conversion, not new capacity inference. Native-only bounds do not generate an invented scalar USD headroom. TVL, reserves, SourceCore NAV, sampled delegation depth and snapshot notes are never provider inputs for admission.

## C. Strategy/context requirements

| Strategy | source_role / required mechanism | Current capture state | Default positive result |
|---|---|---|---|
| Native | CONFIGURED_VALIDATOR_ADMISSION; configured validator/route | None | UNKNOWN |
| Gimo | GIMO_PROTOCOL_ADMISSION; staking protocol/contract | None | UNKNOWN |
| Jaine | REGISTERED_LP_ADMISSION; registered route admission, separate from quote | None | UNKNOWN |
| Oku | REGISTERED_LP_ADMISSION; registered route admission, separate from quote | None | UNKNOWN |
| Ascend | SOURCECORE_ADMISSION; SourceCore route | None; CLOSED gate | GATED |

All five current mechanisms are configuration-dependent. This is why config_required is TRUE; optional/unresolved identity cells are allowed only as unusable captures. The provider requires an explicit caller `config_identities` mapping. It does not derive validator/pool/fee/range/target identity from generic metadata, CSV notes or reference examples. Equality carries a binding but does not verify that an opaque identity is the actual registered deployment. Full Jaine/Oku reconciliation and runtime configuration acquisition remain later work.

## D. Production filtering, selection and conflicts

Production accepts structurally usable LIVE_OBSERVED, LIVE_DERIVED or STATIC_CONFIG claims. HISTORICAL is not current admission, regardless of retrieval date. MODELLED is usable only with explicit `allow_modelled=True` demo/test construction; it remains labelled MODELLED, never execution readiness or live proof.

Different classes are not assigned a universal quality rank. Matching claims must agree first: any SUPPORTED/UNSUPPORTED conflict (including point versus bound) returns UNKNOWN with IDs. Recency cannot override a contradiction. Among agreeing usable matches, choose exact point over bound, then newest observation timestamp, then lexicographically smallest evidence_id. Retrieval time is not a selection clock. Duplicate IDs always invalidate the dataset. Old contradictory captures must be explicitly resolved/withdrawn, not implicitly expired here.

Structural correctness and a matching claim are not a freshness validity verdict, source authenticity audit or live-capital suitability claim. Diagnostics explicitly say STRUCTURAL_CAPTURE_MATCH_NO_TTL_ASSESSMENT. No numeric age cutoff exists in this iteration.

## E. Provider and revalidation flow

Candidate -> metadata admission/gate -> reload canonical CSV -> strict structure validation -> strategy/chain/config/amount/valuation/capture/class matching -> conflict check/selection -> SUPPORTED / UNSUPPORTED / UNKNOWN -> candidate economics/execution -> identical selected-point lookup and comparison.

The provider reloads the file for every lookup, including revalidation. Removing, invalidating, changing disposition or changing selected capture provenance invalidates the selection. Failed revalidation retains diagnostic proposed selections but recommendation=null, as in Iteration 13. No retries, no optimistic fallback and no gate override.

Use `RepositoryAdmissionProvider(path, strategies=metadata, config_identities={...})` as the explicit provider. `run_amount_optimizer(..., admission_fn=None)` uses the canonical path with unresolved default config context; captures alone do not invent a runtime config binding.

## F. Repository-only baseline

`python -m src.ascend_optimizer.amount_demo` uses this repository provider, committed demo economics, assumed USD 1/0G, 1000 0G and 90 days. No quotes/collectors/RPC calls occur without supported admission.

| Profile | Supported positive strategies | Allocation | Idle | Reason |
|---|---|---|---|---|
| Conservative | None | None | 100% | No captures; Ascend CLOSED |
| Balanced | None | None | 100% | No captures; Ascend CLOSED |
| Aggressive | None | None | 100% | No captures; Ascend CLOSED |

`--synthetic-support` remains explicit artificial Iteration 13 demo mode, not a repository/live provider mode.

## G. Synthetic tests and contract compatibility

Temporary hypothetical records verify: exact 200 0G only; explicit 500 0G bound; rejection above 500; wrong chain/strategy/config; conflicting claims; missing observation/config; modelled opt-in; native validator binding; Ascend gate; record removal/change during selected revalidation. No test capture is appended to the repository CSV.

Schema 1.3 remains unchanged except additive optional `admission_evidence.capture` and `diagnostics` fields. Capture exposes the validated canonical fields. Existing admission fields and result meanings remain intact. TypeScript represents the capture fields; API pass-through is unchanged. Whole-portfolio compliance, execution readiness and proof remain unassessed/not established.

Deferred: trustworthy capture acquisition/source verification, actual registered route identity, freshness expiry policy, and the other frozen portfolio/cost/risk/LP-stress gaps. No fresh data, timestamps, block references, capacity or live proof were generated.

## Validation results

- Evidence/provider tests: 56 passed.
- Evidence plus existing amount-aware tests: 83 passed (all 27 Iteration 13 tests retained).
- Full Python suite: 252 passed, with one existing Gimo pandas FutureWarning.
- API/subprocess contract tests: 7 passed.
- TypeScript typecheck and production build: passed.
- Repository-only three-profile comparison: no support/allocations, 100% idle, Ascend GATED.
- git diff --check: passed.
