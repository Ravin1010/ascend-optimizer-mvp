"""Hypothetical captures in temporary files only; no live evidence or RPC."""
import csv
import json
from pathlib import Path

import pytest

from src.ascend_optimizer.admission_records import ADMISSION_COLUMNS, DEFAULT_ADMISSION_PATH, load_admission_records
from src.ascend_optimizer.admission_provider import RepositoryAdmissionProvider
from src.ascend_optimizer.amount_optimizer import AdmissionState, run_amount_optimizer
from src.ascend_optimizer.data_loader import SchemaValidationError, load_snapshots, load_strategies
from src.ascend_optimizer.live_optimize import optimize_live

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def inputs():
    s = load_strategies()
    return s, load_snapshots(s, ROOT/'data/demo_strategy_snapshots.csv')

def record(**changes):
    row = dict.fromkeys(ADMISSION_COLUMNS, '')
    row.update(evidence_id='TEST-1', strategy_id='GIMO_STAKE_0G', chain_id='16661', evidence_type='EXACT_POINT',
               admission_status='SUPPORTED', amount_0g='200', tested_amount_0g='200', source_id='SYNTHETIC_TEST_SOURCE',
               source_role='GIMO_PROTOCOL_ADMISSION', mechanism='Hypothetical explicit protocol admission read',
               evidence_class='LIVE_OBSERVED', observation_timestamp='2026-01-01T00:00:00Z',
               retrieval_timestamp='2026-01-02T00:00:00Z', config_required='TRUE', config_identity='test:gimo:deployment-1',
               capture_status='CAPTURED', notes='SYNTHETIC TEST ONLY, not captured live evidence')
    row.update(changes)
    return row

def write(path, *rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, ADMISSION_COLUMNS); w.writeheader(); w.writerows(rows)
    return path

def provider(tmp_path, inputs, *rows, **kwargs):
    return RepositoryAdmissionProvider(write(tmp_path/'captures.csv', *rows), strategies=inputs[0],
                config_identities=kwargs.pop('config_identities', {'GIMO_STAKE_0G':'test:gimo:deployment-1'}), **kwargs)

def lookup(p, inputs, amount=200, sid='GIMO_STAKE_0G', chain=None, usd=None):
    meta = inputs[0][inputs[0].strategy_id==sid].iloc[0].copy()
    if chain is not None: meta['execution_chain_id'] = chain
    return p(strategy=meta, amount_0g=amount, amount_usd=amount if usd is None else usd, stage='CANDIDATE')

def test_empty_canonical_file():
    assert load_admission_records(DEFAULT_ADMISSION_PATH) == ()

def test_duplicate_rejected_provider_fails_closed(tmp_path, inputs):
    p = provider(tmp_path, inputs, record(), record())
    with pytest.raises(SchemaValidationError, match='duplicate'): load_admission_records(p.path)
    assert lookup(p, inputs).status == AdmissionState.UNKNOWN
    assert 'duplicate' in lookup(p, inputs).diagnostics[0]

@pytest.mark.parametrize('changes', [
    {'strategy_id':'NOT_A_STRATEGY'}, {'strategy_id':'MORPHO_LEND_0G'}, {'chain_id':'16602'},
    {'observation_timestamp':'2026-01-01'}, {'retrieval_timestamp':'not-a-date'},
    {'retrieval_timestamp':'2025-01-01T00:00:00Z'}, {'amount_0g':'-1'}, {'amount_0g':'nan'},
    {'amount_0g':'inf'}, {'amount_0g':'0'}, {'tested_amount_0g':'201'}, {'source_id':''},
    {'mechanism':''}, {'evidence_class':'VERIFIED'}, {'admission_status':'UNKNOWN'},
    {'block_number':'-1'}, {'block_number':'1.5'}, {'block_hash':'0xabc'},
    {'source_role':'MARKET_OBSERVATION'}, {'config_required':'FALSE'},
    {'evidence_type':'SCALAR_BOUND','scalar_headroom_0g':'-1'}, {'evidence_type':'SCALAR_BOUND'},
    {'scalar_headroom_0g':'1000'}, {'amount_usd':'200'}, {'amount_usd':'300','valuation_price_usd':'1'},
])
def test_invalid_record_rejected(tmp_path, inputs, changes):
    p = provider(tmp_path, inputs, record(**changes))
    with pytest.raises(SchemaValidationError): load_admission_records(p.path)
    assert lookup(p, inputs).status == AdmissionState.UNKNOWN

def test_times_and_block_provenance_preserved(tmp_path, inputs):
    p = provider(tmp_path, inputs, record(block_number='123',block_hash='0x'+'ab'*32))
    e = lookup(p, inputs)
    assert e.status == AdmissionState.SUPPORTED
    assert e.capture['observation_timestamp']=='2026-01-01T00:00:00Z'
    assert e.capture['retrieval_timestamp']=='2026-01-02T00:00:00Z'
    assert e.capture['block_number']==123
    assert 'STRUCTURAL_CAPTURE_MATCH_NO_TTL_ASSESSMENT' in e.diagnostics
    json.dumps(e.capture,allow_nan=False)

@pytest.mark.parametrize('changes', [
    {'observation_timestamp':''}, {'retrieval_timestamp':''}, {'config_identity':''},
    {'capture_status':'NO_FRESH_CAPTURE_SUPPLIED'}, {'capture_status':'SOURCE_UNVERIFIED'},
    {'capture_status':'CONFIG_UNRESOLVED','config_identity':''}, {'capture_status':'INVALID'},
])
def test_incomplete_capture_retained_unusable(tmp_path, inputs, changes):
    p = provider(tmp_path,inputs,record(**changes))
    assert len(load_admission_records(p.path))==1
    assert lookup(p,inputs).status==AdmissionState.UNKNOWN

@pytest.mark.parametrize('amount,expected',[(200,'SUPPORTED'),(100,'UNKNOWN'),(201,'UNKNOWN'),(300,'UNKNOWN')])
def test_exact_point_no_interpolation(tmp_path,inputs,amount,expected):
    assert lookup(provider(tmp_path,inputs,record()),inputs,amount).status.value==expected

def test_bound_and_usd_context(tmp_path,inputs):
    p=provider(tmp_path,inputs,record(evidence_type='SCALAR_BOUND',amount_0g='',tested_amount_0g='',scalar_headroom_0g='500'))
    assert lookup(p,inputs,100).status==AdmissionState.SUPPORTED
    assert lookup(p,inputs,500).status==AdmissionState.SUPPORTED
    assert lookup(p,inputs,501).status==AdmissionState.UNSUPPORTED
    write(p.path,record(evidence_type='SCALAR_BOUND',amount_0g='',tested_amount_0g='',scalar_headroom_usd='1000',valuation_price_usd='2'))
    assert lookup(p,inputs,200,usd=400).status==AdmissionState.SUPPORTED
    assert lookup(p,inputs,600,usd=1200).status==AdmissionState.UNSUPPORTED
    assert lookup(p,inputs,200,usd=200).status==AdmissionState.UNKNOWN

def test_wrong_chain_strategy_or_config(tmp_path,inputs):
    p=provider(tmp_path,inputs,record())
    assert lookup(p,inputs,chain=16602).status==AdmissionState.UNKNOWN
    assert lookup(p,inputs,sid='NATIVE_STAKE_0G').status==AdmissionState.UNKNOWN
    p.config_identities['GIMO_STAKE_0G']='wrong'
    assert lookup(p,inputs).status==AdmissionState.UNKNOWN
    p.config_identities.clear()
    assert lookup(p,inputs).status==AdmissionState.UNKNOWN

def test_conflicts_no_optimistic_override(tmp_path,inputs):
    p=provider(tmp_path,inputs,record(admission_status='UNSUPPORTED'),record(evidence_id='NEW',observation_timestamp='2026-01-03T00:00:00Z',retrieval_timestamp='2026-01-04T00:00:00Z'))
    assert lookup(p,inputs).status==AdmissionState.UNKNOWN
    assert 'CONFLICTING_CAPTURE_STATUSES' in lookup(p,inputs).diagnostics[0]
    write(p.path,record(),record(evidence_id='BOUND',evidence_type='SCALAR_BOUND',amount_0g='',tested_amount_0g='',scalar_headroom_0g='100'))
    assert lookup(p,inputs).status==AdmissionState.UNKNOWN

def test_specificity_observation_id_not_retrieval(tmp_path,inputs):
    rows=[record(evidence_id='BOUND',evidence_type='SCALAR_BOUND',amount_0g='',tested_amount_0g='',scalar_headroom_0g='1000',observation_timestamp='2026-01-05T00:00:00Z',retrieval_timestamp='2026-01-06T00:00:00Z'),
          record(evidence_id='OLD',retrieval_timestamp='2026-02-01T00:00:00Z'),
          record(evidence_id='B',observation_timestamp='2026-01-03T00:00:00Z',retrieval_timestamp='2026-01-04T00:00:00Z'),
          record(evidence_id='A',observation_timestamp='2026-01-03T00:00:00Z',retrieval_timestamp='2026-01-04T00:00:00Z')]
    p=provider(tmp_path,inputs,*rows)
    assert lookup(p,inputs).capture['evidence_id']=='A'
    write(p.path,*reversed(rows))
    assert lookup(p,inputs).capture['evidence_id']=='A'

def test_modelled_explicit_opt_in_historical_never_current(tmp_path,inputs):
    p=provider(tmp_path,inputs,record(evidence_class='MODELLED'))
    assert lookup(p,inputs).status==AdmissionState.UNKNOWN
    demo=RepositoryAdmissionProvider(p.path,strategies=inputs[0],config_identities=p.config_identities,allow_modelled=True)
    assert lookup(demo,inputs).evidence_class=='MODELLED'
    assert lookup(demo,inputs).status==AdmissionState.SUPPORTED
    write(p.path,record(evidence_class='HISTORICAL'))
    assert lookup(demo,inputs).status==AdmissionState.UNKNOWN

def test_explicit_negative_point(tmp_path,inputs):
    assert lookup(provider(tmp_path,inputs,record(admission_status='UNSUPPORTED')),inputs).status==AdmissionState.UNSUPPORTED

def test_native_validator_binding(tmp_path,inputs):
    p=provider(tmp_path,inputs,record(strategy_id='NATIVE_STAKE_0G',source_role='CONFIGURED_VALIDATOR_ADMISSION',config_identity='test:validator'),config_identities={'NATIVE_STAKE_0G':'test:validator'})
    assert lookup(p,inputs,sid='NATIVE_STAKE_0G').status==AdmissionState.SUPPORTED
    p.config_identities.clear()
    assert lookup(p,inputs,sid='NATIVE_STAKE_0G').status==AdmissionState.UNKNOWN

def test_ascend_gate_overrides_capture(tmp_path,inputs):
    p=provider(tmp_path,inputs,record(strategy_id='ASCEND_STAKE_A0G',source_role='SOURCECORE_ADMISSION',config_identity='test:core'),config_identities={'ASCEND_STAKE_A0G':'test:core'})
    assert lookup(p,inputs,sid='ASCEND_STAKE_A0G').status==AdmissionState.UNKNOWN
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',admission_fn=p)
    assert not r.selected and r.to_dict()['strategy_results']['ASCEND_STAKE_A0G']=='GATED'

@pytest.mark.parametrize('profile',['Conservative','Balanced','Aggressive'])
def test_repository_no_tvl_depth_or_quote_fallback(inputs,profile):
    s,snapshots=inputs
    snapshots['tvl_usd']=1e15; snapshots['liquidity_usd']=1e15
    def forbidden(**kw): raise AssertionError('quote is not admission')
    r=run_amount_optimizer(s,snapshots,decision_amount=1000,price_usd=1,horizon_days=90,profile=profile,lp_quote_fn=forbidden)
    assert not r.selected and r.to_dict()['recommendation']['idle_weight']==1

@pytest.mark.parametrize('change',['withdraw','invalid','status','observation'])
def test_selected_lookup_repeated_changed_capture_fails(tmp_path,inputs,change):
    base=provider(tmp_path,inputs,record()); calls=[]
    class Changing(RepositoryAdmissionProvider):
        def __call__(self,**kw):
            calls.append(kw['stage'])
            if kw['stage']=='REVALIDATION':
                if change=='withdraw': write(self.path)
                elif change=='invalid': self.path.write_text('invalid header\n')
                elif change=='status': write(self.path,record(admission_status='UNSUPPORTED'))
                else: write(self.path,record(observation_timestamp='2026-01-03T00:00:00Z',retrieval_timestamp='2026-01-04T00:00:00Z'))
            return super().__call__(**kw)
    p=Changing(base.path,strategies=inputs[0],config_identities=base.config_identities)
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',admission_fn=p)
    assert 'REVALIDATION' in calls and r.selected[0].amount_0g==200
    assert r.revalidation=='FAILED' and r.to_dict()['recommendation'] is None

def test_unchanged_capture_passes_and_legacy_unchanged(tmp_path,inputs):
    p=provider(tmp_path,inputs,record())
    legacy=lambda:optimize_live(*inputs,amount=1000,price_usd=1,horizon_days=90,profile='Balanced').to_dict()
    before=legacy()
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',admission_fn=p)
    assert r.revalidation=='PASSED' and r.selected[0].amount_0g==200
    assert before==legacy()
    json.dumps(r.to_dict(),allow_nan=False)


def test_modelled_mode_requires_boolean_opt_in(tmp_path,inputs):
    with pytest.raises(ValueError,match='explicit boolean'):
        provider(tmp_path,inputs,record(evidence_class='MODELLED'),allow_modelled='false')


# Decimal-boundary regressions use hypothetical captures only.
def decimal_point(inputs, p, *, weight=.3, price=1.7):
    from src.ascend_optimizer.amount_optimizer import evaluate_candidate
    from src.ascend_optimizer.profiles import get_profile
    strategies, snapshots = inputs
    sid = 'GIMO_STAKE_0G'
    return evaluate_candidate(strategies[strategies.strategy_id == sid].iloc[0],
                              snapshots[snapshots.strategy_id == sid].iloc[0],
                              decision_amount=100.1, weight=weight, price_usd=price,
                              horizon_days=90, profile=get_profile('Balanced'), admission_fn=p)


@pytest.mark.parametrize('evidence_amount,expected', [
    ('30.03', 'SUPPORTED'), ('30.030', 'SUPPORTED'), ('30.031', 'UNKNOWN'),
])
def test_canonical_decimal_exact_identity(tmp_path, inputs, evidence_amount, expected):
    from decimal import Decimal
    p = provider(tmp_path, inputs, record(amount_0g=evidence_amount, tested_amount_0g=evidence_amount))
    seen = []
    def capture(**kw):
        seen.append((kw['canonical_amount_0g'], kw['canonical_amount_usd']))
        return p(**kw)
    c = decimal_point(inputs, capture)
    assert seen == [(Decimal('30.03'), Decimal('51.051'))]
    assert c.amount_0g == 30.03
    assert c.technical_admission == expected


@pytest.mark.parametrize('price,expected', [(1.7, 'SUPPORTED'), (1.7001, 'UNKNOWN')])
def test_canonical_decimal_valuation(tmp_path, inputs, price, expected):
    p = provider(tmp_path, inputs, record(amount_0g='30.03', tested_amount_0g='30.03',
                 amount_usd='51.051', tested_amount_usd='51.051', valuation_price_usd='1.7'))
    c = decimal_point(inputs, p, price=price)
    assert c.technical_admission == expected
    if expected == 'SUPPORTED':
        assert c.amount_usd == 51.051


@pytest.mark.parametrize('bound,expected', [('30.030', 'SUPPORTED'), ('30.029', 'UNSUPPORTED')])
def test_canonical_decimal_native_bound(tmp_path, inputs, bound, expected):
    p = provider(tmp_path, inputs, record(evidence_type='SCALAR_BOUND', amount_0g='',
                 tested_amount_0g='', scalar_headroom_0g=bound))
    assert decimal_point(inputs, p).technical_admission == expected


@pytest.mark.parametrize('bound,expected', [('51.051', 'SUPPORTED'), ('51.050', 'UNSUPPORTED')])
def test_canonical_decimal_usd_bound(tmp_path, inputs, bound, expected):
    p = provider(tmp_path, inputs, record(evidence_type='SCALAR_BOUND', amount_0g='',
                 tested_amount_0g='', scalar_headroom_usd=bound, valuation_price_usd='1.7'))
    assert decimal_point(inputs, p).technical_admission == expected


def test_canonical_decimal_selected_revalidation(tmp_path, inputs):
    from decimal import Decimal
    base = provider(tmp_path, inputs, record(amount_0g='30.030', tested_amount_0g='30.03',
                    amount_usd='51.051', valuation_price_usd='1.7'))
    calls = []
    def capture(**kw):
        if kw['strategy'].strategy_id == 'GIMO_STAKE_0G' and kw['canonical_amount_0g'] == Decimal('30.03'):
            calls.append((kw['stage'], kw['canonical_amount_0g'], kw['canonical_amount_usd']))
        return base(**kw)
    r = run_amount_optimizer(*inputs, decision_amount=100.1, price_usd=1.7,
                             horizon_days=90, profile='Balanced', admission_fn=capture)
    assert r.revalidation == 'PASSED'
    assert len(r.selected) == 1 and r.selected[0].amount_0g == 30.03
    assert calls == [('CANDIDATE', Decimal('30.03'), Decimal('51.051')),
                     ('REVALIDATION', Decimal('30.03'), Decimal('51.051'))]
