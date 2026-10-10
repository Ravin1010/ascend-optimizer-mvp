"""SYNTHETIC_EVALUATION_ONLY: focused policy examples, not a benchmark harness."""
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal
import json
from pathlib import Path
import runpy
import subprocess

import pytest
from src.ascend_optimizer import evaluation_policy as p, risk_stress as r, exit_liquidity as x, lp_range_stress as lp
from src.ascend_optimizer.amount_optimizer import run_amount_optimizer, candidate_grid
from src.ascend_optimizer.profiles import get_profile
from tools.economics_preflight import repository_baseline

ROOT=Path(__file__).resolve().parents[1]
T=runpy.run_path(str(ROOT/'tests/test_economics_evidence.py'))


def weights(**values):
    return {sid:values.get(sid,'0') for sid in r.STRATEGIES}


def direct(*, profile='Conservative', w=None, deadline=None, missing_exit=(), missing_risk=(), horizon='90',
           prior=(), analysis=False, value='1000', amount='1000'):
    w=w or weights();provider=p.PolicyEvaluator()
    session=provider.prepare(profile=profile,decision_amount_0g=amount,decision_value=value,
                             holding_horizon_days=horizon,cash_deadline_days=deadline,stage='TEST')
    risk_rows={};exit_rows=deepcopy(session.exit_results)
    for sid in r.STRATEGIES:
        allocation=str(Decimal(value)*Decimal(w[sid]));sc=next(s for s in provider.scenarios if sid in s['strategies'] and s['evidence_class']=='MODELLED')
        risk_rows[sid]=None if sid in missing_risk else r.assess(sid,sc,allocation,mode=p.LABEL,lp_config=provider.lp_configs.get(sid))
        if sid in missing_exit:exit_rows[sid]=None
    return p.assess(policy=provider.policy,profile=profile,decision_amount_0g=amount,decision_value=value,holding_horizon_days=horizon,
                    weights=w,idle_weight=str(1-sum(Decimal(v) for v in w.values())),risk_results=risk_rows,exit_results=exit_rows,
                    mode=p.LABEL,cash_deadline_days=deadline,prior_rejections=prior,analysis_only_closed_gate_override=analysis)


def synthetic_run(*, profile='Aggressive', sids=(r.NATIVE,), deadline=None, policy_provider=None, returns=None, snapshots=None):
    qs=[T['quote'](sid,d,str(a)) for sid in sids if sid in lp.STRATEGIES for a in range(100,801,100) for d in ('ENTRY','EXIT')]
    econ=T['provider'](sids,quotes=qs)
    if returns:
        for row in econ.returns:row['value']=returns.get(row['strategy_id'],row['value'])
    s,sn=T['inputs']()
    if snapshots is not None:sn=snapshots
    def admission(**kw):
        return replace(T['supported'](**kw),capture={'synthetic_decimal_amount':str(kw['canonical_amount_0g'])})
    return run_amount_optimizer(s,sn,decision_amount=1000,price_usd=1,horizon_days=365,profile=profile,
        as_of=T['NOW'],admission_fn=admission,economics_fn=econ,economics_mode=p.LABEL,
        evaluation_policy_mode=p.LABEL,evaluation_policy_fn=policy_provider or p.PolicyEvaluator(),cash_deadline_days=deadline)


def example_results():
    cases=[('all_pass',dict(w=weights(**{r.NATIVE:'0.2',r.JAINE:'0.1'}),deadline='8')),
           ('concentration_fail',dict(w=weights(**{r.NATIVE:'0.5'}))),
           ('staking_fail',dict(w=weights(**{r.NATIVE:'0.3',r.GIMO:'0.3'}))),
           ('lp_absolute_fail',dict(w=weights(**{r.JAINE:'0.4',r.OKU:'0.4'}))),
           ('deadline_fail',dict(w=weights(**{r.NATIVE:'0.2'}),deadline='7')),
           ('unresolved_exit',dict(w=weights(**{r.NATIVE:'0.2'}),deadline='8',missing_exit=(r.NATIVE,))),
           ('zero_unresolved',dict(w=weights(**{r.JAINE:'0.1'}),deadline='1',missing_exit=(r.NATIVE,))),
           ('ascend_closed',dict(w=weights(**{r.ASCEND:'0.1'}),analysis=True)),
           ('partial_idle',dict(w=weights(**{r.NATIVE:'0.2'}))),('all_idle',dict(deadline='0'))]
    return [{'case':name,'result':json.loads(json.dumps(asdict(direct(**kw))))} for name,kw in cases]


def test_scope_and_frozen_profile_namespace():
    policy=p.load_policy();assert policy['scope']=='DECISION_SLEEVE' and not policy['whole_portfolio_acquisition_required']
    assert policy['whole_portfolio_compliance']=='NOT_ASSESSED'
    for name,limit in p.LP_LIMITS.items():
        row=policy['profiles'][name];old=get_profile(name)
        assert row['max_decision_sleeve_lp_absolute_stress_loss']==limit
        assert Decimal(row['max_strategy_concentration'])==Decimal(str(old.max_strategy_concentration))
        assert Decimal(row['max_slashing_stress_loss'])==Decimal(str(old.max_slashing_stress_loss))
    assert [get_profile(n).max_portfolio_lp_il_stress for n in p.LP_LIMITS]==[.02,.05,.10]
    assert 'risk_score' not in asdict(direct())
    with pytest.raises(TypeError): direct(existing_holdings=100)


@pytest.mark.parametrize('changes',[{'scope':'WHOLE_PORTFOLIO'},{'version':'V2'},{'label':'LIVE'},
    {'whole_portfolio_compliance':'COMPLIANT'},{'whole_portfolio_acquisition_required':True}])
def test_policy_cannot_change_scope_or_evidence_labels(changes):
    with pytest.raises(r.RiskError):p.validate_policy(p.load_policy()|changes)


def test_profile_limits_cannot_mutate_under_same_version():
    q=p.load_policy();q['profiles']['Conservative']['max_decision_sleeve_lp_absolute_stress_loss']='0.06'
    with pytest.raises(r.RiskError):p.validate_policy(q)


@pytest.mark.parametrize('name,state',[('all_pass','PASS'),('concentration_fail','FAIL'),('staking_fail','FAIL'),
    ('lp_absolute_fail','FAIL'),('deadline_fail','FAIL'),('unresolved_exit','UNRESOLVED'),('zero_unresolved','PASS'),
    ('ascend_closed','FAIL'),('partial_idle','PASS'),('all_idle','PASS')])
def test_reproducible_policy_examples(name,state):
    record=next(x for x in example_results() if x['case']==name)['result']
    assert record['overall']==state and record['scope']=='DECISION_SLEEVE'
    assert record['whole_portfolio_compliance']=='NOT_ASSESSED'
    if state!='PASS':assert record['rejection_reasons']


@pytest.mark.parametrize('sid',[r.JAINE,r.OKU])
def test_range_absolute_loss_scaling_and_missing_stress(sid):
    a=direct(w=weights(**{sid:'0.2'}));b=direct(w=weights(**{sid:'0.2'}),value='2000')
    cfg=next(c for c in lp.load_configs() if c['strategy_id']==sid)
    worst=max(Decimal(lp.evaluate(cfg,s,'1',mode=p.LABEL,expected_config_id=cfg['config_id']).absolute_lp_loss) for s in lp.scenarios())
    assert float(a.constraints['lp_absolute_stress']['value'])==pytest.approx(float(worst)*.2)
    assert a.constraints['lp_absolute_stress']==b.constraints['lp_absolute_stress']
    assert a.input_identity!=b.input_identity  # actual allocation values in each risk fingerprint scale.
    unresolved=direct(w=weights(**{sid:'0.2'}),missing_risk=(sid,))
    assert unresolved.overall=='UNRESOLVED' and 'RISK:'+sid in unresolved.unresolved_required_constraints
    assert 'MODELLED_LP_STRESS_20PCT' not in Path(p.__file__).read_text()


@pytest.mark.parametrize('deadline,state',[ (None,'NOT_REQUESTED'),('7.1','COMPATIBLE_MODELLED'),('7.099','INCOMPATIBLE_MODELLED')])
def test_deadline_boundary_separate_from_holding_horizon(deadline,state):
    a=direct(w=weights(**{r.NATIVE:'0.2'}),deadline=deadline)
    b=direct(w=weights(**{r.NATIVE:'0.2'}),deadline=deadline,horizon='365')
    assert a.constraints['cash_deadline']['state']==b.constraints['cash_deadline']['state']==state
    assert a.idle_time_to_cash_days=='0'


def test_prior_admission_or_economic_failure_never_revived():
    q=direct(prior=('TECHNICAL_ADMISSION_UNKNOWN','MISSING_COST'))
    assert q.overall=='FAIL' and q.rejection_reasons[:2]==('TECHNICAL_ADMISSION_UNKNOWN','MISSING_COST')


def test_ascend_analysis_override_never_allocates():
    assert direct(w=weights(**{r.ASCEND:'0.1'}),analysis=True).overall=='FAIL'
    assert direct(w=weights(**{r.ASCEND:'0.1'}),analysis=False).overall=='FAIL'


def test_amount_grid_profit_fixed_cost_and_exact_identity():
    result=synthetic_run()
    assert result.grid==candidate_grid(get_profile('Aggressive'))
    assert result.selected[0].weight==.8 and result.revalidation=='PASSED'
    points=[c for c in result.candidates if c.strategy_id==r.NATIVE and c.weight>0]
    assert all(c.fixed_execution_cost_usd==2 for c in points)
    assert points[0].net_profit_usd==pytest.approx(8) and points[3].net_profit_usd==pytest.approx(38)
    assert result.evaluation_policy['overall']=='PASS'
    assert 'legacy_stress' not in result.to_dict()['recommendation']
    assert result.to_dict()['whole_portfolio_compliance']=='NOT_ASSESSED'
    for c in points:assert Decimal(c.admission_evidence.capture['synthetic_decimal_amount'])==Decimal(str(c.amount_0g))


def test_policy_profile_and_lp_constraint_changes_selection():
    results=[synthetic_run(profile=n,sids=(r.JAINE,)) for n in ('Conservative','Balanced','Aggressive')]
    assert [q.selected[0].weight for q in results]==[.3,.6,.8]
    assert all(q.revalidation=='PASSED' for q in results)
    assert all(any(c.eligible and c.weight>q.selected[0].weight for c in q.candidates if c.strategy_id==r.JAINE) for q in results[:1])
    # The point is profitable/admitted but a .4 Jaine allocation exceeds the new Conservative absolute budget.
    assert direct(w=weights(**{r.JAINE:'.4'})).constraints['lp_absolute_stress']['state']=='FAIL'


def test_tight_deadline_filters_async_relaxed_restores_and_objective_unchanged():
    tight=synthetic_run(deadline='1');relaxed=synthetic_run(deadline='8')
    assert not tight.selected and relaxed.selected[0].weight==.8
    assert [c.net_profit_usd for c in tight.candidates]==[c.net_profit_usd for c in relaxed.candidates]
    assert tight.evaluation_policy['overall']=='PASS' and tight.evaluation_policy['idle_weight']=='1.0'


def test_economics_ranking_among_feasible_points_unchanged():
    q=synthetic_run(sids=(r.NATIVE,r.JAINE),returns={r.NATIVE:'0.2',r.JAINE:'0.1'})
    assert next(c.weight for c in q.selected if c.strategy_id==r.NATIVE)==.8
    assert q.to_dict()['recommendation']['expected_net_profit_usd']==pytest.approx(sum(c.net_profit_usd for c in q.selected))


@pytest.mark.parametrize('change',['policy','lp_config','exit_config','risk_scenario','deadline'])
def test_selected_policy_revalidation_fails_closed_on_input_change(change):
    class Changing(p.PolicyEvaluator):
        def prepare(self,**kw):
            if kw['stage']=='REVALIDATION':
                if change=='policy':self.policy['assumptions'].append('Changed assumption')
                elif change=='lp_config':
                    c=self.lp_configs[r.JAINE];c['fee_tier']=500;c['config_id']=lp.config_identity(c)
                elif change=='exit_config':self.exit_configs[r.NATIVE]['claim_processing_days']='0.2'
                elif change=='risk_scenario':self.scenarios[0]['assumptions'].append('Changed scenario provenance')
                else:kw['cash_deadline_days']='9'
            return super().prepare(**kw)
    q=synthetic_run(policy_provider=Changing(),deadline='8')
    assert q.revalidation=='FAILED' and q.to_dict()['recommendation'] is None
    assert any('policy' in reason.lower() for reason in q.revalidation_errors)


def test_no_generic_risk_or_legacy_exit_override_in_final_path():
    s,sn=T['inputs']()
    sn.loc[:,'lp_stress_loss_20pct']=.99;sn.loc[:,'slashing_stress_loss']=.99;sn.loc[:,'exit_time_days']=999
    q=synthetic_run(snapshots=sn)
    assert q.selected[0].weight==.8 and q.revalidation=='PASSED'
    # Canonical synthetic risk and optional deadline own feasibility; old coefficients do not override them.
    assert q.evaluation_policy['constraints']['staking_stress']['value']=='0.040'


def test_modes_and_deadline_not_enabled_in_production():
    s,sn=T['inputs']();econ=T['provider']()
    with pytest.raises(ValueError):run_amount_optimizer(s,sn,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',cash_deadline_days='7')
    with pytest.raises(ValueError):run_amount_optimizer(s,sn,decision_amount=1000,price_usd=1,horizon_days=90,profile='Balanced',economics_fn=econ,evaluation_policy_mode=p.LABEL)


def test_frozen_state_and_repository_idle():
    before=subprocess.check_output(['git','diff','--name-only','432e2ede7d86e0cfc9bc4111a89d3ebebdfaab1b','--','data/runtime_strategy_config.json','data/admission_evidence.csv','data/strategy_return_evidence.json','data/lp_quote_evidence.json','data/lifecycle_cost_evidence.json','data/lp_evaluation_config.json'],cwd=ROOT)
    assert before==b''
    baseline=repository_baseline()
    assert all(x['idle_weight']==1 for x in baseline['runs'])
    assert baseline['return_record_count']==baseline['quote_record_count']==baseline['cost_record_count']==0
    assert T['inputs']()[0].set_index('strategy_id').loc[r.ASCEND,'allocation_gate']=='CLOSED'


def test_absolute_losses_scale_to_actual_candidate_values():
    a=direct(w=weights(**{r.NATIVE:'.2',r.JAINE:'.1'}),value='1234.56')
    b=direct(w=weights(**{r.NATIVE:'.2',r.JAINE:'.1'}),value='2469.12')
    ar={x['strategy_id']:x for x in a.risk_budget['rows']};br={x['strategy_id']:x for x in b.risk_budget['rows']}
    for sid in (r.NATIVE,r.JAINE):
        assert float(br[sid]['absolute_strategy_stress_loss'])==pytest.approx(2*float(ar[sid]['absolute_strategy_stress_loss']))
    assert float(ar[r.NATIVE]['absolute_strategy_stress_loss'])==pytest.approx(1234.56*.2*.05)


def test_missing_required_risk_and_exit_remove_positive_choices():
    pr=p.PolicyEvaluator(lp_configs={})
    q=synthetic_run(sids=(r.JAINE,),policy_provider=pr)
    assert not q.selected and q.evaluation_policy['overall']=='PASS'
    pr=p.PolicyEvaluator(exit_configs={})
    q=synthetic_run(deadline='8',policy_provider=pr)
    assert not q.selected and q.evaluation_policy['overall']=='PASS'


def test_exact_boundary_binding_states_and_idle_missing_inputs():
    q=direct(w=weights(**{r.NATIVE:'.4'}),deadline='7.1')
    assert q.overall=='PASS' and {'concentration','staking_stress'} <= set(q.binding_constraints)
    q=direct(missing_risk=r.STRATEGIES,missing_exit=r.STRATEGIES,deadline='0')
    assert q.overall=='PASS' and not q.unresolved_required_constraints


@pytest.mark.parametrize('kwargs',[{'deadline':'-1'},{'horizon':'0'},{'amount':'0'},{'value':'NaN'},
                                    {'w':weights(**{r.NATIVE:'1.1'})}])
def test_invalid_top_level_inputs_rejected(kwargs):
    with pytest.raises(ValueError):direct(**kwargs)


def test_committed_policy_replay_exact():
    from tools.evaluation_policy_preflight import replay
    assert json.loads((ROOT/'results/evaluation_policy_iteration22.json').read_text())==replay()
