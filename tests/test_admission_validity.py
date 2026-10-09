"""Synthetic freshness/config captures only; no live evidence collection."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

import pytest

from src.ascend_optimizer.admission_provider import RepositoryAdmissionProvider
from src.ascend_optimizer.admission_records import load_admission_records
from src.ascend_optimizer.admission_validity import (
    RuntimeConfigContext, assess_capture, DEFAULT_POLICIES,
)
from src.ascend_optimizer.amount_optimizer import run_amount_optimizer
from test_admission_evidence import inputs, record, write

T = datetime(2026, 1, 1, tzinfo=timezone.utc)
SID = 'GIMO_STAKE_0G'
IDENTITY = 'test:gimo:deployment-1'
CONTEXT = RuntimeConfigContext(SID, 16661, IDENTITY, 'VERIFIED', 'SYNTHETIC_TEST_ONLY')

def capture(**kw):
    return record(retrieval_timestamp='2026-01-01T00:00:01Z', **kw)

def make(tmp_path, inputs, *rows, **kw):
    return RepositoryAdmissionProvider(write(tmp_path/'fresh.csv', *(rows or [capture()])),
        strategies=inputs[0], config_contexts=kw.pop('config_contexts', {SID: CONTEXT}),
        **kw)

def lookup(p, inputs, *, age=100, amount=200, as_of=None):
    return p(strategy=inputs[0][inputs[0].strategy_id == SID].iloc[0],
             amount_0g=amount, amount_usd=amount,
             as_of=T+timedelta(seconds=age) if as_of is None else as_of)

@pytest.mark.parametrize('time', [None, datetime(2026,1,1), '2026-01-01T00:00:00Z'])
def test_explicit_aware_time_required(tmp_path,inputs,time):
    p=make(tmp_path,inputs)
    with pytest.raises(ValueError,match='timezone-aware'):
        p(strategy=inputs[0].iloc[1],amount_0g=200,amount_usd=200,as_of=time)

@pytest.mark.parametrize('age,state,status', [(0,'VALID','SUPPORTED'),(299,'VALID','SUPPORTED'),
    (300,'VALID','SUPPORTED'),(301,'STALE','UNKNOWN'),(-1,'MISSING','UNKNOWN')])
def test_age_boundary_and_future(tmp_path,inputs,age,state,status):
    e=lookup(make(tmp_path,inputs),inputs,age=age)
    assert e.validity['state']==state and e.status.value==status
    assert e.validity['observation_age_seconds']==age
    assert e.validity['max_age_seconds']==300
    json.dumps(e.validity,allow_nan=False)

@pytest.mark.parametrize('retrieval',['2026-01-01T00:00:01Z','2026-01-01T00:05:00Z'])
def test_retrieval_never_refreshes_observation(tmp_path,inputs,retrieval):
    e=lookup(make(tmp_path,inputs,record(retrieval_timestamp=retrieval)),inputs,age=301)
    assert e.validity['state']=='STALE'
    assert e.validity['observation_age_seconds']==301
    assert e.validity['retrieval_timestamp']==retrieval

@pytest.mark.parametrize('changes,state', [
    ({'observation_timestamp':''},'MISSING'),({'capture_status':'SOURCE_UNVERIFIED'},'SOURCE_UNVERIFIED'),
    ({'capture_status':'NO_FRESH_CAPTURE_SUPPLIED'},'MISSING'),({'capture_status':'INVALID'},'MISSING'),
    ({'capture_status':'CONFIG_UNRESOLVED'},'CONFIG_MISMATCH'),({'config_identity':''},'MISSING'),
    ({'evidence_class':'STATIC_CONFIG'},'POLICY_UNDEFINED'),({'evidence_class':'HISTORICAL'},'SOURCE_UNVERIFIED'),
    ({'evidence_class':'MODELLED'},'SOURCE_UNVERIFIED'),
])
def test_capture_class_validity(tmp_path,inputs,changes,state):
    e=lookup(make(tmp_path,inputs,capture(**changes)),inputs)
    assert e.status.value=='UNKNOWN' and e.validity['state']==state


def test_policy_undefined_fail_closed(tmp_path,inputs):
    e=lookup(make(tmp_path,inputs,policies={}),inputs)
    assert e.validity['state']=='POLICY_UNDEFINED' and e.status.value=='UNKNOWN'


def test_explicit_demo_modelled_policy(tmp_path,inputs):
    p=make(tmp_path,inputs,capture(evidence_class='MODELLED'),allow_modelled=True)
    assert lookup(p,inputs).status.value=='SUPPORTED'
    assert lookup(p,inputs).evidence_class=='MODELLED'
    assert lookup(p,inputs,age=301).status.value=='UNKNOWN'

@pytest.mark.parametrize('contexts,state', [
    ({},'MISSING'),({SID:RuntimeConfigContext(SID,16661,'wrong','VERIFIED','test')},'CONFIG_MISMATCH'),
    ({SID:RuntimeConfigContext(SID,16602,IDENTITY,'VERIFIED','test')},'CONFIG_MISMATCH'),
    ({SID:RuntimeConfigContext(SID,16661,IDENTITY)},'SOURCE_UNVERIFIED'),
])
def test_runtime_context_requirements(tmp_path,inputs,contexts,state):
    e=lookup(make(tmp_path,inputs,config_contexts=contexts),inputs)
    assert e.status.value=='UNKNOWN' and e.validity['state']==state


def test_legacy_identity_alone_not_verified(tmp_path,inputs):
    p=make(tmp_path,inputs,config_contexts={},config_identities={SID:IDENTITY})
    assert lookup(p,inputs).validity['state']=='SOURCE_UNVERIFIED'


def test_exact_amount_distinct_from_config(tmp_path,inputs):
    p=make(tmp_path,inputs)
    assert lookup(p,inputs,amount=201).validity['state']=='AMOUNT_MISMATCH'
    assert lookup(p,inputs,amount=201).status.value=='UNKNOWN'


def test_scalar_exceedance_is_valid_negative_not_amount_mismatch(tmp_path,inputs):
    p=make(tmp_path,inputs,capture(evidence_type='SCALAR_BOUND',amount_0g='',tested_amount_0g='',scalar_headroom_0g='200'))
    e=lookup(p,inputs,amount=201)
    assert e.validity['state']=='VALID' and e.status.value=='UNSUPPORTED'

@pytest.mark.parametrize('age,status',[(100,'UNSUPPORTED'),(301,'UNKNOWN')])
def test_explicit_negative_must_be_current(tmp_path,inputs,age,status):
    assert lookup(make(tmp_path,inputs,capture(admission_status='UNSUPPORTED')),inputs,age=age).status.value==status

@pytest.mark.parametrize('support_age,negative_age,status',[(100,100,'UNKNOWN'),(100,301,'SUPPORTED'),
    (301,100,'UNSUPPORTED'),(301,301,'UNKNOWN')])
def test_current_conflicts_keep_stale_provenance(tmp_path,inputs,support_age,negative_age,status):
    as_of=T+timedelta(seconds=400)
    rows=[]
    for eid,assertion,age in [('YES','SUPPORTED',support_age),('NO','UNSUPPORTED',negative_age)]:
        obs=as_of-timedelta(seconds=age)
        rows.append(record(evidence_id=eid,admission_status=assertion,
                           observation_timestamp=obs.isoformat(),retrieval_timestamp=obs.isoformat()))
    e=lookup(make(tmp_path,inputs,*rows),inputs,as_of=as_of)
    assert e.status.value==status
    assert len(e.validity_records)==2
    if max(support_age,negative_age)>300:
        assert any('STALE' in d for d in e.diagnostics)
    else:
        assert 'CONFLICTING_CAPTURE_STATUSES' in e.diagnostics[0]


def test_retrieval_not_selection_clock(tmp_path,inputs):
    p=make(tmp_path,inputs,capture(evidence_id='A'),record(evidence_id='B',retrieval_timestamp='2026-01-01T00:04:59Z'))
    assert lookup(p,inputs,age=300).capture['evidence_id']=='A'

@pytest.mark.parametrize('revalidate_age,outcome',[(300,'RECOMMENDATION_GENERATED'),(301,'SELECTED_REVALIDATION_FAILED')])
def test_selected_expiry_and_later_valid_assessment(tmp_path,inputs,revalidate_age,outcome):
    p=make(tmp_path,inputs)
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',
        admission_fn=p,as_of=T+timedelta(seconds=100),revalidation_as_of=T+timedelta(seconds=revalidate_age))
    assert r.to_dict()['outcome']==outcome
    assert (r.to_dict()['recommendation'] is None)==(revalidate_age>300)


def test_runtime_config_change_revalidation_fails(tmp_path,inputs):
    p=make(tmp_path,inputs)
    def changed(**kw):
        if kw['stage']=='REVALIDATION': p.config_contexts[SID]=RuntimeConfigContext(SID,16661,'changed','VERIFIED','test')
        return p(**kw)
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',
        admission_fn=changed,as_of=T+timedelta(seconds=100))
    assert r.revalidation=='FAILED' and r.to_dict()['recommendation'] is None

@pytest.mark.parametrize('profile',['Conservative','Balanced','Aggressive'])
def test_empty_repository_fixed_time(tmp_path,inputs,profile):
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile=profile,as_of=T)
    assert r.to_dict()['recommendation']['idle_weight']==1
    assert not r.selected


def test_ascend_gate_still_closed(tmp_path,inputs):
    row=capture(strategy_id='ASCEND_STAKE_A0G',source_role='SOURCECORE_ADMISSION',config_identity='ascend:test')
    p=make(tmp_path,inputs,row,config_contexts={'ASCEND_STAKE_A0G':RuntimeConfigContext('ASCEND_STAKE_A0G',16661,'ascend:test','VERIFIED','test')})
    e=p(strategy=inputs[0][inputs[0].strategy_id=='ASCEND_STAKE_A0G'].iloc[0],amount_0g=200,amount_usd=200,as_of=T)
    assert e.status.value=='UNKNOWN' and 'METADATA_GATE_NOT_ADMITTED' in e.diagnostics



def test_default_runner_requires_evaluation_time(inputs):
    with pytest.raises(ValueError, match='timezone-aware'):
        run_amount_optimizer(*inputs, decision_amount=1000, price_usd=1,
                             horizon_days=90, profile='Balanced')


def test_validity_engine_matches_usd_without_float_artifacts(tmp_path, inputs):
    p=make(tmp_path,inputs,capture(amount_0g='30.03',tested_amount_0g='30.03',
           amount_usd='51.051',valuation_price_usd='1.7'))
    rec=load_admission_records(p.path)[0]
    valid=assess_capture(rec,as_of=T,amount=Decimal('30.030'),usd=Decimal('51.051'),context=CONTEXT)
    mismatch=assess_capture(rec,as_of=T,amount=Decimal('30.03'),usd=Decimal('51.052'),context=CONTEXT)
    assert valid.state.value=='VALID'
    assert mismatch.state.value=='AMOUNT_MISMATCH'
