"""Actual-config loader tests. All VERIFIED proofs below are synthetic temporary fixtures."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from src.ascend_optimizer.runtime_config import (
    DEFAULT_RUNTIME_CONFIG_PATH, ROUTE_FIELDS, ADDRESS_FIELDS, config_fingerprint,
    canonical_serialization, load_runtime_configs, runtime_config_contexts,
)
from src.ascend_optimizer.admission_provider import RepositoryAdmissionProvider
from src.ascend_optimizer.amount_optimizer import run_amount_optimizer
from src.ascend_optimizer.data_loader import MVP_STRATEGY_IDS, SchemaValidationError
from test_admission_evidence import inputs, record, write

T=datetime(2026,1,1,tzinfo=timezone.utc)


def dataset():
    return json.loads(DEFAULT_RUNTIME_CONFIG_PATH.read_text())


def complete(row,index=1):
    """Hypothetical registration and chain-code assertions, not live evidence."""
    row=deepcopy(row);sid=row['strategy_id'];c=row['config_components']
    for n,key in enumerate(ROUTE_FIELDS[sid]):
        if key in ADDRESS_FIELDS and c[key] is None: c[key]='0x'+format(index*100+n+1,'040x')
    c['manager_strategy_key']='0x'+format(index,'064x')
    if sid=='GIMO_STAKE_0G': c['referral']=''
    if sid in {'JAINE_LP_0G_USDC','OKU_LP_0G_USDC'}:
        c.update(token0=c['w0g'],token1=c['usdce'],fee_tier=3000,tick_spacing=60,
                 tick_lower=-60,tick_upper=60,sqrt_lower_x96=100,sqrt_upper_x96=200,target_usdc_bps=5000)
    row.update(verification_state='VERIFIED',verification_source='SYNTHETIC_ROUTE_PROOF',
               verified_at='2026-01-01T00:00:00Z')
    row['evidence_sources']=[{'source_id':'SYNTHETIC_ROUTE_PROOF','source_type':'ONCHAIN_READ',
        'location':'synthetic://temporary-test-only','chain_id':16661,
        'verified_components':list(ROUTE_FIELDS[sid])+['execution_chain_id','strategy_id'],
        'code_verified_addresses':[c[k] for k in c if k in ADDRESS_FIELDS]}]
    row['config_identity']=config_fingerprint(sid,16661,c)
    return row


def put(tmp_path,data):
    p=tmp_path/'configs.json';p.write_text(json.dumps(data));return p


def test_repository_five_explicit_unresolved_records():
    records=load_runtime_configs()
    assert len(records)==5 and {r['strategy_id'] for r in records}==MVP_STRATEGY_IDS
    assert all(r['verification_state']=='UNRESOLVED' and r['config_identity'] is None for r in records)
    contexts=runtime_config_contexts()
    assert all(c.verification_state=='UNRESOLVED' and not c.config_identity for c in contexts.values())

@pytest.mark.parametrize('index',range(5))
def test_deterministic_complete_identity_order_case_and_component_change(index):
    row=complete(dataset()['records'][index],index+1);sid=row['strategy_id'];c=row['config_components']
    original=config_fingerprint(sid,16661,c)
    assert original==config_fingerprint(sid,16661,dict(reversed(list(c.items()))))
    upper={k:('0x'+v[2:].upper() if k in ADDRESS_FIELDS else v) for k,v in c.items()}
    assert original==config_fingerprint(sid,16661,upper)
    changed=dict(c,adapter_address='0x'+'f'*40)
    assert original!=config_fingerprint(sid,16661,changed)
    assert original!=config_fingerprint(sid,16602,c)
    assert original=='sha256:'+hashlib.sha256(canonical_serialization(sid,16661,c).encode()).hexdigest()

@pytest.mark.parametrize('field',['validator','stake_pool','pool','tick_lower','withdrawal_queue'])
def test_missing_component_cannot_verify(tmp_path,field):
    d=dataset();index=next(i for i,r in enumerate(d['records']) if field in r['config_components'])
    d['records'][index]=complete(d['records'][index]);d['records'][index]['config_components'][field]=None
    with pytest.raises(SchemaValidationError,match='missing required component'): load_runtime_configs(put(tmp_path,d))

@pytest.mark.parametrize('change', ['source','time','identity','coverage','code','chain','unknown_strategy','duplicate','unresolved_identity','market_only'])
def test_invalid_verification_rejected(tmp_path,change):
    d=dataset();r=complete(d['records'][1]);d['records'][1]=r
    if change=='source': r['verification_source']=None
    elif change=='time': r['verified_at']=None
    elif change=='identity': r['config_identity']='sha256:'+'0'*64
    elif change=='coverage': r['evidence_sources'][0]['verified_components']=[]
    elif change=='code': r['evidence_sources'][0]['code_verified_addresses']=[]
    elif change=='chain': r['execution_chain_id']=16602
    elif change=='unknown_strategy': r['strategy_id']='MORPHO_LEND_0G'
    elif change=='duplicate': d['records'].append(deepcopy(d['records'][0]))
    elif change=='unresolved_identity': r['verification_state']='UNRESOLVED'
    else: r['evidence_sources'][0]['source_type']='MARKET_OBSERVATION'
    with pytest.raises(SchemaValidationError): load_runtime_configs(put(tmp_path,d))


def test_verified_contexts_from_explicit_complete_synthetic_proofs(tmp_path):
    d=dataset();d['records']=[complete(r,i+1) for i,r in enumerate(d['records'])]
    contexts=runtime_config_contexts(put(tmp_path,d))
    assert len(contexts)==5 and all(c.verification_state=='VERIFIED' and c.verification_source=='SYNTHETIC_ROUTE_PROOF' for c in contexts.values())


def test_native_gimo_do_not_use_samples_tvl_rates():
    byid={r['strategy_id']:r for r in load_runtime_configs()}
    assert byid['NATIVE_STAKE_0G']['config_components']['validator'] is None
    assert byid['GIMO_STAKE_0G']['config_components']['referral'] is None
    assert all(not {'tvl_usd','liquidity_usd','exchange_rate','gross_apy','delegation_depth'}.intersection(r['config_components']) for r in byid.values())


def test_lp_routes_independently_bound_and_no_dynamic_pool_selection():
    rows={r['strategy_id']:r for r in load_runtime_configs()}
    j=rows['JAINE_LP_0G_USDC'];o=rows['OKU_LP_0G_USDC']
    for k in ('factory','router','position_manager','router_mode'): assert j['config_components'][k]!=o['config_components'][k]
    for r in (j,o):
        for k in ('pool','token0','token1','fee_tier','tick_lower','tick_upper','target_usdc_bps'):
            assert r['config_components'][k] is None
    jc=complete(j);oc=complete(o,2)
    assert jc['config_identity']!=oc['config_identity']
    for key,value in [('pool','0x'+'b'*40),('fee_tier',500),('tick_lower',-120),('target_usdc_bps',4000)]:
        assert jc['config_identity']!=config_fingerprint(j['strategy_id'],16661,dict(jc['config_components'],**{key:value}))


def test_repository_provider_reload_config_mismatch_and_revalidation(tmp_path,inputs):
    d=dataset();d['records'][1]=complete(d['records'][1]);path=put(tmp_path,d)
    sid='GIMO_STAKE_0G';identity=d['records'][1]['config_identity']
    captures=write(tmp_path/'captures.csv',record(config_identity=identity,retrieval_timestamp='2026-01-01T00:00:00Z'))
    p=RepositoryAdmissionProvider(captures,strategies=inputs[0],runtime_config_path=path)
    meta=inputs[0][inputs[0].strategy_id==sid].iloc[0]
    assert p(strategy=meta,amount_0g=200,amount_usd=200,as_of=T).status.value=='SUPPORTED'
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',admission_fn=p,as_of=T)
    assert r.revalidation=='PASSED'
    d['records'][1]['config_components']['referral']='different-route-referral'
    d['records'][1]['config_identity']=config_fingerprint(sid,16661,d['records'][1]['config_components'])
    def change(**kw):
        if kw['stage']=='REVALIDATION': path.write_text(json.dumps(d))
        return p(**kw)
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',admission_fn=change,as_of=T)
    assert r.revalidation=='FAILED' and r.to_dict()['recommendation'] is None
    e=p(strategy=meta,amount_0g=200,amount_usd=200,as_of=T)
    assert e.status.value=='UNKNOWN' and e.validity['state']=='CONFIG_MISMATCH'


def test_verified_config_absent_admission_unknown(tmp_path,inputs):
    d=dataset();d['records'][1]=complete(d['records'][1]);path=put(tmp_path,d)
    p=RepositoryAdmissionProvider(write(tmp_path/'empty.csv'),strategies=inputs[0],runtime_config_path=path)
    e=p(strategy=inputs[0][inputs[0].strategy_id=='GIMO_STAKE_0G'].iloc[0],amount_0g=200,amount_usd=200,as_of=T)
    assert e.status.value=='UNKNOWN' and e.validity['state']=='MISSING'


def test_verified_ascend_config_does_not_open_gate(tmp_path,inputs):
    d=dataset();d['records'][4]=complete(d['records'][4]);path=put(tmp_path,d)
    captures=write(tmp_path/'ascend.csv',record(strategy_id='ASCEND_STAKE_A0G',source_role='SOURCECORE_ADMISSION',
        config_identity=d['records'][4]['config_identity'],retrieval_timestamp='2026-01-01T00:00:00Z'))
    p=RepositoryAdmissionProvider(captures,strategies=inputs[0],runtime_config_path=path)
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',admission_fn=p,as_of=T)
    assert not any(c.eligible for c in r.candidates if c.strategy_id=='ASCEND_STAKE_A0G' and c.weight>0)

@pytest.mark.parametrize('profile',['Conservative','Balanced','Aggressive'])
def test_empty_repository_still_idle(profile,inputs):
    before=Path('data/admission_evidence.csv').read_bytes()
    r=run_amount_optimizer(*inputs,decision_amount=1000,price_usd=1,horizon_days=90,profile=profile,as_of=T)
    assert not r.selected and r.to_dict()['recommendation']['idle_weight']==1
    assert Path('data/admission_evidence.csv').read_bytes()==before
    assert len(before.splitlines())==1
    assert len({c.strategy_id for c in r.candidates})==5
    assert 'W0G' not in {c.strategy_id for c in r.candidates}


def test_missing_runtime_dataset_fails_closed(tmp_path,inputs):
    p=RepositoryAdmissionProvider(runtime_config_path=tmp_path/'missing.json',strategies=inputs[0])
    e=p(strategy=inputs[0].iloc[1],amount_0g=200,amount_usd=200,as_of=T)
    assert e.status.value=='UNKNOWN' and 'CONFIG_DATASET_UNUSABLE' in e.diagnostics[0]
