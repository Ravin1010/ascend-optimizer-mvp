"""Synthetic amount/admission fixtures; no live evidence or RPC requests."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.amount_optimizer import (
    AdmissionEvidence, AdmissionState, candidate_grid, evaluate_candidate, run_amount_optimizer,
)
from src.ascend_optimizer.collectors.common import CollectionError
from src.ascend_optimizer.data_loader import load_strategies, load_snapshots, MVP_STRATEGY_IDS
from src.ascend_optimizer.live_optimize import optimize_live
from src.ascend_optimizer.lp_execution import LPExecutionQuote
from src.ascend_optimizer.profiles import get_profile

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    s = load_strategies(ROOT / 'data/strategies.csv')
    return s, load_snapshots(s, ROOT / 'data/demo_strategy_snapshots.csv')


def supported(**kw):
    return AdmissionEvidence(AdmissionState.SUPPORTED, str(kw['strategy'].strategy_id), kw['amount_0g'],
                             16661, 'SYNTHETIC_TEST_ONLY', 'Explicit tested amount assumption', 'MODELLED')


def quote(**kw):
    amount = kw['amount_0g']
    # A nonlinear synthetic loss, not a scaled full-portfolio quote.
    return LPExecutionQuote(kw['strategy_id'], 3000, amount / 100000, amount / 80000,
                            amount * .5 * (1 - amount / 100000), amount * .5 * (1 - amount / 80000))


def run(inputs, **kw):
    s, snapshots = inputs
    return run_amount_optimizer(s, snapshots, decision_amount=1000, price_usd=1, horizon_days=90,
                                profile=kw.pop('profile', 'Balanced'), as_of=datetime(2026, 1, 1, tzinfo=timezone.utc), **kw)


def point(inputs, sid='NATIVE_STAKE_0G', weight=.2, **kw):
    s, snapshots = inputs
    return evaluate_candidate(s[s.strategy_id == sid].iloc[0], snapshots[snapshots.strategy_id == sid].iloc[0],
                              weight=weight, decision_amount=1000, price_usd=1, horizon_days=90,
                              profile=get_profile('Aggressive'), admission_fn=kw.pop('admission_fn', supported),
                              lp_quote_fn=kw.pop('lp_quote_fn', quote), **kw)


def test_zero_for_every_member_without_cost_quote_or_admission(inputs):
    def forbidden(**kw):
        raise AssertionError('zero must not invoke admission or quote')
    s, snapshots = inputs
    for sid in MVP_STRATEGY_IDS:
        c = point(inputs, sid, 0, admission_fn=forbidden, lp_quote_fn=forbidden)
        assert c.eligible and c.net_profit_usd == c.fixed_execution_cost_usd == 0
        assert c.runtime_execution == 'NOT_REQUIRED'


def test_fixed_lifecycle_cost_once_at_actual_amount(inputs):
    s, snapshots = inputs
    snapshots.loc[snapshots.strategy_id == 'NATIVE_STAKE_0G', 'gas_cost_usd'] = 2
    small = point((s, snapshots), weight=.1)
    large = point((s, snapshots), weight=.4)
    assert small.fixed_execution_cost_usd == large.fixed_execution_cost_usd == 2
    assert large.net_profit_usd == pytest.approx(4 * (small.net_profit_usd + 2) - 2)
    assert point((s, snapshots), weight=0).net_profit_usd == 0


def test_missing_cost_is_not_zero(inputs):
    s, snapshots = inputs
    snapshots.loc[snapshots.strategy_id == 'NATIVE_STAKE_0G', 'gas_cost_usd'] = pd.NA
    c = point((s, snapshots))
    assert not c.eligible and c.net_profit_usd is None
    assert 'MISSING_COST_OR_RETURN_COMPONENT: gas_cost_usd' in c.rejection_reasons


@pytest.mark.parametrize('sid', ['JAINE_LP_0G_USDC', 'OKU_LP_0G_USDC'])
def test_lp_always_quotes_actual_points_despite_prefilled_slippage(inputs, sid):
    calls = []
    def measured(**kw):
        calls.append(kw['amount_0g'])
        return quote(**kw)
    a = point(inputs, sid, .1, lp_quote_fn=measured)
    b = point(inputs, sid, .4, lp_quote_fn=measured)
    assert calls == [100, 400]
    assert a.entry_slippage_rate != b.entry_slippage_rate
    assert a.net_return_horizon != b.net_return_horizon
    assert b.net_profit_usd != pytest.approx(4 * a.net_profit_usd)
    assert b.quote_context['amount_0g'] == 400
    assert b.quote_context['registered_configuration_alignment'] == 'NOT_ESTABLISHED'


def test_quote_failure_is_candidate_specific(inputs):
    def one_fails(**kw):
        if kw['amount_0g'] == 200:
            raise CollectionError('synthetic point failure')
        return quote(**kw)
    assert point(inputs, 'JAINE_LP_0G_USDC', .1, lp_quote_fn=one_fails).eligible
    failed = point(inputs, 'JAINE_LP_0G_USDC', .2, lp_quote_fn=one_fails)
    assert not failed.eligible and failed.runtime_execution == 'FAILED'


def test_liquidity_proxy_never_limits_new_search(inputs):
    s, snapshots = inputs
    original = run(inputs, admission_fn=supported, lp_quote_fn=quote)
    snapshots['liquidity_usd'] = pd.NA
    changed = run((s, snapshots), admission_fn=supported, lp_quote_fn=quote)
    assert changed.selected == original.selected
    assert changed.to_dict()['recommendation'] == original.to_dict()['recommendation']


def test_unknown_admission_is_not_unlimited(inputs):
    def forbidden(**kw):
        raise AssertionError('unknown admission should not cause live quoting')
    result = run(inputs, lp_quote_fn=forbidden)
    assert not result.selected
    assert result.to_dict()['recommendation']['idle_weight'] == 1
    positives = [c for c in result.candidates if c.weight > 0]
    assert all(not c.eligible for c in positives)
    assert any('TECHNICAL_ADMISSION_UNKNOWN' in c.rejection_reasons for c in positives)


def test_point_support_without_scalar_capacity_not_extrapolated(inputs):
    def only_point(**kw):
        e = supported(**kw)
        return e if kw['strategy'].strategy_id == 'GIMO_STAKE_0G' and kw['amount_0g'] == 200 else replace(e, status=AdmissionState.UNKNOWN)
    result = run(inputs, admission_fn=only_point, lp_quote_fn=quote)
    assert [(c.strategy_id, c.amount_0g) for c in result.selected] == [('GIMO_STAKE_0G', 200)]
    assert result.selected[0].admission_evidence.scalar_headroom_usd is None
    assert result.to_dict()['recommendation']['idle_weight'] == .8


def test_explicit_bound_and_mismatched_point_fail(inputs):
    def bound(**kw):
        return replace(supported(**kw), scalar_headroom_usd=100)
    assert point(inputs, weight=.1, admission_fn=bound).eligible
    assert point(inputs, weight=.2, admission_fn=bound).technical_admission == 'UNSUPPORTED'
    def wrong(**kw):
        return replace(supported(**kw), amount_0g=999)
    assert not point(inputs, admission_fn=wrong).eligible


def test_closed_gate_cannot_be_overridden_and_nonmembers_have_no_options(inputs):
    r = run(inputs, admission_fn=supported, lp_quote_fn=quote)
    assert {c.strategy_id for c in r.candidates} == MVP_STRATEGY_IDS
    assert all(not c.eligible for c in r.candidates if c.strategy_id == 'ASCEND_STAKE_A0G' and c.weight > 0)
    assert set(r.reported_non_members) == {'ASCEND_RESTAKE', 'MORPHO_LEND_0G'}
    for sid in r.reported_non_members:
        with pytest.raises(ValueError, match='Non-members'):
            point(inputs, sid)


@pytest.mark.parametrize('profile,cap', [('Conservative', .4), ('Balanced', .6), ('Aggressive', .8)])
def test_grid_boundaries_and_search_determinism(inputs, profile, cap):
    r = run(inputs, profile=profile, admission_fn=supported, lp_quote_fn=quote)
    assert r.grid[0] == 0 and r.grid[-1] == cap
    assert r.selected == run(inputs, profile=profile, admission_fn=supported, lp_quote_fn=quote).selected
    assert r.revalidation == 'PASSED'
    assert r.combinations_tested <= 9**4
    rec = r.to_dict()['recommendation']
    assert sum(c.weight for c in r.selected) + rec['idle_weight'] == pytest.approx(1, abs=1e-10)


def test_custom_profile_cap_exact():
    p = replace(get_profile('Balanced'), max_strategy_concentration=.35)
    assert candidate_grid(p) == (0, .1, .2, .3, .35)


def test_tie_prefers_idle_and_then_registration_order(inputs):
    s, snapshots = inputs
    snapshots['gross_apy'] = 0
    snapshots['incentive_apy'] = 0
    snapshots['entry_slippage_rate'] = 0
    snapshots['exit_slippage_rate'] = 0
    def zero_quote(**kw):
        return replace(quote(**kw), entry_slippage_rate=0, exit_slippage_rate=0)
    r = run((s, snapshots), admission_fn=supported, lp_quote_fn=zero_quote)
    assert not r.selected  # profit tie -> least deployed
    snapshots['gross_apy'] = .1
    # Restrict to identical Native/Gimo: exact same return/cost/stress.
    snapshots['slashing_stress_loss'] = .01
    def two(**kw):
        e = supported(**kw)
        return e if kw['strategy'].strategy_id in {'NATIVE_STAKE_0G', 'GIMO_STAKE_0G'} else replace(e, status=AdmissionState.UNKNOWN)
    r = run((s, snapshots), admission_fn=two, lp_quote_fn=zero_quote)
    assert [(c.strategy_id, c.weight) for c in r.selected] == [('NATIVE_STAKE_0G', .6), ('GIMO_STAKE_0G', .4)]


@pytest.mark.parametrize('change', ['failure', 'still_passing', 'admission', 'gate'])
def test_selected_revalidation_rejects_changed_evidence(inputs, change):
    s, snapshots = inputs
    phase = False
    def admission(**kw):
        nonlocal phase
        phase = kw['stage'] == 'REVALIDATION'
        e = supported(**kw)
        if phase and change == 'admission':
            return replace(e, status=AdmissionState.UNKNOWN)
        if phase and change == 'gate':
            s.loc[s.strategy_id == 'JAINE_LP_0G_USDC', 'allocation_gate'] = 'CLOSED'
        # Only Jaine admitted to ensure selected quote revalidation.
        return e if kw['strategy'].strategy_id == 'JAINE_LP_0G_USDC' else replace(e, status=AdmissionState.UNKNOWN)
    def changing_quote(**kw):
        if phase and change == 'failure':
            raise CollectionError('changed quote failed')
        q = quote(**kw)
        return replace(q, entry_slippage_rate=q.entry_slippage_rate + .00001) if phase and change == 'still_passing' else q
    r = run((s, snapshots), admission_fn=admission, lp_quote_fn=changing_quote)
    if change == 'gate':
        # Mutation occurs during this check; final metadata check must catch it.
        assert r.revalidation == 'FAILED'
    else:
        assert r.revalidation == 'FAILED'
    payload = r.to_dict()
    assert payload['recommendation'] is None
    assert payload['outcome'] == 'SELECTED_REVALIDATION_FAILED'


def test_eligible_zero_is_not_exclusion(inputs):
    s, snapshots = inputs
    snapshots.loc[snapshots.strategy_id == 'NATIVE_STAKE_0G', 'gross_apy'] = 0
    r = run((s, snapshots), admission_fn=supported, lp_quote_fn=quote)
    assert r.to_dict()['strategy_results']['NATIVE_STAKE_0G'] == 'ELIGIBLE_ZERO'
    assert r.to_dict()['strategy_results']['ASCEND_STAKE_A0G'] == 'GATED'


def test_schema_optional_extension_preserves_benchmark_and_strict_json(inputs):
    s, snapshots = inputs
    legacy = optimize_live(s, snapshots, amount=1000, horizon_days=90, profile='Balanced', price_usd=1)
    amount = run(inputs, admission_fn=supported, lp_quote_fn=quote)
    before = legacy.to_dict()
    extended = legacy.to_dict(amount_aware=amount)
    assert {k:v for k,v in extended.items() if k != 'amount_aware'} == before
    assert extended['schema_version'] == '1.3'
    assert extended['amount_aware']['benchmark']['method'] == 'LEGACY_LINEAR'
    assert extended['amount_aware']['whole_portfolio_compliance'] == 'NOT_ASSESSED'
    json.dumps(extended, allow_nan=False)
    with pytest.raises(ValueError, match='contexts'):
        legacy.to_dict(amount_aware=replace(amount, decision_amount=2000))


def test_invalid_universe_and_decision_inputs_fail(inputs):
    s, snapshots = inputs
    with pytest.raises(ValueError, match='exactly'):
        run((s[s.strategy_id != 'GIMO_STAKE_0G'], snapshots))
    with pytest.raises(ValueError, match='duplicate'):
        run((pd.concat([s, s.iloc[:1]]), snapshots))
    with pytest.raises(ValueError, match='positive'):
        run_amount_optimizer(s, snapshots, decision_amount=0, price_usd=1, horizon_days=90, profile='Balanced')


def test_fixed_cost_activation_and_constraint_limited_idle(inputs):
    s, snapshots = inputs
    snapshots.loc[snapshots.strategy_id == 'GIMO_STAKE_0G', 'gas_cost_usd'] = 3
    def gimo_only(**kw):
        e = supported(**kw)
        return e if kw['strategy'].strategy_id == 'GIMO_STAKE_0G' else replace(e, status=AdmissionState.UNKNOWN)
    r = run((s, snapshots), admission_fn=gimo_only)
    assert r.selected[0].weight == .6
    assert r.selected[0].fixed_execution_cost_usd == 3
    assert r.to_dict()['recommendation']['idle_weight'] == pytest.approx(.4)
    profit = .6 * 1000 * ((1.1)**(90/365)-1-.0035) - 3
    assert r.to_dict()['recommendation']['expected_net_profit_usd'] == pytest.approx(profit)


def test_aggregate_legacy_stress_constraints_and_missing_risk(inputs):
    s, snapshots = inputs
    snapshots['bridge_fraction'] = .5
    snapshots['slashing_stress_loss'] = .5
    r = run((s, snapshots), profile='Conservative', admission_fn=supported, lp_quote_fn=quote)
    rec = r.to_dict()['recommendation']
    # Staking points contribute >=5% slash and cannot enter. LP slash is
    # structurally zero; LP/dependency aggregate constraints still bind.
    assert all(c.strategy_id in {'JAINE_LP_0G_USDC', 'OKU_LP_0G_USDC'} for c in r.selected)
    assert rec['legacy_stress']['slashing_stress_loss'] <= .02
    assert rec['legacy_stress']['bridge_fraction'] <= .1 + 1e-10
    assert rec['legacy_stress']['lp_stress_loss_20pct'] <= .02 + 1e-10
    snapshots.loc[snapshots.strategy_id == 'GIMO_STAKE_0G', 'slashing_stress_loss'] = pd.NA
    c = point((s, snapshots), 'GIMO_STAKE_0G')
    assert not c.eligible and 'MISSING_slashing_stress_loss' in c.rejection_reasons


def test_unresolved_fee_basis_and_invalid_quote_are_not_admitted(inputs):
    s, snapshots = inputs
    snapshots.loc[snapshots.strategy_id == 'NATIVE_STAKE_0G', 'yield_fee_status'] = 'UNKNOWN'
    assert 'FEE_BASIS_UNRESOLVED' in point((s, snapshots)).rejection_reasons
    def bad(**kw):
        return replace(quote(**kw), entry_amount_out_usdc=float('nan'))
    c = point(inputs, 'JAINE_LP_0G_USDC', lp_quote_fn=bad)
    assert not c.eligible and c.runtime_execution == 'FAILED'


def test_demo_benchmark_compare_does_not_change_legacy_allocations(inputs):
    s, snapshots = inputs
    expected = {
        'Conservative': {'NATIVE_STAKE_0G': .4, 'GIMO_STAKE_0G': .4},
        'Balanced': {'JAINE_LP_0G_USDC': .6, 'GIMO_STAKE_0G': .4},
        'Aggressive': {'JAINE_LP_0G_USDC': .8, 'OKU_LP_0G_USDC': .2},
    }
    for profile, weights in expected.items():
        legacy = optimize_live(s, snapshots, amount=1000, horizon_days=90, profile=profile, price_usd=1)
        amount = run(inputs, profile=profile)
        assert legacy.pipeline.result.allocations == pytest.approx(weights)
        assert amount.to_dict()['recommendation']['idle_weight'] == 1
        extension = legacy.to_dict(amount_aware=amount)
        assert extension['portfolio']['allocations'] == legacy.to_dict()['portfolio']['allocations']
        assert extension['amount_aware']['benchmark']['allocations'] == pytest.approx(weights)
