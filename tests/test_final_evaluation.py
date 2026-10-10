"""Final deterministic synthetic evaluation contract and replay assertions."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import subprocess

import pytest
from src.ascend_optimizer import final_evaluation as f, risk_stress as r, evaluation_policy as p
from src.ascend_optimizer.evaluation_baselines import allocate, METHODS
from src.ascend_optimizer.final_evaluation_inputs import SyntheticInputs
from src.ascend_optimizer.amount_optimizer import candidate_grid
from src.ascend_optimizer.profiles import get_profile

ROOT=f.ROOT


@pytest.fixture(scope='module')
def benchmark():
    return f.replay()


def row(benchmark,id,method=METHODS[3]):
    return next(x for x in benchmark[0]['rows'] if x['scenario_id']==id and x['method_id']==method)


def test_contract_exact_matrix_and_synthetic_package():
    q=f.load_config()
    assert q['version']==f.VERSION and tuple(q['methods'])==METHODS and len(METHODS)==4
    assert len(q['scenarios'])==49 and sum(s['kind']=='CORE' for s in q['scenarios'])==27
    assert {s['scenario_id'] for s in q['scenarios'] if s['kind']=='TARGETED'}==f.TARGET_IDS
    assert all(s['label']==f.LABEL and s['version']==f.SCENARIOS and s['purpose'] and s['expected_behavioral_hypothesis'] for s in q['scenarios'])
    assert q['ascend_gate']=='CLOSED' and q['scope']=='DECISION_SLEEVE'
    assert q['whole_portfolio_compliance']=='NOT_ASSESSED'


@pytest.mark.parametrize('change',[{'version':'V2'},{'methods':list(METHODS)+['OTHER']},{'label':'LIVE'}, {'ascend_gate':'OPEN'}])
def test_config_boundaries_reject(tmp_path,change):
    q=f.load_config()|change;path=tmp_path/'config.json';path.write_text(json.dumps(q))
    with pytest.raises(ValueError):f.load_config(path)


@pytest.mark.parametrize('field,value',[('scenario_id','unknown'),('version','V2'),('label','LIVE'),('cash_deadline_days','-1')])
def test_scenario_identity_validation(tmp_path,field,value):
    q=f.load_config();q['scenarios'][-1][field]=value;path=tmp_path/'config.json';path.write_text(json.dumps(q))
    with pytest.raises(ValueError):f.load_config(path)


def test_highest_rank_and_tie():
    w,idle=allocate(METHODS[0],{r.NATIVE:'.1',r.GIMO:'.2',r.JAINE:'.3'},'.6',r.STRATEGIES)
    assert w[r.JAINE]==Decimal('.6') and w[r.GIMO]==Decimal('.4') and idle==0
    w,_=allocate(METHODS[0],{r.NATIVE:'.2',r.GIMO:'.2'},'.6',r.STRATEGIES)
    assert w[r.GIMO]==Decimal('.6') and w[r.NATIVE]==Decimal('.4')


@pytest.mark.parametrize('method',METHODS[:2])
def test_simple_gate_and_negative_idle(method):
    w,idle=allocate(method,{r.ASCEND:'100',r.NATIVE:'-.1'},'.6',r.STRATEGIES)
    assert idle==1 and w[r.ASCEND]==0


@pytest.mark.parametrize('n,cap,expected_idle',[(1,'.4','.6'),(2,'.4','.2'),(4,'.6','0')])
def test_equal_target_capped_no_redistribution(n,cap,expected_idle):
    eligible=list(r.STRATEGIES[:n]);w,idle=allocate(METHODS[1],dict.fromkeys(eligible,'.1'),cap,r.STRATEGIES)
    assert len({w[s] for s in eligible})==1 and idle==Decimal(expected_idle)
    assert sum(w.values())+idle==1


def test_legacy_actual_implementation_and_adapter(benchmark,monkeypatch):
    q=f.load_config();inputs=SyntheticInputs(q,q['scenarios'][1]);table=f.legacy_candidates(inputs)
    native=table[table.strategy_id==r.NATIVE].iloc[0]
    point=inputs.point(r.NATIVE,q['scenarios'][1]['decision_amount_0g'])
    assert native.net_return_horizon==point.net_return_horizon
    called=[];original=f.optimize_portfolio
    def spy(*args,**kw):called.append(1);return original(*args,**kw)
    monkeypatch.setattr(f,'optimize_portfolio',spy)
    out=f.normalize(q,q['scenarios'][1],METHODS[2]);assert called==[1]
    assert out['diagnostics']['implementation'].endswith('optimize_portfolio')
    assert out['supported_feature_flags']['lp_quote_effects']=='APPROXIMATED'
    assert out['supported_feature_flags']['legacy_lp_proxy']=='LEGACY_ONLY'
    assert out['deadline_compatibility']=='NOT_SUPPORTED'


def test_final_actual_path_mode_grid_revalidation(benchmark,monkeypatch):
    original=f.run_amount_optimizer;called=[]
    def spy(*args,**kw):
        assert kw['economics_mode']==kw['evaluation_policy_mode']==f.LABEL
        called.append(1);return original(*args,**kw)
    monkeypatch.setattr(f,'run_amount_optimizer',spy)
    q=f.load_config();out=f.normalize(q,next(s for s in q['scenarios'] if s['scenario_id']=='FIXED_1000'),METHODS[3])
    assert called==[1] and out['diagnostics']['selected_revalidation']=='PASSED'
    assert out['diagnostics']['policy_revalidation_calls']==1
    assert out['diagnostics']['grid']==[f.fmt(w) for w in candidate_grid(get_profile('Balanced'))]


@pytest.mark.parametrize('id',['FIXED_100','NEGATIVE','MISSING_RETURN','ADMISSION_FAILURE','ASCEND_ATTRACTIVE','QUOTE_MISMATCH','MISSING_COST'])
def test_fail_closed_final_idle(benchmark,id):
    q=row(benchmark,id);assert q['idle_weight']=='1' and q['recommendation_state']=='IDLE_ALLOWED'
    assert q['final_policy_feasibility']=='PASS'


def test_fixed_cost_and_notional_sensitivity(benchmark):
    assert row(benchmark,'FIXED_100')['idle_weight']=='1'
    for id in ['FIXED_1000','FIXED_10000','FIXED_ZERO_CONTROL']:
        assert Decimal(row(benchmark,id)['allocation_weights'][r.NATIVE])>0
    assert benchmark[1]['fixed_cost_changes_decision_count']==1


def test_lp_quote_amount_and_pair_changes(benchmark):
    a=row(benchmark,'QUOTE_CURVE');b=row(benchmark,'QUOTE_CONSTANT_CONTROL')
    assert Decimal(a['allocation_weights'][r.JAINE])<Decimal(b['allocation_weights'][r.JAINE])
    assert benchmark[1]['quote_effect_changes_decision_count']==1
    q=f.load_config();s=next(s for s in q['scenarios'] if s['scenario_id']=='QUOTE_CURVE');inputs=SyntheticInputs(q,s)
    small=inputs.point(r.JAINE,'100');large=inputs.point(r.JAINE,'200')
    assert small.entry_slippage_rate<large.entry_slippage_rate
    assert small.evidence['quotes'][0]['amount_0g']=='100'


def test_lp_progression(benchmark):
    assert [row(benchmark,'LP_PROGRESSION_'+profile.upper())['allocation_weights'][r.JAINE] for profile in f.PROFILES]==['0.3','0.6','0.8']


def test_deadline_exclusion_restoration_and_unsupported(benchmark):
    tight=row(benchmark,'DEADLINE_STAKING_1');moderate=row(benchmark,'DEADLINE_STAKING_8');relaxed=row(benchmark,'DEADLINE_STAKING_15')
    assert tight['allocation_weights'][r.NATIVE]==tight['allocation_weights'][r.GIMO]=='0'
    assert moderate['allocation_weights'][r.NATIVE]=='0.6' and moderate['allocation_weights'][r.GIMO]=='0'
    assert Decimal(relaxed['allocation_weights'][r.GIMO])>0
    for m in METHODS[:3]:assert row(benchmark,'DEADLINE_STAKING_1',m)['deadline_compatibility']=='NOT_SUPPORTED'


@pytest.mark.parametrize('method',METHODS)
def test_gate_scope_and_readiness_all_rows(benchmark,method):
    rows=[q for q in benchmark[0]['rows'] if q['method_id']==method]
    assert len(rows)==49
    assert all(q['allocation_weights'][r.ASCEND]=='0' for q in rows)
    assert all(q['whole_portfolio_compliance']=='NOT_ASSESSED' and q['execution_readiness']=='NOT_ESTABLISHED'
               and q['public_live_proof_state']=='NOT_ESTABLISHED' and q['evidence_mode']==f.LABEL for q in rows)


def test_shared_inputs_and_exact_weight_columns(benchmark):
    for s in f.load_config()['scenarios']:
        rows=[row(benchmark,s['scenario_id'],m) for m in METHODS]
        assert len({json.dumps(q['valuation'],sort_keys=True) for q in rows})==1
        assert all(q['decision_amount_0g']==s['decision_amount_0g'] and q['holding_horizon_days']==s['holding_horizon_days'] for q in rows)
        for q in rows:
            assert set(q['allocation_weights'])==set(r.STRATEGIES)
            assert sum(Decimal(w) for w in q['allocation_weights'].values())+Decimal(q['idle_weight'])==1
    q=f.load_config();s=q['scenarios'][0];inputs=SyntheticInputs(q,s)
    rates,_=inputs.apparent_returns();point=inputs.point(r.NATIVE,'10')
    assert point.evidence['return']['base_apy']==rates[r.NATIVE]


def test_no_float_artifact_and_unsupported_not_zero(benchmark):
    text=f.json_bytes(benchmark[0]).decode()
    assert '0.19999999999999996' not in text
    for q in benchmark[0]['rows']:
        if q['method_id'] in METHODS[:2]:
            assert q['method_reported_profit']=='NOT_SUPPORTED'
            assert q['method_lifecycle_cost']=='NOT_SUPPORTED_EXACT_ALLOCATION'
    assert any(q['profit_comparability']=='LIMITED' and q['expected_net_profit']=='NOT_ASSESSED' for q in benchmark[0]['rows'])


def test_profit_comparison_and_attribution(benchmark):
    summary=benchmark[1]
    assert summary['amount_vs_legacy_allocation_difference_count']>0
    assert sum(summary['difference_driver_counts'].values())==len(summary['disagreements'])
    assert summary['limited_profit_rows']>0
    assert all(d['primary_driver']=='MULTIPLE' if len(d['diagnostic_contributors'])>1 else d['primary_driver']==d['diagnostic_contributors'][0] for d in summary['disagreements'])
    assert summary['method_selection_profit_comparability'].startswith('LIMITED')


@pytest.mark.parametrize('name,encoder,index',[
    ('final_evaluation_iteration23.json',f.json_bytes,0),
    ('final_evaluation_iteration23_summary.json',f.json_bytes,1),
    ('final_evaluation_iteration23.csv',lambda raw:f.csv_bytes(raw['rows']),0)])
def test_exact_artifact_replay(benchmark,name,encoder,index):
    assert (ROOT/'results'/name).read_bytes()==encoder(benchmark[index])


def test_frozen_files_unmodified_and_production_idle(benchmark):
    frozen=['data/runtime_strategy_config.json','data/admission_evidence.csv','data/strategy_return_evidence.json',
        'data/lp_quote_evidence.json','data/lifecycle_cost_evidence.json','data/lp_evaluation_config.json','data/evaluation_policy.json','data/strategies.csv']
    for path in frozen:
        assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show','0d8508987e4c499d7be343cdcc63ba48a989c9be:'+path],cwd=ROOT)
    raw=json.loads((ROOT/frozen[0]).read_text());assert all(c['verification_state']=='UNRESOLVED' for c in raw['records'])
    for path in frozen[2:5]:assert not json.loads((ROOT/path).read_text())['records']
    assert len((ROOT/frozen[1]).read_text().splitlines())==1
    assert all(q['idle_weight']==1 for q in benchmark[0]['production_baseline']['runs'])


def test_no_public_fetch_clock_or_random_in_harness():
    for module in (f,):
        text=Path(module.__file__).read_text()
        assert 'datetime.now' not in text and 'random.' not in text and 'requests.' not in text


@pytest.mark.parametrize('feature',['exact_amount_economics','fixed_lifecycle_costs','lp_quote_effects','range_aware_lp_stress','cash_deadline','amount_specific_feasibility','selected_point_revalidation'])
def test_final_supported_capabilities_and_baseline_limitations(feature):
    q=f.load_config()['capabilities']
    assert q[METHODS[3]][feature]=='SUPPORTED'
    assert q[METHODS[0]][feature]==q[METHODS[1]][feature]=='NOT_SUPPORTED'


@pytest.mark.parametrize('id',['NEGATIVE','MISSING_RETURN','ADMISSION_FAILURE','ASCEND_ATTRACTIVE'])
def test_all_methods_legitimate_idle(benchmark,id):
    assert all(row(benchmark,id,m)['idle_weight']=='1' for m in METHODS)


@pytest.mark.parametrize('id',['MISSING_COST','QUOTE_MISMATCH'])
def test_limited_score_missing_not_zero(benchmark,id):
    for m in METHODS[:2]:
        q=row(benchmark,id,m)
        assert q['profit_comparability']=='LIMITED'
        assert q['expected_net_profit']==q['lifecycle_cost']=='NOT_ASSESSED'
    assert row(benchmark,id,METHODS[2])['idle_weight']=='1'


def test_no_mutation_from_ephemeral_input_or_synthetic_labels():
    q=f.load_config();before=deepcopy(q);inputs=SyntheticInputs(q,q['scenarios'][0])
    inputs.point(r.JAINE,'25');inputs.point(r.JAINE,'25')
    assert q==before and len(inputs.provider.quotes)==2
    assert all(rec['observation_timestamp'] is None and rec['retrieval_timestamp'] is None for rec in inputs.returns+inputs.costs+inputs.provider.quotes)
    assert all(rec['configuration_binding']=='SYNTHETIC_SCENARIO' for rec in inputs.provider.quotes)
    with pytest.raises(ValueError):SyntheticInputs(q|{'label':'LIVE'},q['scenarios'][0])


def test_legacy_compatibility_proxy_matches_actual_frozen_source():
    from src.ascend_optimizer.lp_execution import MODELLED_LP_STRESS_20PCT
    assert float(f.load_config()['package']['legacy_lp_proxy'])==pytest.approx(MODELLED_LP_STRESS_20PCT)


def test_summary_scenario_counts_not_candidate_or_strategy_counts(benchmark):
    q=benchmark[1]
    assert q['core_rows']==108 and q['normalized_rows']==196
    assert all(count<=49 for count in q['amount_candidate_exclusion_or_selected_binding_scenario_counts'].values())
    assert q['amount_gate_or_admission_evidence_block_counts']['gate']==49
    assert q['amount_gate_or_admission_evidence_block_counts']['admission_or_evidence']<=49


def test_quote_and_cost_do_not_enter_stress_values(benchmark):
    a=row(benchmark,'QUOTE_CURVE');b=row(benchmark,'QUOTE_CONSTANT_CONTROL')
    assert a['posthoc_policy_constraints']['lp_absolute_stress']['limit']==b['posthoc_policy_constraints']['lp_absolute_stress']['limit']
    # Risk fraction per unit is invariant; only allocated weight changes.
    af=Decimal(a['lp_absolute_stress'])/Decimal(a['allocation_weights'][r.JAINE])
    bf=Decimal(b['lp_absolute_stress'])/Decimal(b['allocation_weights'][r.JAINE])
    assert float(af)==pytest.approx(float(bf),abs=1e-10)


def test_tie_difference_is_secondary_selection_not_profit_improvement(benchmark):
    d=next(d for d in benchmark[1]['disagreements'] if d['scenario_id']=='TIE')
    assert d['common_profit_delta']=='0'
    assert d['driver_detail']=='SECONDARY_TIE_SELECTION_NOT_PROFIT_FORMULA'


def test_common_rescore_matches_selected_profit_and_fixed_cost_once(benchmark):
    for q in benchmark[0]['rows']:
        if q['method_id']==METHODS[3]:
            assert float(q['method_reported_profit'])==pytest.approx(float(q['expected_net_profit']),abs=1e-8)
            assert float(q['fixed_cost'])==pytest.approx(sum(float(x['fixed_cost_usd']) for x in q['common_economic_points']))


@pytest.mark.parametrize('value,expected',[
    ('1320.000000000001','1320'),('1315.000000000001','1315'),('506.999999999999','507'),
    ('0.19999999999999996','0.2'),('43.395279634804','43.395279634804'),
    ('0.120632485555','0.120632485555'),('0.213699654621','0.213699654621'),('-506.999999999999','-507'),
    ('-1320.000000000001','-1320'),('0','0'),('-0.000000000001','0'),
    ('1.234500000001','1.2345'),('12345.678901234567','12345.678901234567')])
def test_presentation_precision(value,expected):
    result=f.fmt(Decimal(value))
    assert result==expected and 'e' not in result.lower()
    assert f.fmt(Decimal(result))==result


@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity'])
def test_presentation_precision_nonfinite_rejected(value):
    with pytest.raises(ValueError):f.fmt(Decimal(value))


def presentation_dust(value):
    """General numeric invariant for the <=12-place display domain.

    Full-precision source/config/model strings intentionally remain untouched.
    No list of particular offending values is used by the invariant.
    """
    from decimal import InvalidOperation, localcontext
    if not isinstance(value,str):return False
    try:d=Decimal(value)
    except InvalidOperation:return False
    if not d.is_finite():raise AssertionError('nonfinite numeric artifact')
    if d.as_tuple().exponent < -12:return False
    with localcontext() as ctx:
        ctx.prec=60
        return any(0<abs(d-d.quantize(Decimal(1).scaleb(-n)))<=f.DISPLAY_SNAP_TOLERANCE for n in range(9))


def numeric_leaves(value):
    if isinstance(value,dict):
        for v in value.values():yield from numeric_leaves(v)
    elif isinstance(value,list):
        for v in value:yield from numeric_leaves(v)
    else:yield value


def test_presentation_precision_all_artifacts_general_audit(benchmark):
    import csv,io
    for artifact in benchmark:
        assert not any(presentation_dust(v) for v in numeric_leaves(artifact))
    rows=list(csv.DictReader(io.StringIO(f.csv_bytes(benchmark[0]['rows']).decode())))
    assert not any(presentation_dust(v) for v in numeric_leaves(rows))
    for filename in ['final_evaluation_iteration23.json','final_evaluation_iteration23.csv','final_evaluation_iteration23_summary.json']:
        text=(ROOT/'results'/filename).read_text()
        for known in ['1320.000000000001','1315.000000000001','506.999999999999','0.19999999999999996']:
            assert known not in text


def test_presentation_correction_substantive_invariance(benchmark):
    accepted='8e214fa0d5437da22696267dcb1bc929ef1dd4a9'
    def previous(path):return json.loads(subprocess.check_output(['git','show',accepted+':'+path],cwd=ROOT))
    old=previous('results/final_evaluation_iteration23.json');new=benchmark[0]
    assert old['synthetic_config']==new['synthetic_config']
    assert old['production_baseline']==new['production_baseline']
    assert old['dependency_fingerprints']==new['dependency_fingerprints']
    keys=['scenario_id','method_id','allocation_weights','idle_weight','binding_constraints','recommendation_state',
          'profit_comparability','feasibility_state','final_policy_feasibility','supported_feature_flags','rejection_reasons']
    for a,b in zip(old['rows'],new['rows'],strict=True):
        assert {k:a[k] for k in keys}=={k:b[k] for k in keys}
        assert b['allocation_weights'][r.ASCEND]=='0'
        assert sum(Decimal(w) for w in b['allocation_weights'].values())+Decimal(b['idle_weight'])==1
    old_summary=previous('results/final_evaluation_iteration23_summary.json')
    summary=benchmark[1]
    for key,value in old_summary.items():
        if key not in ('disagreements','mean_comparable_profit_delta','median_comparable_profit_delta'):
            assert summary[key]==value
    for a,b in zip(old_summary['disagreements'],summary['disagreements'],strict=True):
        assert {k:v for k,v in a.items() if k!='common_profit_delta'}=={k:v for k,v in b.items() if k!='common_profit_delta'}
    frozen=['runtime_strategy_config.json','admission_evidence.csv','strategy_return_evidence.json',
        'lp_quote_evidence.json','lifecycle_cost_evidence.json','lp_evaluation_config.json','evaluation_policy.json',
        'risk_scenarios.json','exit_evaluation_config.json','strategies.csv','final_evaluation_config.json']
    for name in frozen:
        assert (ROOT/'data'/name).read_bytes()==subprocess.check_output(['git','show',accepted+':data/'+name],cwd=ROOT)
