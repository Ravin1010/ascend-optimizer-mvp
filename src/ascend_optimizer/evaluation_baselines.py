"""Transparent FINAL_EVALUATION_V1 rules; no production optimizer changes."""
from decimal import Decimal

METHODS = ('HIGHEST_YIELD_BASELINE', 'EQUAL_WEIGHT_ELIGIBLE_BASELINE',
           'LEGACY_LINEAR_OPTIMIZER', 'POLICY_AWARE_AMOUNT_OPTIMIZER')


def allocate(method, eligible_rates, concentration, strategy_ids):
    """Positive apparent annual return only; Ascend is always gated.

    Highest yield fills ranked caps. Equal weight uses min(1/n, cap), leaving
    residual idle. Neither rule searches amount-specific costs/risk/deadlines.
    """
    if method not in METHODS[:2]:
        raise ValueError('simple baseline method required')
    cap = Decimal(str(concentration))
    if not 0 <= cap <= 1:
        raise ValueError('invalid concentration')
    eligible = [s for s in strategy_ids if s != 'ASCEND_STAKE_A0G'
                and s in eligible_rates and Decimal(str(eligible_rates[s])) > 0]
    weights = dict.fromkeys(strategy_ids, Decimal(0))
    if method == METHODS[0]:
        remaining = Decimal(1)
        for sid in sorted(eligible, key=lambda s: (-Decimal(str(eligible_rates[s])), s)):
            weights[sid] = min(cap, remaining)
            remaining -= weights[sid]
    elif eligible:
        target = min(Decimal(1) / len(eligible), cap)
        for sid in eligible:
            weights[sid] = target
    return weights, Decimal(1) - sum(weights.values())
