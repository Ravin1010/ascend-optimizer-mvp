"""Synthetic decision-sleeve feasibility. No objective penalties or live claims."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from decimal import Decimal

from . import risk_stress as risk, exit_liquidity as exits, lp_range_stress as lp
from .data_loader import DEFAULT_DATA_DIR
from .profiles import get_profile

VERSION='EVALUATION_POLICY_V1'
LABEL=risk.LABEL
SCOPE='DECISION_SLEEVE'
LP_LIMITS={'Conservative':'0.05','Balanced':'0.10','Aggressive':'0.20'}
POLICY_FIELDS={'version','artifact_type','label','scope','whole_portfolio_compliance','decision_capital','existing_positions',
 'whole_portfolio_acquisition_required','profiles','lp_rule','risk_aggregation','deadline_rule','ascend_gate','bridge_rule','assumptions'}


def validate_policy(p):
    if not isinstance(p,dict) or set(p)!=POLICY_FIELDS or p['version']!=VERSION or p['label']!=LABEL or p['artifact_type']!=lp.ARTIFACT_TYPE:
        raise risk.RiskError('versioned synthetic policy required')
    if p['scope']!=SCOPE or p['whole_portfolio_compliance']!='NOT_ASSESSED' or p['whole_portfolio_acquisition_required'] is not False or p['existing_positions']!='EXOGENOUS_OUTSIDE_OPTIMIZED_STATE':
        raise risk.RiskError('decision-sleeve scope cannot acquire holdings/whole-portfolio compliance')
    if set(p['profiles'])!=set(LP_LIMITS) or p['lp_rule']!='WORST_ABSOLUTE_LOSS_ACROSS_LP_SHOCKS_V1' or p['risk_aggregation']!=risk.ENVELOPE:
        raise risk.RiskError('policy measure/profile mismatch')
    for name,limit in LP_LIMITS.items():
        profile=get_profile(name);row=p['profiles'][name]
        if set(row)!= {'max_strategy_concentration','max_slashing_stress_loss','max_decision_sleeve_lp_absolute_stress_loss'}:
            raise risk.RiskError('policy thresholds mismatch')
        expected=(Decimal(str(profile.max_strategy_concentration)),Decimal(str(profile.max_slashing_stress_loss)),Decimal(limit))
        actual=tuple(risk.decimal(row[k],fraction=True) for k in ('max_strategy_concentration','max_slashing_stress_loss','max_decision_sleeve_lp_absolute_stress_loss'))
        if actual!=expected: raise risk.RiskError('frozen profile limits changed without new version')
    if not p['assumptions'] or any(not isinstance(x,str) or not x for x in p['assumptions']):
        raise risk.RiskError('policy assumption provenance required')
    return p


def load_policy(path=DEFAULT_DATA_DIR/'evaluation_policy.json'):
    return validate_policy(json.loads(Path(path).read_text()))


@dataclass(frozen=True)
class PolicyResult:
    policy_version: str
    policy_fingerprint: str
    scope: str
    profile: str
    candidate_weights: dict
    idle_weight: str
    decision_amount_0g: str
    decision_value: str
    holding_horizon_days: str
    cash_deadline_days: str | None
    constraints: dict
    per_strategy_exit_compatibility: dict
    unresolved_required_constraints: tuple[str,...]
    overall: str
    rejection_reasons: tuple[str,...]
    binding_constraints: tuple[str,...]
    input_identity: str
    risk_input_identities: dict
    exit_input_identities: dict
    source_identity: str
    risk_budget: dict
    whole_portfolio_compliance: str = 'NOT_ASSESSED'
    evidence_class: str = 'MODELLED'
    label: str = LABEL
    idle_time_to_cash_days: str = '0'


def missing_risk(sid,amount):
    category='LP_POSITION_VALUE' if sid in lp.STRATEGIES else 'STAKING_LOSS' if sid in (risk.NATIVE,risk.GIMO) else 'SOURCECORE_VALUE_LOSS'
    return risk.StressResult(sid,'UNRESOLVED',risk.SCENARIO_VERSION,'UNRESOLVED',risk.VERSION,category,'UNRESOLVED',amount,amount,
        None,None,None,'MISSING','UNRESOLVED',LABEL,'UNRESOLVED',False,{},('No qualified range/staking result supplied',),
        ('Missing required risk is not zero',),allocation_gate='CLOSED' if sid==risk.ASCEND else 'NOT_EVALUATED_BY_RISK_MODEL')


def assess(*, policy, profile, decision_amount_0g, decision_value, holding_horizon_days, weights, idle_weight,
           risk_results, exit_results, mode, cash_deadline_days=None, prior_rejections=(),
           analysis_only_closed_gate_override=False, source_identity='DIRECT_TYPED_INPUTS') -> PolicyResult:
    if mode!=LABEL: raise risk.RiskError('explicit synthetic policy mode required')
    validate_policy(policy);p=get_profile(profile)
    if set(weights)!=set(risk.STRATEGIES) or set(risk_results)!=set(risk.STRATEGIES) or set(exit_results)!=set(risk.STRATEGIES):
        raise risk.RiskError('exact five-strategy maps required; holdings are not policy inputs')
    with risk.precision():
        amount=risk.decimal(decision_amount_0g,positive=True);value=risk.decimal(decision_value,positive=True)
        risk.decimal(holding_horizon_days,positive=True)
        deadline=None if cash_deadline_days is None else risk.decimal(cash_deadline_days)
        w={sid:risk.decimal(v,fraction=True) for sid,v in weights.items()};idle=risk.decimal(idle_weight,fraction=True)
        if sum(w.values())+idle!=1: raise risk.RiskError('exact sleeve weights plus idle must sum to one')
        rows=[];risk_ids={};exit_ids={};reasons=list(prior_rejections);required=[]
        for sid in risk.STRATEGIES:
            allocation=lp.text(value*w[sid]);r=risk_results[sid]
            if sid==risk.ASCEND and not analysis_only_closed_gate_override:
                r=None  # Do not perform a closed-gate economic assessment without explicit analysis override.
            if r is None: r=missing_risk(sid,allocation)
            if not isinstance(r,risk.StressResult) or r.strategy_id!=sid:
                raise risk.RiskError('typed strategy risk result required')
            if w[sid]>0 and r.aggregation_eligible:
                if sid in lp.STRATEGIES:
                    d=r.diagnostics
                    if r.risk_category!='LP_POSITION_VALUE' or r.severity is not None or not d.get('only_absolute_loss_aggregated') or d.get('selection_rule')!=policy['lp_rule'] or not d.get('lp_config_id','').startswith(lp.CONFIG_VERSION+':'+sid+':') :
                        raise risk.RiskError('range-aware absolute LP risk required; no legacy/IL substitution')
                    fraction=risk.decimal(d.get('lp_absolute_stress_loss'),fraction=True)
                    if abs(risk.decimal(r.loss_fraction,fraction=True)-fraction)>Decimal('1e-55'):
                        raise risk.RiskError('LP absolute fraction conflicts with range result')
                    # Frozen risk V1 divides loss by allocation, which can round
                    # one ulp. Canonicalize that ratio back to its range fraction.
                    r=replace(r,loss_fraction=lp.text(fraction))
                elif sid in (risk.NATIVE,risk.GIMO) and (r.risk_category!='STAKING_LOSS' or r.severity!='0.05'):
                    raise risk.RiskError('underlying staking loss result required')
            rows.append(r);risk_ids[sid]=risk.fingerprint(asdict(risk_results[sid])) if risk_results[sid] is not None else risk.fingerprint(asdict(r))
            x=exit_results[sid]
            if x is not None and (not isinstance(x,exits.ExitResult) or x.strategy_id!=sid or x.exit_model_version!=exits.VERSION or x.output_asset!='native 0G'):
                raise risk.RiskError('typed native-0G exit result required')
            exit_ids[sid]=None if x is None else risk.fingerprint(asdict(x))
        # The aggregation override permits diagnostics only; gate feasibility below ALWAYS rejects positive Ascend.
        budget=risk.aggregate(rows,{s:lp.text(v) for s,v in w.items()},decision_value,mode=LABEL,allow_closed_analysis=True)
        budget['closed_gate_analysis_only']=analysis_only_closed_gate_override
        budget['allocation_gate_enforcement']='POLICY_ALWAYS_REJECTS_POSITIVE_ASCEND'
        for sid in budget['unresolved_positive_allocations']:
            required.append('RISK:'+sid)
        limits=policy['profiles'][p.name.value]
        constraints={}
        def limit_check(name,actual,limit):
            state='UNRESOLVED' if actual is None else 'PASS' if Decimal(actual)<=Decimal(limit) else 'FAIL'
            constraints[name]={'state':state,'value':actual,'limit':limit}
            if state=='UNRESOLVED': required.append(name)
            elif state=='FAIL': reasons.append(name)
        limit_check('concentration',lp.text(max(w.values())),limits['max_strategy_concentration'])
        limit_check('staking_stress',budget['staking_stress_loss'],limits['max_slashing_stress_loss'])
        limit_check('lp_absolute_stress',budget['lp_absolute_stress_loss'],limits['max_decision_sleeve_lp_absolute_stress_loss'])
        gate='FAIL' if w[risk.ASCEND]>0 else 'PASS'
        constraints['allocation_gate']={'state':gate,'ascend':'CLOSED','analysis_only_override':analysis_only_closed_gate_override}
        if gate=='FAIL': reasons.append('ASCEND_ALLOCATION_GATE_CLOSED')
        compatibility={}
        for sid in risk.STRATEGIES:
            x=exit_results[sid]
            if deadline is None: state='NOT_REQUESTED'
            elif w[sid]==0: state='NOT_REQUIRED_ZERO_WEIGHT'
            elif x is None or x.qualification_state!='ASSESSED_MODELLED' or x.evidence_class!='MODELLED' or x.timing_evidence_class!='MODELLED' or x.mode!=LABEL or x.time_to_cash_days is None: state='UNRESOLVED'
            else: state=exits.deadline_compatible(x,cash_deadline_days)
            compatibility[sid]={'state':state,'time_to_cash_days':None if x is None else x.time_to_cash_days,'weight':lp.text(w[sid])}
            if state=='UNRESOLVED': required.append('DEADLINE:'+sid)
            if state=='INCOMPATIBLE_MODELLED': reasons.append('CASH_DEADLINE:'+sid)
        deadline_states={x['state'] for x in compatibility.values()}
        deadline_state='NOT_REQUESTED' if deadline is None else 'INCOMPATIBLE_MODELLED' if 'INCOMPATIBLE_MODELLED' in deadline_states else 'UNRESOLVED' if 'UNRESOLVED' in deadline_states else 'COMPATIBLE_MODELLED'
        constraints['cash_deadline']={'state':deadline_state,'deadline_days':cash_deadline_days,'idle_time_to_cash_days':'0'}
        constraints['required_risk']={'state':'UNRESOLVED' if budget['unresolved_positive_allocations'] else 'PASS'}
        overall='FAIL' if reasons else 'UNRESOLVED' if required else 'PASS'
        bindings=tuple(k for k,v in constraints.items() if v['state'] in ('FAIL','UNRESOLVED','INCOMPATIBLE_MODELLED') or
                       (v['state']=='PASS' and 'value' in v and v['value'] is not None and Decimal(v['value'])==Decimal(v['limit'])))
        reasons.extend('UNRESOLVED_REQUIRED:'+x for x in required)
        identity=risk.fingerprint({'policy':risk.fingerprint(policy),'profile':p.name.value,'weights':weights,'idle':idle_weight,
            'decision_amount':decision_amount_0g,'decision_value':decision_value,'horizon':holding_horizon_days,'deadline':cash_deadline_days,
            'risk':risk_ids,'exit':exit_ids,'source':source_identity,'prior_rejections':list(prior_rejections),
            'analysis_only_closed_gate_override':analysis_only_closed_gate_override})
        return PolicyResult(VERSION,risk.fingerprint(policy),SCOPE,p.name.value,dict(weights),idle_weight,decision_amount_0g,
            decision_value,holding_horizon_days,cash_deadline_days,constraints,compatibility,tuple(required),overall,
            tuple(reasons),bindings,identity,risk_ids,exit_ids,source_identity,budget)


class PolicyEvaluator:
    """Prepare a per-stage snapshot; caches exact per-amount risks inside that snapshot.

    Revalidation takes a NEW snapshot/fingerprint. Missing data yields unresolved
    results, never a legacy proxy. Model inputs remain mutable for explicit tests.
    """
    def __init__(self, *, policy=None, scenarios=None, lp_configs=None, exit_configs=None):
        self.policy=load_policy() if policy is None else deepcopy(policy)
        self.scenarios=risk.load_scenarios() if scenarios is None else deepcopy(scenarios)
        self.lp_configs={c['strategy_id']:c for c in lp.load_configs()} if lp_configs is None else deepcopy(lp_configs)
        self.exit_configs={c['strategy_id']:c for c in exits.load_configs()} if exit_configs is None else deepcopy(exit_configs)

    def prepare(self, *, profile, decision_amount_0g, decision_value, holding_horizon_days, cash_deadline_days, stage):
        return PolicySession(self,profile,decision_amount_0g,decision_value,holding_horizon_days,cash_deadline_days)


class PolicySession:
    def __init__(self,provider,profile,amount,value,horizon,deadline):
        self.provider=deepcopy(provider);validate_policy(self.provider.policy)
        self.args=dict(policy=self.provider.policy,profile=profile,decision_amount_0g=amount,decision_value=value,
                       holding_horizon_days=horizon,cash_deadline_days=deadline,mode=LABEL)
        self.identity=risk.fingerprint({'policy':self.provider.policy,'scenarios':self.provider.scenarios,
                                       'lp_configs':self.provider.lp_configs,'exit_configs':self.provider.exit_configs})
        self.risks={};self.exit_results={s:exits.assess(s,mode=LABEL,config=self.provider.exit_configs.get(s)) for s in risk.STRATEGIES}

    def __call__(self, *, weights, idle_weight, prior_rejections=()):
        rows={}
        with risk.precision():
            for sid in risk.STRATEGIES:
                value=lp.text(Decimal(self.args['decision_value'])*Decimal(weights[sid]));key=(sid,value)
                if key not in self.risks:
                    scenario=next((s for s in self.provider.scenarios if sid in s['strategies'] and s['evidence_class']=='MODELLED'),None)
                    if Decimal(weights[sid])==0 or sid==risk.ASCEND or scenario is None or (sid in lp.STRATEGIES and sid not in self.provider.lp_configs):
                        self.risks[key]=None
                    else:
                        self.risks[key]=risk.assess(sid,scenario,value,mode=LABEL,lp_config=self.provider.lp_configs.get(sid))
                rows[sid]=self.risks[key]
        return assess(**self.args,weights=weights,idle_weight=idle_weight,risk_results=rows,exit_results=self.exit_results,
                      source_identity=self.identity,prior_rejections=prior_rejections)
