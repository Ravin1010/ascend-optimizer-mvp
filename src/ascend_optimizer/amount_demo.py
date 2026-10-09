"""Reproducible Iteration 13 comparison; local demo assumptions, no RPC calls.

Default: canonical repository admission captures (empty baseline -> UNKNOWN). --synthetic-support
explicitly tests the solver with modelled point admission and nonlinear quotes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json

from .amount_optimizer import AdmissionEvidence, AdmissionState, run_amount_optimizer
from .data_loader import DEFAULT_DATA_DIR, load_snapshots, load_strategies
from .live_optimize import optimize_live
from .lp_execution import LPExecutionQuote
from .profiles import list_profiles


def synthetic_admission(**kw) -> AdmissionEvidence:
    return AdmissionEvidence(AdmissionState.SUPPORTED, str(kw['strategy'].strategy_id), kw['amount_0g'],
                             int(kw['strategy'].execution_chain_id), 'SYNTHETIC_DEMO_ONLY',
                             'Explicit tested point assumption, not live admission', 'MODELLED')


def synthetic_quote(**kw) -> LPExecutionQuote:
    amount = kw['amount_0g']
    return LPExecutionQuote(kw['strategy_id'], 3000, amount / 100000, amount / 80000,
                            amount * .5 * (1 - amount / 100000), amount * .5 * (1 - amount / 80000))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-support', action='store_true', help='Explicit modelled admission/quote test; never live evidence')
    parser.add_argument('--as-of', help='Timezone-aware ISO admission evaluation time (default: current UTC, resolved by CLI)')
    args = parser.parse_args()
    as_of = datetime.now(timezone.utc) if args.as_of is None else datetime.fromisoformat(args.as_of.replace('Z', '+00:00'))
    strategies = load_strategies()
    snapshots = load_snapshots(strategies, DEFAULT_DATA_DIR / 'demo_strategy_snapshots.csv')
    outputs = []
    for profile in list_profiles():
        legacy = optimize_live(strategies, snapshots, amount=1000, price_usd=1, horizon_days=90, profile=profile.name.value)
        kwargs = {'admission_fn': synthetic_admission, 'lp_quote_fn': synthetic_quote} if args.synthetic_support else {}
        amount_run = run_amount_optimizer(strategies, snapshots, decision_amount=1000, price_usd=1,
                                          horizon_days=90, profile=profile, as_of=as_of, **kwargs)
        outputs.append(legacy.to_dict(amount_aware=amount_run))
    print(json.dumps({'evidence': 'SYNTHETIC_DEMO_ONLY', 'admission_basis': 'MODELLED_POINT_SUPPORT' if args.synthetic_support else 'REPOSITORY_CAPTURE_PROVIDER',
                      'runs': outputs}, allow_nan=False, indent=2))


if __name__ == '__main__':
    main()
