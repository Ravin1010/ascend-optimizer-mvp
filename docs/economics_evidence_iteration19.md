# Iteration 19 — deployment-independent economics evidence foundation

Accepted baseline: `2cf76ba4c5b0b7b20c600f1433b73539ce473825`.
Exactly two coupled tasks were implemented: canonical strategy-return evidence;
canonical LP quote/lifecycle-cost evidence and amount-aware normalization.

The [evidence contract](../data/economics_evidence_contract.md) contains required
outputs A–F: metric/unit/normalization contract, five-strategy return matrix,
double-count matrix, quote field/validity matrices and lifecycle cost treatment.
[Reproducible results](../results/economics_iteration19_validation.json) separate
the canonical repository baseline from SYNTHETIC_EVALUATION_ONLY test replay.

## Implemented behavior

- Three canonical JSON evidence envelopes with strict fields, classes and units;
  exact decimal amounts; distinct actual observation/retrieval timestamps; no
  timestamp fallback. All canonical record lists remain empty.
- Return normalization supports APY/APR, explicit compounding, exchange-rate
  endpoints, holding-period returns, benchmark roles, fees and realizable
  incentives. Normalized/derived class and original provenance classes are both
  exposed. Missing return/fee basis fails instead of manufacturing income.
- Gimo net-rate yield is not reduced by the documented commission again.
  Ascend embedded Mellow/Symbiotic yield is counted once; matching return/incentive
  components are rejected. Points are excluded; LP fee APR and quote losses stay
  separate. LP NAV growth does not acquire a separate reward-notification path.
- Quote lookup is exact at each candidate amount, including entry and exit.
  Strategy/venue, path, pool/evaluation context, tokens, fee tier and output units
  must agree. Quote output/loss and embedded pool-swap-fee coverage are explicit.
  Unbound observational quotes do not become current executable route claims.
- Required lifecycle-cost coverage fails when absent. A zero requires a
  source-supported structural-zero record. Fixed entry/exit/lifecycle costs are
  paid once; variable bps and exact amount-dependent fees vary by amount.
  Native-unit conversion preserves the valuation source/class. Quoted swap fees
  cannot be charged again as a separate cost line.
- Default economic freshness policies are empty; no defensible numeric budget
  was acquired. Current return/cost claims fail NO_VALID_POLICY; current quotes
  fail POLICY_UNDEFINED. Admission's 300 seconds is never copied. Synthetic
  scenario validity and test-only expiry policies are explicit.
- Default repository runs use canonical economics. Explicit custom-provider
  scalar calls retain the frozen legacy/testing convention; they are not
  qualified current economic evidence. New evidence-backed evaluations require
  an explicit provider and matching economic mode.
- Selected candidates are evaluated again at their original exact amount.
  Evidence snapshots are copied before comparison, so mutable providers cannot
  rewrite earlier evidence. Changed identity, provenance, context, price, costs
  or quote expiry invalidates the recommendation. No live RPC requoting is added.

## G. Canonical repository baseline

Fixed `as_of = 2026-10-09T14:30:00+00:00`. Canonical non-demo snapshots and the
three empty economics datasets were used. Amount 1000 0G, H=90 days and USD/0G=1
are analysis parameters; **the price is a modelled placeholder, not qualified
observed valuation**. It supports no positive financial allocation. No synthetic
admission or quote provider was used for this baseline.

| Profile | Qualified return evidence | Qualified quote/cost evidence | Allocation | Idle | Main reason |
|---|---|---|---|---|---|
| Conservative | MISSING | MISSING | None | 100% | Unresolved runtime config and empty technical admission; economics also missing |
| Balanced | MISSING | MISSING | None | 100% | Same |
| Aggressive | MISSING | MISSING | None | 100% | Same; Ascend also CLOSED |

The baseline reports known token quantity/status, not an evidence-qualified
financial recommendation. Neither an idle mathematical result nor the price
placeholder establishes current valuation or measured economic completeness.

## H. SYNTHETIC_EVALUATION_ONLY verification

All scenario inputs reside in ephemeral tests. Saved results below are labelled
test results, not records in canonical return/quote/cost evidence. No fresh market
observations or blocks were invented. Test records exercising LIVE/HISTORICAL
classes are fabricated test fixtures with explicit synthetic notes, not captures.

| Case | Demonstrated result |
|---|---|
| Fixed cost once | Synthetic Native 10% annual return, H=365, price=1: 100 0G → $8 profit; 400 0G → $38. Both pay the same $2 fixed cost |
| Variable cost | 25 bps → $0.25 at 100 0G; $1 at 400 0G |
| Missing cost | Missing required exit-gas evidence excludes positive candidate |
| Structural zero | Explicit STATIC_CONFIG + qualified source + basis accepted; unlabelled/modelled zero rejected |
| Gimo fee | Assumed rate 1→1.1 over 365 days gives 10% APY; documented 10% commission metadata incurs no second net-rate deduction |
| Ascend embedded yield | Same endpoint calculation counted once; duplicate base/embedded incentive streams rejected; metadata gate remains CLOSED |
| Quote amount | 100 quote cannot serve 100.000000000000000001; AMOUNT_MISMATCH |
| Quote expiry | With a test-only 60-second observation policy, a later selected-point check fails when age exceeds budget |
| Synthetic quote | Matching scenario + explicit synthetic mode accepted; production or different scenario rejected |
| Modelled return | Cannot unlock production economics; economics cannot create technical admission |
| Amount-aware ranking | Exact amount-dependent cost penalty beyond 400 0G selects 40% without changing the grid |
| Selected evidence | Unchanged evidence passes; changed quote/return identity, source, context, amount or valuation fails closed |

Synthetic solver cases explicitly supply test-only admission support and unchanged
legacy risk coefficients. Success is economic/mechanical evaluation evidence,
not technical admission or actual execution proof. No stress/IL model, risk
scenario, whole-portfolio model or cash-deadline logic was redesigned.

## Validation

| Check | Result |
|---|---|
| Focused economics tests | 65 passed |
| Full Python regression | 481 passed; one existing Gimo pandas FutureWarning |
| Result contract/serialization suite | 10 passed; additive amount-aware evidence additionally round-tripped in focused tests |
| Actual API/contract tests | 7 passed |
| Historical audit replay | Passed; historical optimizer source hash checked against accepted Iteration 17 content |
| Iteration 18 design preflight | Passed; frozen config/admission/source references unchanged |
| Reproducible baseline/synthetic report | Passed |
| git diff --check | Passed |
| Hardhat | Sources/tests unchanged; not run for this economics-only change |
| Frontend build/typecheck | Not run; frontend/types untouched |

Reproduce the results without modifying canonical evidence:

```bash
python tools/economics_preflight.py --synthetic
python -m pytest -q tests/test_economics_evidence.py
python -m pytest -q
python -m pytest -q tests/test_result_contract.py
npm --prefix frontend run test:contract
python tools/audit_deployment_history.py --check
python tools/deployment_preflight.py
git diff --check
```

The Iteration 17 audit/data and Iteration 18 canonical design are unchanged.
Only the audit replay tool now treats the authorized optimizer implementation
extension as a new version, verifying its old source fingerprint historically.
It still checks canonical runtime/admission/metadata and all other frozen paths.

## Retained boundaries and limitations

**Economic evidence quality, technical admission, execution quote validity,
risk/stress and public deployment proof are separate dimensions.** Qualified
economics does not substitute for admission; quote validity does not assert
capacity; source/policy metadata does not certify public deployment or risk.

All five runtime configs remain UNRESOLVED and admission CSV is unchanged and
headers-only. Ascend stays CLOSED. Public deployment remains neither required
nor planned. No validator, actual pool/range or wallet was selected/created.
Contracts, schema 1.3, frontend, proposal and legacy optimizer equations are
unchanged. No Iteration 20 work was performed.

The new path is an evidence foundation, not a current observational economics
package. Fresh observations, defensible source-specific policies, captured
cost/zero bases and price-loss context remain acquisition requirements. Source
qualification is explicit ingestion metadata; this layer does not independently
authenticate upstream claims. Those limits remain visible rather than turning
MISSING into zero or MODELLED into LIVE_OBSERVED.
