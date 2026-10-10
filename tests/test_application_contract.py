"""Current-input schema 1.4; no frozen benchmark/report changes."""
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import pytest
from src.ascend_optimizer import application_contract as a, evaluation_policy as p, risk_stress as r

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def synthetic():return a.optimize_request(decision_amount_0g=1000,evidence_mode=p.LABEL)
@pytest.fixture(scope='module')
def production():return a.optimize_request(decision_amount_0g=1000,as_of=datetime(2026,10,10,tzinfo=timezone.utc))

def test_version_and_scope(synthetic):
    assert synthetic['schema_version']=='1.4'
    assert synthetic['run_scope']==dict(scope='DECISION_SLEEVE',whole_portfolio_compliance='NOT_ASSESSED',existing_positions='EXOGENOUS_NOT_OPTIMIZED')
    assert synthetic['recommendation']['method']=='POLICY_AWARE_AMOUNT_OPTIMIZER'

def test_exact_input_fields(synthetic):
    assert synthetic['input']==dict(decision_amount_0g='1000',profile='Balanced',holding_horizon_days='90',cash_deadline_days=None,evidence_mode=p.LABEL)

@pytest.mark.parametrize('sid',r.STRATEGIES)
def test_all_five_rows_and_zero_diagnostics(synthetic,sid):
    row=next(x for x in synthetic['strategies'] if x['strategy_id']==sid)
    assert row['structural_candidate'] and row['runtime_configuration']=='UNRESOLVED'
    assert row['execution_readiness']==row['public_proof']=='NOT_ESTABLISHED'
    assert row['allocated_weight']==synthetic['recommendation']['allocation_weights'][sid]
    assert 'rejection_reasons' in row and 'binding_constraints' in row
    assert row['liquidity']['output_asset']=='native 0G'
    assert row['liquidity']['time_to_cash_days']['basis']=='MODELLED'

def test_idle_is_explicit_and_exact(synthetic):
    rec=synthetic['recommendation']
    assert sum(Decimal(v) for v in rec['allocation_weights'].values())+Decimal(rec['idle_weight'])==1
    assert Decimal(rec['idle_amount_0g'])==Decimal(rec['idle_weight'])*1000
    assert rec['allocation_weights'][r.ASCEND]=='0'
    assert synthetic['strategies'][-1]['allocation_gate']=='CLOSED'

def test_no_final_legacy_proxy(synthetic):
    assert 'lp_stress_loss_20pct' not in json.dumps(synthetic['risk'])
    assert synthetic['risk']['lp_absolute_stress']==synthetic['policy']['assessment']['constraints']['lp_absolute_stress']
    assert synthetic['risk']['staking_stress']==synthetic['policy']['assessment']['constraints']['staking_stress']
    assert 'Independent' in synthetic['risk']['qualification']

def test_selected_economics_cost_once(synthetic):
    eco=synthetic['recommendation']['economics']
    selected=[s for s in synthetic['strategies'] if Decimal(s['allocated_weight'])>0]
    assert eco['fixed_cost_usd']['value']=='8'
    assert Decimal(eco['expected_net_profit_usd']['value'])==sum(Decimal(s['economics']['expected_net_profit_usd']['value']) for s in selected)
    assert all(s['economics_basis']=='SELECTED_EXACT_AMOUNT' for s in selected)
    assert Decimal(eco['gross_income_usd']['value'])-Decimal(eco['lifecycle_cost_usd']['value'])-Decimal(eco['quote_execution_cost_usd']['value'])==Decimal(eco['expected_net_profit_usd']['value'])

def test_selected_revalidation_and_grid(synthetic):
    assert synthetic['recommendation']['revalidation_state']=='PASSED'
    assert synthetic['solver']['grid']==[0,.1,.2,.3,.4,.5,.6]
    assert synthetic['policy']['assessment']['risk_input_identities']
    assert synthetic['policy']['assessment']['exit_input_identities']

def test_recommendation_is_not_proof(synthetic):
    assert synthetic['recommendation']['state']=='RECOMMENDATION_GENERATED'
    assert synthetic['readiness']==dict(execution_readiness='NOT_ESTABLISHED',public_proof='NOT_ESTABLISHED',public_deployment='NOT_REQUIRED_NOT_PLANNED')

def test_legacy_only_current_comparison(synthetic):
    c=synthetic['comparison']['legacy_linear']
    assert c['state']=='ASSESSED' and c['cash_deadline']=='NOT_SUPPORTED' and c['profit_comparability']=='LIMITED'
    assert c['risk_namespace']=='LEGACY_COMPATIBILITY'
    assert set(synthetic['comparison'])=={'legacy_linear'}

@pytest.mark.parametrize('profile,limit', [('Conservative','0.05'),('Balanced','0.10'),('Aggressive','0.20')])
def test_production_fail_closed_all_profiles(profile,limit):
    q=a.optimize_request(decision_amount_0g=1000,profile=profile)
    assert q['recommendation']['idle_weight']=='1' and q['recommendation']['state']=='KEEP_IDLE'
    assert q['risk']['lp_absolute_stress']['limit']==limit
    assert q['policy']['state']=='NOT_ASSESSED'
    assert q['valuation']['price_usd']['value'] is None
    assert all(x['value'] is None for x in q['recommendation']['economics'].values())
    assert q['evidence']['mode']=='PRODUCTION'
    assert q['comparison']['legacy_linear']['state']=='NOT_ASSESSED'

def test_production_strategy_economics_missing_not_zero(production):
    for s in production['strategies']:
        assert s['economics_state']=='MISSING'
        assert s['economics']['expected_net_profit_usd']['value'] is None
        assert s['liquidity']['time_to_cash_days']['value'] is None
        assert s['liquidity']['deadline_state']=='NOT_REQUESTED'

@pytest.mark.parametrize('deadline', [0,1,8,15])
def test_deadline_states_and_modelled_timing(deadline):
    q=a.optimize_request(decision_amount_0g=1000,cash_deadline_days=deadline,evidence_mode=p.LABEL)
    assert q['liquidity']['cash_deadline_days']==str(deadline)
    assert q['liquidity']['holding_horizon_days']=='90'
    for s in q['strategies']:
        if Decimal(s['allocated_weight'])>0:assert s['liquidity']['deadline_state']=='COMPATIBLE_MODELLED'
    if deadline==1:
        for s in q['strategies'][:2]: assert s['allocated_weight']=='0' and s['liquidity']['deadline_state']=='INCOMPATIBLE_MODELLED'

def test_production_requested_deadline_exposes_unresolved():
    q=a.optimize_request(decision_amount_0g=1000,cash_deadline_days=1)
    assert q['recommendation']['idle_weight']=='1'
    assert q['strategies'][0]['liquidity']['deadline_state']=='UNRESOLVED'

@pytest.mark.parametrize('kw',[{'decision_amount_0g':0},{'decision_amount_0g':-1},{'decision_amount_0g':'NaN'},{'decision_amount_0g':'Infinity'},{'holding_horizon_days':0},{'cash_deadline_days':-1},{'evidence_mode':'LIVE'}])
def test_invalid_inputs_rejected(kw):
    with pytest.raises(ValueError):a.optimize_request(**(dict(decision_amount_0g=1000)|kw))

def test_existing_holdings_cannot_enter():
    with pytest.raises(TypeError):a.optimize_request(decision_amount_0g=1000,existing_holdings=500)

@pytest.mark.parametrize('path',[
 'data/runtime_strategy_config.json','data/admission_evidence.csv','data/strategy_return_evidence.json','data/lp_quote_evidence.json',
 'data/lifecycle_cost_evidence.json','data/lp_evaluation_config.json','data/evaluation_policy.json','data/risk_scenarios.json','data/exit_evaluation_config.json','data/strategies.csv',
 'results/final_evaluation_iteration23.json','results/final_evaluation_iteration23.csv','results/final_evaluation_iteration23_summary.json','data/final_evaluation_config.json'])
def test_frozen_bytes(path):
    assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show','a786d6327d952375dfe345c23374a4cee2b994a1:'+path],cwd=ROOT)

def test_all_iteration24_outputs_frozen():
    manifest=json.loads((ROOT/'results/final_results_iteration24_manifest.json').read_text())
    import hashlib
    for path,digest in manifest['output_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest

def test_no_report_or_benchmark_loading():
    source=(ROOT/'src/ascend_optimizer/application_contract.py').read_text()
    assert 'final_results' not in source and 'final_evaluation_config.json' not in source
    assert 'final_evaluation_iteration23' not in source

def test_selected_revalidation_failure_fails_closed(monkeypatch):
    from dataclasses import replace
    original=a.run_amount_optimizer
    def failed(*args,**kwargs):return replace(original(*args,**kwargs),revalidation='FAILED',revalidation_errors=('Evidence changed',))
    monkeypatch.setattr(a,'run_amount_optimizer',failed)
    q=a.optimize_request(decision_amount_0g=1000,evidence_mode=p.LABEL,cash_deadline_days=15)
    assert q['recommendation']['state']=='SELECTED_REVALIDATION_FAILED'
    assert q['recommendation']['idle_weight']=='1'
    assert all(s['allocated_weight']=='0' for s in q['strategies'])
    assert q['liquidity']['deadline_state']=='UNRESOLVED'
    assert q['solver']['revalidation_errors']==['Evidence changed']

def test_unknown_profile_rejected():
    with pytest.raises(ValueError):a.optimize_request(decision_amount_0g=1000,profile='Other')

def test_current_adapter_calls_frozen_policy_path(monkeypatch):
    original=a.run_amount_optimizer;calls=[]
    def checked(*args,**kwargs):calls.append(kwargs);return original(*args,**kwargs)
    monkeypatch.setattr(a,'run_amount_optimizer',checked)
    a.optimize_request(decision_amount_0g=1000,evidence_mode=p.LABEL,cash_deadline_days=8)
    assert calls[0]['evaluation_policy_mode']==p.LABEL and calls[0]['economics_mode']==p.LABEL
    assert calls[0]['cash_deadline_days']=='8'

def test_exact_request_input_not_display_rounded():
    q=a.optimize_request(decision_amount_0g='0.0000000000001',holding_horizon_days='90.0000000000001')
    assert q['input']['decision_amount_0g']=='0.0000000000001'
    assert q['input']['holding_horizon_days']=='90.0000000000001'
    assert q['recommendation']['idle_amount_0g']==q['input']['decision_amount_0g']

@pytest.mark.parametrize('sid',r.STRATEGIES)
def test_schema_metadata_matches_authoritative_strategy_state(synthetic,production,sid):
    from src.ascend_optimizer.data_loader import load_strategies
    from src.ascend_optimizer.strategy_state import strategy_state
    metadata=load_strategies()
    canonical=strategy_state(metadata[metadata.strategy_id==sid].iloc[0])
    for response in (synthetic,production):
        row=next(s for s in response['strategies'] if s['strategy_id']==sid)
        assert row['canonical_state']==canonical.reconciliation_category
        assert row['structural_candidate']==canonical.structural_candidate is True
        assert row['integration_state']==canonical.integration_status=='IMPLEMENTED'
        assert row['allocation_gate']==canonical.allocation_gate
        assert row['protocol_availability']==canonical.protocol_availability
        assert row['canonical_state']==('INTEGRATED_GATED' if sid==r.ASCEND else 'INTEGRATED_ALLOCATABLE')
        assert row['allocation_gate']==('CLOSED' if sid==r.ASCEND else 'CONDITIONAL')

def test_no_invented_state_in_final_contract_source():
    for path in ('src/ascend_optimizer/application_contract.py','frontend/src/lib/final-types.ts','frontend/src/lib/final-response.ts'):
        assert 'INTEGRATED_CONDITIONAL' not in (ROOT/path).read_text()

@pytest.mark.parametrize('mode,profile,deadline',[
    ('PRODUCTION','Conservative',None),('PRODUCTION','Balanced',1),('PRODUCTION','Aggressive',None),
    (p.LABEL,'Conservative',None),(p.LABEL,'Balanced',None),(p.LABEL,'Balanced',1),
    (p.LABEL,'Balanced',8),(p.LABEL,'Aggressive',15)])
def test_only_metadata_differs_from_iteration25_parent(mode,profile,deadline):
    import types
    before=types.ModuleType('src.ascend_optimizer._accepted_application_contract')
    before.__file__=str(ROOT/'src/ascend_optimizer/application_contract.py')
    before.__package__='src.ascend_optimizer'
    source=subprocess.check_output(['git','show','7933258bcc8551b66a260d1aee83bf740d05ec61:src/ascend_optimizer/application_contract.py'],cwd=ROOT)
    exec(compile(source,before.__file__,'exec'),before.__dict__)
    args=dict(decision_amount_0g=1000,profile=profile,cash_deadline_days=deadline,evidence_mode=mode,
              as_of=datetime(2026,10,10,tzinfo=timezone.utc))
    old=before.optimize_request(**args);new=a.optimize_request(**args)
    for old_row,new_row in zip(old['strategies'],new['strategies']):
        for field in ('canonical_state','protocol_availability'):
            old_row.pop(field);new_row.pop(field)
    assert old==new
