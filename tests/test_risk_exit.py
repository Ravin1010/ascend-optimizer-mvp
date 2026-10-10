"""SYNTHETIC_EVALUATION_ONLY risk/exit semantics and fail-closed boundaries."""
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal, ROUND_DOWN, localcontext
import json
from pathlib import Path
import subprocess

import pytest

from src.ascend_optimizer import risk_stress as r, exit_liquidity as e, lp_range_stress as lp
from src.ascend_optimizer.data_loader import DEFAULT_DATA_DIR, load_strategies, SchemaValidationError
from src.ascend_optimizer.runtime_config import load_runtime_configs
from src.ascend_optimizer.profiles import get_profile
from tools.risk_exit_preflight import risk_replay, exit_replay
from tools.economics_preflight import repository_baseline


def scenario(suffix):
    return next(s for s in r.load_scenarios() if s['scenario_id'].endswith(':'+suffix))


def assessed(sid,notional='1000'):
    suffix={r.NATIVE:'NATIVE_STAKING_5PCT',r.GIMO:'GIMO_UNDERLYING_5PCT',r.JAINE:'LP_WORST_ABSOLUTE',
            r.OKU:'LP_WORST_ABSOLUTE',r.ASCEND:'ASCEND_ECONOMIC_HAIRCUT'}[sid]
    config=next((c for c in lp.load_configs() if c['strategy_id']==sid),None)
    return r.assess(sid,scenario(suffix),notional,mode=r.LABEL,lp_config=config)


def budget(weights=None, *, allow_closed_analysis=True):
    weights=weights or {sid:'0.2' for sid in r.STRATEGIES}
    rows=[assessed(sid,str(Decimal('5000')*Decimal(weights[sid]))) for sid in r.STRATEGIES]
    return r.aggregate(rows,weights,'5000',mode=r.LABEL,allow_closed_analysis=allow_closed_analysis)


def exit_config(sid):
    return next(c for c in e.load_configs() if c['strategy_id']==sid)


def test_exact_five_versioned_risk_and_exit_strategies():
    assert set(r.STRATEGIES)=={r.NATIVE,r.GIMO,r.JAINE,r.OKU,r.ASCEND}
    assert set().union(*(set(s['strategies']) for s in r.load_scenarios()))==set(r.STRATEGIES)
    assert set(e.PATHS)==set(r.STRATEGIES)
    assert {c['strategy_id'] for c in e.load_configs()}==set(r.STRATEGIES)
    assert len(r.STRATEGIES)==5 and 'W0G' not in r.STRATEGIES
    assert all(s['version']==r.SCENARIO_VERSION and s['label']==r.LABEL for s in r.load_scenarios())


@pytest.mark.parametrize('changes', [
    {'scenario_id':'unknown'}, {'version':'V2'},{'label':'LIVE'}, {'evidence_class':'LIVE_OBSERVED'},
    {'probability':'0.5'}, {'severity':'-0.01'}, {'severity':'1.01'}, {'severity':'NaN'}, {'severity':'Infinity'},
    {'severity':'0.1'}, {'strategies':[r.NATIVE,r.GIMO]}, {'assumptions':[]},
])
def test_invalid_or_promoted_scenario_rejected(changes):
    s=scenario('NATIVE_STAKING_5PCT')|changes
    with pytest.raises(r.RiskError): r.validate_scenario(s)


def test_no_probabilities_or_shared_causal_event():
    a,b=assessed(r.NATIVE),assessed(r.GIMO)
    assert a.severity==b.severity=='0.05'
    assert a.scenario_id!=b.scenario_id and a.scenario_fingerprint!=b.scenario_fingerprint
    assert b.diagnostics['shared_severity_not_shared_event']
    assert not any('probability' in s for s in r.load_scenarios())
    out=budget();assert out['joint_event_assumed'] is False and out['correlation']=='UNRESOLVED_NOT_INFERRED'
    assert out['aggregation_rule']==r.ENVELOPE


@pytest.mark.parametrize('sid',[r.NATIVE,r.GIMO])
def test_underlying_staking_exposure_loss_and_missing_concentration(sid):
    x=assessed(sid)
    assert x.stressed_exposure_amount=='1000' and Decimal(x.absolute_stressed_loss)==50
    assert Decimal(x.loss_fraction)==Decimal('.05') and x.risk_assessment_state=='ASSESSED_MODELLED'
    assert x.evidence_class=='MODELLED' and x.stress_basis=='MODELLED'
    if sid==r.NATIVE: assert x.diagnostics['configured_validator_concentration']=='UNRESOLVED'
    else:
        assert x.diagnostics['causal_losses_applied']==1
        assert x.diagnostics['gimo_specific_protocol_severity'] is None


@pytest.mark.parametrize('sid',[r.JAINE,r.OKU])
def test_lp_range_total_loss_not_il_plus_market(sid):
    x=assessed(sid);d=x.diagnostics
    cfg=next(c for c in lp.load_configs() if c['strategy_id']==sid)
    points=[lp.evaluate(cfg,s,'1000',mode=r.LABEL,expected_config_id=cfg['config_id']) for s in lp.scenarios()]
    worst=max(points,key=lambda p:Decimal(p.absolute_lp_loss))
    assert d['worst_lp_scenario_id']==worst.scenario_id
    assert Decimal(x.loss_fraction)==Decimal(d['lp_absolute_stress_loss'])
    assert float(x.absolute_stressed_loss)==pytest.approx(1000*float(worst.absolute_lp_loss))
    assert float(x.absolute_stressed_loss)!=pytest.approx(1000*(float(worst.absolute_lp_loss)-float(worst.impermanent_loss_fraction)+float(worst.hodl_market_loss)))
    assert d['only_absolute_loss_aggregated'] and not d['fees_execution_costs_included']
    assert d['lp_config_id']==cfg['config_id']
    assert len(d['shock_results_per_unit'])==4
    assert x==assessed(sid)


def test_lp_requires_correct_config_and_does_not_import_generic_proxy():
    s=scenario('LP_WORST_ABSOLUTE');j,o=lp.load_configs()
    with pytest.raises(r.RiskError): r.assess(r.JAINE,s,'1000',mode=r.LABEL)
    with pytest.raises(r.RiskError): r.assess(r.JAINE,s,'1000',mode=r.LABEL,lp_config=o)
    assert 'lp_execution' not in Path(r.__file__).read_text()
    assert 'MODELLED_LP_STRESS_20PCT' not in Path(r.__file__).read_text()
    # No snapshot/legacy proxy argument exists on the new risk path.
    with pytest.raises(TypeError): r.assess(r.JAINE,s,'1000',mode=r.LABEL,lp_config=j,lp_stress_loss_20pct='0')


def test_ascend_one_haircut_not_embedded_double_count_and_gate():
    x=assessed(r.ASCEND)
    assert Decimal(x.absolute_stressed_loss)==50
    assert x.risk_assessment_state=='PARTIALLY_ASSESSED'
    assert x.allocation_gate=='CLOSED'
    assert x.diagnostics['queue_funding_severity'] is None
    assert x.diagnostics['remote_dependency_severity'] is None
    assert x.diagnostics['oracle_accounting_severity'] is None
    assert 'not additive' in x.diagnostics['embedded_mellow_symbiotic']
    with pytest.raises(r.RiskError,match='CLOSED'): budget(allow_closed_analysis=False)


def test_missing_severity_stays_unresolved_and_blocks_positive_budget():
    x=r.assess(r.ASCEND,scenario('ASCEND_DEPENDENCIES_UNRESOLVED'),'1000',mode=r.LABEL)
    assert x.severity is None and x.loss_fraction is None and x.absolute_stressed_loss is None
    assert not x.aggregation_eligible and x.risk_assessment_state=='UNRESOLVED'
    rows=[x if sid==r.ASCEND else assessed(sid) for sid in r.STRATEGIES]
    out=r.aggregate(rows,{sid:'0.2' for sid in r.STRATEGIES},'5000',mode=r.LABEL,allow_closed_analysis=True)
    assert out['total_decision_sleeve_stress_loss'] is None and out['total_loss_fraction'] is None
    assert out['unresolved_positive_allocations']==[r.ASCEND]


def test_portfolio_weighted_budget_and_zero_unresolved_allocation():
    out=budget()
    assert float(out['total_decision_sleeve_stress_loss'])==pytest.approx(sum(float(x['absolute_strategy_stress_loss']) for x in out['rows']))
    assert float(out['total_loss_fraction'])==pytest.approx(sum(float(x['weighted_contribution']) for x in out['rows']))
    assert float(out['total_loss_fraction'])==pytest.approx(float(out['total_decision_sleeve_stress_loss'])/5000)
    weights={sid:('0' if sid==r.ASCEND else '0.2') for sid in r.STRATEGIES}
    rows=[r.assess(r.ASCEND,scenario('ASCEND_DEPENDENCIES_UNRESOLVED'),'0',mode=r.LABEL) if sid==r.ASCEND else assessed(sid) for sid in r.STRATEGIES]
    z=r.aggregate(rows,weights,'5000',mode=r.LABEL)
    az=next(x for x in z['rows'] if x['strategy_id']==r.ASCEND)
    assert az['weighted_contribution']=='0' and az['absolute_strategy_stress_loss']=='0'
    assert az['strategy_stress_loss_fraction'] is None and z['state']=='ASSESSED_MODELLED'
    assert Decimal(z['idle_weight'])==Decimal('.2')


@pytest.mark.parametrize('changes',[{'loss_fraction':'1.01'},{'loss_fraction':'-1'}, {'absolute_stressed_loss':'2000'},
                                    {'allocation_value':'999'}, {'evidence_class':'LIVE_DERIVED'}, {'label':'LIVE'},
                                    {'aggregation_eligible':False}])
def test_invalid_risk_result_rejected_during_aggregation(changes):
    rows=[assessed(sid) for sid in r.STRATEGIES];rows[0]=replace(rows[0],**changes)
    with pytest.raises(r.RiskError): r.aggregate(rows,{s:'0.2' for s in r.STRATEGIES},'5000',mode=r.LABEL,allow_closed_analysis=True)


def test_profile_mapping_no_silent_il_threshold_reuse():
    b=budget();p=get_profile('Conservative');out=r.profile_constraints(b,'Conservative')
    assert out['max_portfolio_lp_il_stress']['limit']==str(p.max_portfolio_lp_il_stress)
    assert out['max_portfolio_lp_il_stress']['result']=='LEGACY_COMPATIBILITY_ONLY_NOT_APPLIED_TO_ABSOLUTE_LOSS'
    assert out['max_decision_sleeve_lp_absolute_stress_loss']['result']=='UNRESOLVED'
    assert r.profile_constraints(b,'Conservative',lp_absolute_limit='0.001')['max_decision_sleeve_lp_absolute_stress_loss']['result']=='FAIL'
    assert r.profile_constraints(b,'Conservative',lp_absolute_limit='0.2')['max_decision_sleeve_lp_absolute_stress_loss']['result']=='PASS'
    assert out['max_strategy_concentration']['result']=='PASS'
    assert out['max_slashing_stress_loss']['result']=='PASS'
    assert 'REMOTE_DEPENDENCY_IS_NOT_USER_CAPITAL_BRIDGE' in out['max_bridge_exposure']['result']
    assert out['overall_risk_clearance']=='NOT_ESTABLISHED'


@pytest.mark.parametrize('sid,kind', [(r.NATIVE,'ASYNCHRONOUS'),(r.GIMO,'ASYNCHRONOUS'),(r.JAINE,'SYNCHRONOUS'),(r.OKU,'SYNCHRONOUS'),(r.ASCEND,'QUEUE_BASED')])
def test_exit_source_path_unresolved_runtime_and_native_output(sid,kind):
    x=e.assess(sid)
    assert x.exit_type==kind and x.output_asset=='native 0G'
    assert x.request_step and x.waiting_step and x.claim_step
    assert x.requestable_now_state==x.claimability_state==x.maturity_state==x.funding_state=='UNRESOLVED'
    assert x.time_to_cash_days is None and x.timing_evidence_class=='MISSING'
    assert x.execution_readiness=='NOT_ESTABLISHED'
    if kind=='SYNCHRONOUS':
        assert x.waiting_maturity_days==x.funding_wait_days=='0'
        assert x.qualification_state=='PARTIALLY_ASSESSED'
        assert 'NOT_ASSESSED' in x.quote_validity
    else: assert x.waiting_maturity_days is None and x.qualification_state=='UNRESOLVED'
    if sid==r.ASCEND: assert x.allocation_gate=='CLOSED'


@pytest.mark.parametrize('sid',r.STRATEGIES)
def test_synthetic_exit_stage_sums_and_separate_horizon(sid):
    c=exit_config(sid);x=e.assess(sid,mode=r.LABEL,config=c,holding_horizon_days='90')
    assert x.time_to_cash_days==str(sum(Decimal(c[k]) for k in e.DURATIONS))
    assert x.evidence_class==x.timing_evidence_class=='MODELLED' and x.qualification_state=='ASSESSED_MODELLED'
    assert x.holding_horizon_days=='90'
    assert x.time_to_cash_days==e.assess(sid,mode=r.LABEL,config=c,holding_horizon_days='1').time_to_cash_days
    assert x.requestable_now_state=='ASSUMED_REQUESTABLE_FOR_EVALUATION'
    assert x.claimability_state.startswith('CONDITIONAL_ON')
    assert x.output_asset=='native 0G' and x.execution_readiness=='NOT_ESTABLISHED'
    assert x.config_fingerprint==r.fingerprint(c)
    with pytest.raises(r.RiskError): e.assess(sid,config=c)


@pytest.mark.parametrize('field,value',[('waiting_maturity_days','-1'),('waiting_maturity_days','NaN'),('claim_processing_days','Infinity'),
                                        ('label','LIVE'),('evidence_class','LIVE_OBSERVED'),('version','V2'),('config_id','other')])
def test_invalid_exit_timing_or_promotion_rejected(field,value):
    c=exit_config(r.NATIVE)|{field:value}
    with pytest.raises(r.RiskError): e.assess(r.NATIVE,mode=r.LABEL,config=c)


def test_missing_exit_wait_is_not_zero_deadline_tristate():
    c=exit_config(r.ASCEND)|{'waiting_maturity_days':None}
    x=e.assess(r.ASCEND,mode=r.LABEL,config=c)
    assert x.time_to_cash_days is None and x.waiting_maturity_days is None
    assert x.qualification_state=='UNRESOLVED' and x.maturity_state=='UNRESOLVED'
    assert e.deadline_compatible(x,'30')=='UNRESOLVED'
    y=e.assess(r.NATIVE,mode=r.LABEL,config=exit_config(r.NATIVE))
    assert e.deadline_compatible(y,'8')=='COMPATIBLE_MODELLED'
    assert e.deadline_compatible(y,'7')=='INCOMPATIBLE_MODELLED'
    with pytest.raises(r.RiskError): e.deadline_compatible(y,'-1')


def test_synchronous_cannot_acquire_protocol_queue_and_config_mismatch():
    c=exit_config(r.JAINE)|{'waiting_maturity_days':'1'}
    with pytest.raises(r.RiskError): e.assess(r.JAINE,mode=r.LABEL,config=c)
    with pytest.raises(r.RiskError): e.assess(r.OKU,mode=r.LABEL,config=exit_config(r.JAINE))


def test_risk_synthetic_only_and_not_admission():
    with pytest.raises(r.RiskError): r.assess(r.NATIVE,scenario('NATIVE_STAKING_5PCT'),'1000',mode='PRODUCTION')
    with pytest.raises(r.RiskError): r.assess(r.GIMO,scenario('NATIVE_STAKING_5PCT'),'1000',mode=r.LABEL)
    with pytest.raises(SchemaValidationError): load_runtime_configs(DEFAULT_DATA_DIR/'risk_scenarios.json')
    with pytest.raises(SchemaValidationError): load_runtime_configs(DEFAULT_DATA_DIR/'exit_evaluation_config.json')


def test_replay_artifacts_and_precision_determinism():
    root=DEFAULT_DATA_DIR.parent
    expected=risk_replay()
    assert json.loads((root/'results/risk_stress_iteration21.json').read_text())==expected
    assert json.loads((root/'results/exit_liquidity_iteration21.json').read_text())==exit_replay()
    with localcontext() as ctx:
        ctx.prec=12;ctx.rounding=ROUND_DOWN
        assert risk_replay()==expected


def test_frozen_state_and_baseline():
    assert all(x['verification_state']=='UNRESOLVED' for x in load_runtime_configs())
    assert len((DEFAULT_DATA_DIR/'admission_evidence.csv').read_text().splitlines())==1
    for name in ('strategy_return_evidence.json','lp_quote_evidence.json','lifecycle_cost_evidence.json'):
        assert json.loads((DEFAULT_DATA_DIR/name).read_text())['records']==[]
    assert load_strategies().set_index('strategy_id').loc[r.ASCEND,'allocation_gate']=='CLOSED'
    assert all(x['idle_weight']==1 and x['positive_selected_count']==0 for x in repository_baseline()['runs'])
    # Freeze the exact Iteration 20 configuration, not just its evidence label.
    root=DEFAULT_DATA_DIR.parent
    before=subprocess.check_output(['git','show','a02844c802c781cf056b79c59172d719aaaf990a:data/lp_evaluation_config.json'],cwd=root)
    assert before==(DEFAULT_DATA_DIR/'lp_evaluation_config.json').read_bytes()
