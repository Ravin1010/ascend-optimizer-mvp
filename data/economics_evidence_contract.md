# Economics evidence contract — Iteration 19

Version `ECONOMICS_EVIDENCE_V1`. Implementation:
`src/ascend_optimizer/economics_evidence.py`. Canonical envelopes are
`strategy_return_evidence.json`, `lp_quote_evidence.json` and
`lifecycle_cost_evidence.json`, each `{schema_version, kind, records}`.
**All three record lists are empty.** No current return history, market quote,
cost measurement, timestamp, block or deployed configuration was acquired or
backfilled. Existing collector implementations and historical tracker claims
are acquisition leads, not silently qualified records. JSON is used because
embedded streams, quote context and provenance are structured; decimal amounts
and values should be stored as strings to preserve exact candidate identity.

The capstone does not require or plan public deployment. Canonical runtime
configurations remain UNRESOLVED, admission captures remain empty, and Ascend
remains CLOSED. Economic evidence cannot promote runtime configuration, provide
technical admission, attest risk/stress, or establish public deployment proof.

## Common record fields

Every key in the Python `RETURN_FIELDS`, `QUOTE_FIELDS` and `COST_FIELDS` sets
must be present. Optional information uses explicit JSON null; unknown keys are
rejected. Loader envelopes validate identity uniqueness. Provenance includes:

| Field | Meaning / requirement |
|---|---|
| evidence_id / quote_id | Unique stable evidence identity; content fingerprint detects replacement even if identity is reused |
| strategy_id | One of the five frozen independent strategies |
| evidence_class | Original observation/derivation/history/model/static/missing class; normalization preserves all contributing classes |
| source_id, source_role, source_verified | Traceable source and economic role; explicit caller-attested source qualification, never inferred from the class or a successful quote |
| observation_timestamp | Actual observation time, timezone-aware; never replaced by retrieval time or now |
| retrieval_timestamp | Actual retrieval time, timezone-aware, not before observation |
| period_start/end | Optional paired ordered measurement period, mandatory for holding-period metrics |
| block_number/hash | Optional actual block provenance, never synthesized |
| chain_id | 16661 when supplied; mandatory for nonmissing LP quotes; Ethereum backing is not a separate return stream |
| amount_0g/usd | Optional exact applicability notional; mandatory 0G amount for nonmissing quotes and amount-dependent costs |
| config_context | Explicit market/evaluation binding string or null; never a generated VERIFIED runtime identity |
| capture_status | CAPTURED for observations/derivations/history; SYNTHETIC for MODELLED; STATIC for STATIC_CONFIG; MISSING for MISSING |
| scenario_id | Required for MODELLED records and must match explicit synthetic invocation |
| notes | Derivation, limitations, source URL/file/commit and unresolved assumptions; no automatic provenance repair |

Observed, derived, historical and quote-derived records require both real
timestamps. Modelled records need no observation timestamp. MISSING records
cannot carry a numeric value. No timestamps or values are fabricated by loaders.
`source_verified` is an evidence ingestion assertion, not an automatic external
audit; supporting URLs/raw captures must accompany future acquisition.

## A. Return-evidence contract

Allowed return classes: LIVE_OBSERVED, LIVE_DERIVED, HISTORICAL, MODELLED,
STATIC_CONFIG, MISSING. Static fee metadata is usable as metadata, whereas
STATIC_CONFIG alone cannot establish a current projected base return.

| Metric | Meaning | Unit | Allowed evidence classes | Normalization rule |
|---|---|---|---|---|
| exchange_rate | Redeemable underlying value per receipt share | 0G_PER_SHARE | All return classes | At least two compatible observations: APY = (last/first)^(365/elapsed days) − 1 |
| gross_apy | Explicit annual expected return basis | FRACTION_PER_YEAR | All return classes | Horizon return = (1 + APY)^(H/365) − 1 |
| gross_apr | Annual simple rate with explicit compounding convention | FRACTION_PER_YEAR | All return classes | APY = (1 + APR/n)^n − 1; n recorded, never inferred |
| lp_fee_apr | LP fee APR/proxy, separate from quote loss | FRACTION_PER_YEAR | All return classes | Same APR conversion; observational proxy derivation belongs in provenance |
| validator_yield_benchmark | Representative validator sample, not a configured-validator return | FRACTION_PER_YEAR | All return classes | Annual APY benchmark; production rejects Native sample role |
| holding_period_return | Observed or assumed return across the supplied period | FRACTION | All return classes | Annualize its exact period then convert to H; extrapolation is explicit |
| protocol_fee_rate / commission / fee_rate | Fraction of positive income payable as the specified yield fee | FRACTION | All return classes | Deduct once only for GROSS_BEFORE_FEES; never again for NET_OF_PROTOCOL_FEES |
| incentive_apy | Additional economically realizable annual incentive stream | FRACTION_PER_YEAR | All return classes | Add to base APY using the existing MVP approximation only with explicit realization evidence |
| realized_incentive | Evidence-supported redeemable income for exact amount and period | USD | All return classes | Add only for matching amount and horizon; no interpolation/scaling |
| points | Non-financial credits/points | NON_FINANCIAL | All return classes | Excluded from financial return |

Each return record also supplies `fee_basis`, `fees_embedded`,
`return_components`, `incentive_policy`, `economically_realizable` and
`compounding_periods_per_year`. Exactly one base metric is selected (or one
compatible rate history). Multiple base streams fail as ambiguous/double-counted.
Rate histories must share source, context, fee basis and embedded components.
Annualized endpoint growth is a projection assumption, not a guarantee of future
yield; LIVE observations remain observations even when the formula is derived.

The normalized result reports strategy, H, expected gross income/return,
additional fee deduction, already embedded fees, incentives, original classes,
full provenance, qualification, assumptions/method and reasons. No normalizer
sets an allocation gate. Negative returns and negative net profit are allowed;
net APY is null when a loss of at least 100% makes real annualization undefined.

`EXCLUDED_NO_REALIZABLE_EVIDENCE` explicitly excludes incentives: its zero
contribution is an exclusion policy, not a claim that missing observed incentives
are zero. `REQUIRE_REALIZABLE_EVIDENCE` fails when financial incentive evidence is
missing/unrealizable. Protocol fee basis UNKNOWN fails. Gross return requires one
explicit yield-fee record; zero fee metadata requires source-supported provenance.

## B. Strategy return matrix

| Strategy | Primitive return evidence | Fee treatment | Incentive treatment | Optimizer-facing result | Current limitation |
|---|---|---|---|---|---|
| Native | Validator benchmark or configured-validator economics when independently supported | Commission needs explicit gross/net basis; Native withdrawal fee is a separate lifecycle line | Excluded unless realized/redeemable evidence exists | Horizon income with benchmark/evaluation role exposed | No validator selected; no canonical rates/commission/withdrawal-fee measurement |
| Gimo | st0G redeemable 0G/share history | Exchange-rate economics require NET_OF_PROTOCOL_FEES; documented 10% metadata is retained, not deducted again | Separate stream only if realizable and not embedded | Endpoint-rate APY and H-income | No rate samples imported; metadata alone does not supply return history |
| Jaine | LP fee APR/proxy or explicitly modelled annual return | Explicit fee/NAV basis, independent quote economics | LP NAV fee growth is not a separate reward stream | H-return from fee proxy/model with method/provenance | Historical tracker values are not current; no registered range or bound quote |
| Oku | Its own LP fee APR/proxy/model | Same economic principles with independent venue/context | No duplicate fee-growth reward notification | Its own H-return, not copied Jaine return | No canonical current volume/liquidity/range return record |
| Ascend | SourceCore/a0G redeemable 0G/share history | Net rate embeds underlying fees/yield; metadata retained | Embedded Mellow/Symbiotic return counted once | Rate-derived H-income, even though allocation stays CLOSED | No canonical compatible rate history; economic completeness cannot open gate |

Future LP proxy acquisition may justify volume × pool fee / attributable
liquidity annualization, but must state interval, fee tier, attribution and range
assumptions. No such proxy calculation or current range claim is fabricated here.

## C. Double-count matrix

| Strategy / item | Potential double-count | Prevention |
|---|---|---|
| Gimo | Net st0G growth plus another 10% deduction | NET_OF_PROTOCOL_FEES implies no second deduction; exchange-rate gross basis rejected |
| Ascend | a0G growth plus embedded restaking APY | One base basis; incentive components cannot overlap embedded return components |
| LPs | NAV/fee APR plus the same separate reward stream | Explicit component sets; overlapping incentive components rejected; no reward notification changes |
| All | Quoted swap fee plus separate swap-cost line | Quote embedded_cost_types suppress duplicate components by rejecting double-counted evidence |
| All | Yield commission listed again as lifecycle cost | Commission/protocol_yield_fee/embedded_reward cost aliases rejected |
| Points/iAI credits | Non-financial credits treated as APY | Points excluded; financial incentives require explicit realizability |

## D. Quote evidence contract

Quotes use LIVE_OBSERVED, LIVE_DERIVED, HISTORICAL, MODELLED or MISSING.
They are **not technical admission or capacity evidence**.

| Field | Meaning | Observational quote? | Synthetic quote? |
|---|---|---|---|
| quote_id, strategy_id, venue | Independent Jaine/Oku identity and venue | Required | Required |
| chain_id | Intended observed/evaluation network | 16661 required | 16661 intended domain required; no public proof |
| amount_0g | Exact full candidate notional to which entry/exit leg estimate applies | Required | Required |
| amount_usd | Optional quoted valuation context; if supplied must equal candidate amount × valuation | Optional | Optional |
| direction / path | ENTRY or EXIT and full explicit path | Required | Required |
| token_in/out, fee_tier | Tokens and fee tier; must match expected context | Required | Required |
| market_context | Pool/reference parameters, including any modeled inventory/range assumptions | Required | Required |
| config_context | Bound observed market/evaluation configuration | Explicit string/null | Explicit scenario context |
| quoted_output / output_unit | Actual or assumed output of this leg, not full-position principal | Required | Required |
| slippage_rate | Candidate-notional fractional loss; provenance must explain price/fee basis | Required | Required assumed loss |
| observation/retrieval timestamps | Separate actual times | Required | Null allowed; scenario validity does not pretend time freshness |
| source/evidence_class | Common source metadata | Required | MODELLED + SYNTHETIC capture and scenario |
| configuration_binding | UNBOUND_TO_DEPLOYED_ROUTE or independently proven runtime binding | Explicit; observation alone remains unbound | SYNTHETIC_SCENARIO |
| quote_validity_state | Persisted value must be UNASSESSED; computed validity is separate | Required | Required |
| embedded_cost_types | Pool swap/other fees already represented by quote loss | Required list | Required list |
| notes | Provenance plus inventory/price/fee assumptions | Required field | Required explicit synthetic context |

Quoted outputs and slippage are recorded evidence, not mechanically substituted
for each other. Normalization applies recorded loss fractions to the exact
candidate principal. Future capture must preserve the loss computation's price
basis and explicitly enumerate embedded fee coverage. Missing amount-specific
quotes are not interpolated, scaled or replaced by success at another amount.
Entry and exit are both required; context includes token/fee/output units as well
as strategy, path, market and evaluation binding. Jaine and Oku remain separate.

## E. Quote validity and independent freshness

`DEFAULT_ECONOMIC_POLICIES` is intentionally empty. Central policy keys are
`(kind, source_id, metric/direction/cost_type)`; valuation uses
`('valuation', source_id, '0G_USD')`. Any supplied policy requires positive
`max_age_seconds` and a documented `rationale`. No policy copies the admission
300-second budget. Test-only 60-second budgets demonstrate expiry without
asserting a real market stability bound. No policy in this iteration qualifies a
current repository quote/return/price.

| Condition | Validity | Optimizer consequence |
|---|---|---|
| Exact amount/context and qualified policy/scenario | VALID | Economics may consume it; admission/risk remain separate |
| Different exact decimal amount | AMOUNT_MISMATCH | Reject; no tolerance or interpolation |
| Wrong strategy, direction, path, market, binding, token, fee or unit | CONTEXT_MISMATCH | Reject |
| Observation within a justified per-source policy | VALID | Observation may support economics; an unbound quote still cannot be current executable proof |
| Observation outside policy | STALE | Reject, including at selected-point revalidation |
| No quote policy | POLICY_UNDEFINED | Fail closed for current claims |
| No return/cost policy | NO_VALID_POLICY | Fail closed for current claims |
| Source not qualified | SOURCE_UNVERIFIED | Reject observation |
| Historical evidence in production | HISTORICAL_NOT_CURRENT | Reject current claim; explicit historical/synthetic evaluation may consume as history |
| Matching synthetic scenario in explicit synthetic mode | VALID | MODELLED economics only; no admission implied |
| Synthetic quote without matching explicit mode/scenario | SYNTHETIC_MODE_REQUIRED | Reject |
| Missing quote | MISSING | No positive LP economics |
| Future observation/retrieval | FUTURE_TIMESTAMP | Reject |
| Unbound observational quote in production | CONTEXT_MISMATCH | Does not describe a deployed/registered route |

## F. Lifecycle costs

Allowed cost classes: LIVE_OBSERVED, QUOTE_DERIVED, MODELLED, STATIC_CONFIG,
HISTORICAL, MISSING. Every cost has an identity, type, structure, value/unit,
optional exact amount and H, source/timestamps, valuation in normalized output,
and optional parent quote ID. MISSING never becomes zero. Any numeric zero must
be STRUCTURAL_ZERO with STATIC_CONFIG, qualified source and explicit basis.

| Cost type | Applicability | Fixed/variable structure | Evidence classes | Treatment |
|---|---|---|---|---|
| entry_gas | All five | FIXED_PER_ENTRY or amount-specific quote | Cost classes | Once per positive strategy lifecycle entry, never weight-scaled |
| exit_gas | All five | FIXED_PER_EXIT or amount-specific quote | Cost classes | Once per modelled full lifecycle exit |
| claim_gas | Native/Gimo/Ascend | FIXED_PER_EXIT or lifecycle | Cost classes | Required asynchronous lifecycle line, separate from exit gas |
| native_withdrawal_fee | Native | Fixed or amount-specific quote | Cost classes | Separate validator processing fee; never inferred from benchmark APY |
| protocol_entry_fee / protocol_exit_fee | All five | VARIABLE_BPS, fixed, amount-specific or supported structural zero | Cost classes | BPS × actual candidate USD principal / 10000, or full fixed charge |
| lp_swap_fee / additional LP execution cost | Jaine/Oku | Quote-derived or variable | Cost classes | Required fee coverage may be embedded in both validated leg quotes; duplicate cost lines rejected |
| bridge_cost | All frozen user-capital routes | STRUCTURAL_ZERO only when supported | STATIC_CONFIG only | No invented Ethereum bridge expense; canonical evidence still missing until zero basis is recorded |
| fixed_fee | Supported explicit evaluation stream | FIXED_PER_LIFECYCLE / ENTRY / EXIT | Cost classes | Apply once, not proportional to allocation weight |
| amount-dependent fee | Supported explicit evaluation stream | AMOUNT_DEPENDENT_QUOTE | Cost classes | Exact amount/context/H; parent quote validity required for QUOTE_DERIVED |

Required default coverage is entry/exit gas, protocol entry/exit fees and bridge
cost, plus claim gas on asynchronous routes and Native withdrawal fee. No global
zero defaults. All supplied extra cost lines also contribute. Test-only coverage
overrides require SYNTHETIC_EVALUATION_ONLY. Aggregate and component lines cannot
be mixed. Costs concern one modelled entry/hold/exit lifecycle at H, not an
assertion of actual exit transactions or liquidity availability.

USD costs retain their source value. Native 0G cost × supplied USD/0G valuation
converts to USD. Every normalized component preserves native amount, converted
USD, H applicability, evidence, fingerprint and full valuation provenance. A
MODELLED/user-override price requires matching synthetic mode/scenario; an
observed current price requires its own qualified source/timestamps/policy.
No numerical price silently certifies a reference valuation.

The objective remains expected horizon income minus protocol, management,
performance, quote losses and lifecycle costs. Management/performance rates are
explicit caller inputs retaining the existing convention; output records them.
Fixed cost is charged once per positive strategy candidate, not per weight unit.
Zero allocation requires no economic evidence and incurs no lifecycle cost.

## Optimizer boundary and reproducibility

`run_amount_optimizer(..., economics_fn=provider, economics_mode=...)` consumes
typed `EconomicPoint` values at the original exact Decimal candidate amount.
It retains the same grid, concentration/risk constraints, technical admission,
Ascend gate and selected-point revalidation. It does not alter LP stress math.
The same provider is called at the selected point, with later explicit as_of
when supplied. Full evidence content and identity are detached from mutable
providers before comparison; expiry, changed identity/source/context/value or
changed cost/valuation invalidates the recommendation. Repository-backed
economics reload records on lookup, without RPC/requoting.

Default repository admission uses the canonical empty economics provider. An
explicit custom admission provider with no economics_fn retains the pre-existing
scalar compatibility path for frozen tests/demo/benchmark callers; that path is
not newly qualified evidence and still exposes its unresolved provenance basis.
New economics verification supplies the provider and explicit evaluation mode.
Modelled economics never supplies admission, even if economically attractive.

`AmountCandidate.economics_evidence` is an additive internal amount-aware detail;
schema 1.3, legacy output semantics and frontend types are not changed. When
used, amount-aware cost_basis identifies CANONICAL_ECONOMICS_EVIDENCE_V1; without
it the existing scalar provenance-unresolved label is retained. The evidence
detail separately reports technical_admission NOT_ASSESSED, risk_stress
NOT_ASSESSED and public_deployment_proof NOT_ESTABLISHED.

Reproduce:

```bash
python tools/economics_preflight.py
python -m pytest -q tests/test_economics_evidence.py
python -m pytest -q
python -m pytest -q tests/test_result_contract.py
npm --prefix frontend run test:contract
python tools/audit_deployment_history.py --check
python tools/deployment_preflight.py
git diff --check
```

The Iteration 17 source hash for amount_optimizer.py is now replayed against its
historical accepted commit, preserving that audit as a historical fact. Its
evidence/config/admission hashes still guard unchanged working-tree records.
No historical audit/design dataset was edited to hide the authorized new path.
No Hardhat source/tests, deployment tooling, dashboard or proposal is modified.

Remaining acquisition: actual compatible rate observations with source/period
provenance; defensible return/quote/price freshness policies; independently
recorded lifecycle costs and true structural zeros; amount-specific market quote
captures and price-loss coverage. These are deployment-independent evidence
needs, not required future public deployment milestones.
