# Admission freshness and configuration validity — Iteration 15

This is an optimizer operational policy, **not a protocol stability guarantee**.
The canonical CSV remains headers only. No live evidence or actual runtime route
identity was acquired or certified. The legacy optimizer/API path is unchanged.

## Centralized policy

`src/ascend_optimizer/admission_validity.py:DEFAULT_POLICIES`, version
`ADMISSION_VALIDITY_V1`, keys `(source_role, evidence_class, evidence_type)`.

| Source role | Evidence class | Type | Maximum observation age | Production usable | Rationale |
|---|---|---|---|---|---|
| CONFIGURED_VALIDATOR_ADMISSION | LIVE_OBSERVED / LIVE_DERIVED | EXACT_POINT / SCALAR_BOUND | 300 seconds | Conditional | Short operational decision-to-execution budget for dynamic admission |
| GIMO_PROTOCOL_ADMISSION | LIVE_OBSERVED / LIVE_DERIVED | EXACT_POINT / SCALAR_BOUND | 300 seconds | Conditional | Same dynamic-admission budget; TVL is not headroom |
| REGISTERED_LP_ADMISSION | LIVE_OBSERVED / LIVE_DERIVED | EXACT_POINT / SCALAR_BOUND | 300 seconds | Conditional | Separate admission assertion; does not validate quote freshness |
| SOURCECORE_ADMISSION | LIVE_OBSERVED / LIVE_DERIVED | EXACT_POINT / SCALAR_BOUND | 300 seconds | Conditional; Ascend gate remains CLOSED | Dynamic admission; never gate clearance |
| All above | MODELLED | Both | 300 seconds in explicit demo/test mode | No | Model assumption, not qualified production support |
| All above | HISTORICAL | Both | No current-admission policy | No | History is not current admission regardless of age |
| All above | STATIC_CONFIG | Both | NO_VALID_POLICY | No | Existing mechanism cannot distinguish immutable permission from dynamic remaining headroom |
| Any unlisted key | Any | Any | NO_VALID_POLICY | No | Fail closed rather than infer policy |

The five-minute window is a deliberately short, centralized operational budget,
not an empirical guarantee or a measured protocol limit. A fresh record can still
be wrong or cease to describe admissible headroom. Production use also requires
qualified capture status and explicitly verified current configuration context.

Custom policy maps are injectable for deterministic tests; they are not data-derived
fallbacks. Earlier matching-only tests use an explicitly labelled long synthetic
window so their amount/conflict assertions remain independent of expiry.

## Validity states and time

| State | Meaning | Runtime admission consequence |
|---|---|---|
| VALID | Applicable policy, captured source, amount and verified config checks pass | Captured assertion/bound can apply; conflicts still fail closed |
| STALE | Observation age exceeds policy | UNKNOWN for positive and negative assertions |
| CONFIG_MISMATCH | Evidence/runtime route identity or chain disagrees; evidence config explicitly unresolved | UNKNOWN |
| AMOUNT_MISMATCH | Exact native amount or USD valuation context differs | UNKNOWN |
| SOURCE_UNVERIFIED | Capture source, runtime config verification or production class unusable; also unresolved conflicting assertions | UNKNOWN |
| MISSING | Required capture/context absent, malformed dataset, or future observation | UNKNOWN |
| POLICY_UNDEFINED | Structurally present claim has no applicable validity rule | UNKNOWN |

POLICY_UNDEFINED is the sole additional state: absence of a defensible policy is
not missing capture data and is not proof of staleness. Historical/modelled
production rejection remains SOURCE_UNVERIFIED, with a specific class reason.

The core requires timezone-aware explicit `as_of`; no wall clock is read inside
provider/validity/search. `age = as_of - observation_timestamp`. Retrieval is
preserved provenance and never an age or selection clock. Age <= 300 seconds is
valid; age > 300 is stale. Future observation fails closed, with zero clock grace.
CLI `--as-of` accepts an explicit timestamp; absent CLI input resolves UTC externally.

Example observation `2026-01-01T00:00:00Z`, retrieval `00:00:01Z`:
- As-of 00:04:59: VALID.
- As-of 00:05:00: VALID.
- As-of 00:05:01: STALE.
- Same old observation retrieved at 00:05:00: still STALE at 00:05:01.
- As-of before observation: MISSING / FUTURE_OBSERVATION.
- Missing observation: MISSING; no trustworthy age can be computed.

Assessment fields: state, as_of, original observation/retrieval timestamps, age,
maximum age, source role/class, config identity, exact decimal candidate native/USD
identity, policy version, reason/details, runtime config verification state/source.
Provider records additionally identify evidence ID and captured assertion. Missing
capture values remain null, never fabricated. Configuration/source/class checks
can reject independently of age. Admission assertion and validity are separate.

## Runtime configuration

`RuntimeConfigContext(strategy_id, chain_id, config_identity, verification_state,
verification_source)` must be supplied by qualified caller state. Production uses
only `VERIFIED` plus a nonempty verification source and exact matching context.
Caller declarations are not independently authenticated by this module.
Legacy `config_identities` remains accepted but cannot alone certify verification.
Nothing derives identities from notes, samples, source labels, TVL or captures.

| Strategy | Required binding | Current default context | Consequence |
|---|---|---|---|
| Native | Configured validator/delegation route | Unresolved | UNKNOWN |
| Gimo | Actual staking contract/route | Unresolved | UNKNOWN |
| Jaine | Registered adapter/pool/fee/range/target identity | Unresolved; not discovered here | UNKNOWN |
| Oku | Its separate registered route identity | Unresolved; not discovered here | UNKNOWN |
| Ascend | Actual SourceCore route | Unresolved; CLOSED | No positive allocation |

Missing runtime/evidence identity => MISSING; unequal identity => CONFIG_MISMATCH;
unverified context => SOURCE_UNVERIFIED. A fresh timestamp never fixes these.
Config contexts remain mutable at the provider boundary so revalidation can observe
an explicitly changed caller context; no acquisition service is implemented.

## Matching, conflicts and revalidation

Canonical decimal exact matching remains unchanged. Scalar-bound exceedance is
not AMOUNT_MISMATCH: a valid supported maximum yields UNSUPPORTED above its bound.
A stale maximum yields UNKNOWN instead. USD-only bounds compare USD directly.

Only individually VALID assertions participate in current conflict resolution.
All relevant rejected/stale records remain in `validity_records` and diagnostics.

| Assertions | Current result | Diagnostics |
|---|---|---|
| Fresh support + fresh unsupported | UNKNOWN | Explicit conflict; both assessments retained |
| Fresh support + stale unsupported | SUPPORTED | Stale contradictory assertion retained |
| Stale support + fresh unsupported | UNSUPPORTED | Stale contradictory assertion retained |
| Both stale | UNKNOWN | Both stale assertions retained |
| Config mismatch | UNKNOWN | CONFIG_MISMATCH independently of age |
| Wrong exact amount | UNKNOWN | AMOUNT_MISMATCH; no nearest point |

Agreeing valid claims retain point-before-bound, newest observation, then smallest
ID precedence. Retrieval does not change selection. Duplicate/malformed datasets
remain unusable in their entirety. No universally ranked evidence classes.

`run_amount_optimizer(..., as_of=..., revalidation_as_of=...)` supports distinct
explicit times; omitted revalidation time repeats the candidate time. Providers
can also receive a fixed constructor `as_of`. Each selected positive point reloads
captures and reassesses config/expiry. Expiry or config change invalidates the
recommendation: outcome SELECTED_REVALIDATION_FAILED, recommendation null, no retry.
A later still-VALID assessment may have a different age/time: those assessment
fields alone do not imply changed economics/capture. All other existing evidence,
quote, admission and economics comparisons remain in force.

## Contract and scope

Schema 1.3 receives only optional `admission_evidence.validity` and
`validity_records`. TypeScript represents these additive fields. No rendering or
API route change. Recommendation/readiness/proof remain distinct. Admission
VALID does not establish execution readiness or transaction proof.

LP quote TTLs, registered-route acquisition/binding proof, valuation/oracle/cost
freshness, whole-portfolio state, risk redesign and proposal work remain deferred.
LPs still require separate candidate-specific quotes; admission freshness cannot
make those quotes fresh or establish registered configuration alignment.

Repository-only baseline at fixed `2026-10-09T10:00:00Z`: Conservative, Balanced and
Aggressive all have no supported positives and 100% idle. No capture rows added.

## Validation

- Focused validity/config tests: 44 passed.
- All evidence/amount-aware tests: 137 passed (66 existing evidence and 27 existing amount-aware tests retained).
- Full Python suite: 306 passed; one existing Gimo pandas FutureWarning.
- Python result/serialization subset: 26 passed.
- Actual API contract tests: 7 passed.
- TypeScript typecheck and production build: passed.
- Fixed-time repository-only baseline: 100% idle in all three profiles.
- git diff --check: passed.
