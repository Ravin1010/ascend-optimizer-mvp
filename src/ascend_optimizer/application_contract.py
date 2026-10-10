"""Schema 1.4 current-request adapter; no change to search or evidence qualification."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from . import evaluation_policy as p, risk_stress as r, exit_liquidity as exits
from .amount_optimizer import run_amount_optimizer
from .data_loader import load_strategies, load_snapshots
from .strategy_state import strategy_state
from .final_evaluation_inputs import SyntheticInputs
from .final_evaluation import fmt, legacy_candidates
from .optimizer import optimize_portfolio
from .net_return_engine import annualize_horizon_return

ROOT=Path(__file__).resolve().parents[2]
NAMES=dict(zip(r.STRATEGIES, ('Native Staking','Gimo Staking','Jaine LP','Oku LP','Ascend Staking')))
MODES=('PRODUCTION',p.LABEL)


def measure(value=None, unit='FRACTION', state=None, basis='CURRENT_REQUEST'):
    return {'state':state or ('NOT_ASSESSED' if value is None else 'ASSESSED'),
            'value':None if value is None else fmt(Decimal(str(value))), 'unit':unit,'basis':basis}


def economics(candidate=None):
    ev=None if candidate is None else candidate.economics_evidence
    if not ev:
        return {k:measure(unit='USD' if k.endswith('_usd') else 'FRACTION') for k in
                ('gross_income_usd','lifecycle_cost_usd','fixed_cost_usd','quote_execution_cost_usd','expected_net_profit_usd','expected_net_return','net_apy')}
    return dict(gross_income_usd=measure(ev['return']['expected_gross_income_usd'],'USD'),
        lifecycle_cost_usd=measure(ev['costs']['total_cost_usd'],'USD'),
        fixed_cost_usd=measure(candidate.fixed_execution_cost_usd,'USD'),
        quote_execution_cost_usd=measure(ev['quote_cost_usd'],'USD'),
        expected_net_profit_usd=measure(candidate.net_profit_usd,'USD'),
        expected_net_return=measure(candidate.net_return_horizon),net_apy=measure(candidate.net_apy))


def optimize_request(*, decision_amount_0g, profile='Balanced', holding_horizon_days=90,
                     cash_deadline_days=None, evidence_mode='PRODUCTION', as_of=None):
    amount=r.decimal(str(decision_amount_0g),positive=True); horizon=r.decimal(str(holding_horizon_days),positive=True)
    amount_text=format(amount.normalize(),'f'); horizon_text=format(horizon.normalize(),'f')
    deadline=None if cash_deadline_days is None else format(r.decimal(str(cash_deadline_days)).normalize(),'f')
    if evidence_mode not in MODES: raise ValueError('explicit recognized evidence mode required')
    synthetic=evidence_mode==p.LABEL
    if profile not in p.LP_LIMITS: raise ValueError('unknown profile')
    policy=p.PolicyEvaluator(); limits=policy.policy['profiles'][profile]
    # Never fetch prices or market data in this interface. Production has no
    # qualified valuation: unit-price solver placeholder cannot qualify evidence.
    price=Decimal('1'); inp=None
    if synthetic:
        config=json.loads((ROOT/'data/application_evaluation_config.json').read_text())
        if config['version']!='APPLICATION_EVALUATION_V1' or config['label']!=p.LABEL: raise ValueError('synthetic application package required')
        scenario={'scenario_id':'APPLICATION_CURRENT_INPUT_V1','label':p.LABEL,'modified_assumptions':{},
            'decision_amount_0g':amount_text,'holding_horizon_days':horizon_text,'profile':profile,'cash_deadline_days':deadline}
        inp=SyntheticInputs(config,scenario); price=Decimal(inp.package['price_usd'])
        run=run_amount_optimizer(inp.strategies,inp.snapshots,decision_amount=float(amount),price_usd=float(price),
            horizon_days=float(horizon),profile=profile,as_of=inp.as_of,admission_fn=inp.admission,
            economics_fn=inp.economics,economics_mode=p.LABEL,evaluation_policy_mode=p.LABEL,
            evaluation_policy_fn=policy,cash_deadline_days=deadline)
    else:
        strategies=load_strategies(); snapshots=load_snapshots(strategies)
        run=run_amount_optimizer(strategies,snapshots,decision_amount=float(amount),price_usd=1,
            horizon_days=float(horizon),profile=profile,as_of=as_of or datetime.now(timezone.utc))
        if run.selected: raise ValueError('production interface requires qualified valuation before positive allocation')
    metadata=inp.strategies if synthetic else strategies
    canonical={sid:strategy_state(metadata[metadata.strategy_id==sid].iloc[0]) for sid in r.STRATEGIES}
    valid=run.revalidation!='FAILED'
    selected={c.strategy_id:c for c in run.selected} if valid else {}
    weights={s:Decimal(str(selected[s].weight)) if s in selected else Decimal(0) for s in r.STRATEGIES}
    idle=1-sum(weights.values()); ep=run.evaluation_policy if valid else None
    exit_rows={s:exits.assess(s,mode=evidence_mode,config=policy.exit_configs[s] if synthetic else None,
                            holding_horizon_days=horizon_text) for s in r.STRATEGIES}
    session=policy.prepare(profile=profile,decision_amount_0g=str(float(amount)),decision_value=str(amount*price),
        holding_horizon_days=str(float(horizon)),cash_deadline_days=deadline,stage='CANDIDATE') if synthetic else None
    rows=[]
    for sid in r.STRATEGIES:
        points=[c for c in run.candidates if c.strategy_id==sid and c.weight>0]
        diagnostic=selected.get(sid) or next((c for c in points if c.eligible), points[0])
        reasons=sorted({x for c in points for x in c.rejection_reasons})
        check=None
        if synthetic:
            diagnostic_weight=Decimal(str(diagnostic.weight))
            w={s:(str(diagnostic_weight) if s==sid else '0') for s in r.STRATEGIES}
            check=session(weights=w,idle_weight=str(1-diagnostic_weight),prior_rejections=tuple(diagnostic.rejection_reasons))
            reasons=sorted(set(reasons)|set(check.rejection_reasons))
        risk_row=None if check is None else next(x for x in check.risk_budget['rows'] if x['strategy_id']==sid)
        canonical_metadata=canonical[sid]
        gated=canonical_metadata.allocation_gate=='CLOSED'
        allocation='GATED' if gated else 'ALLOCATED_POSITIVE' if weights[sid]>0 else 'EXCLUDED' if not any(c.eligible for c in points) or (check and check.overall!='PASS') else 'ELIGIBLE_ZERO'
        if allocation=='ELIGIBLE_ZERO': reasons.append('Lower expected net profit or candidate-level policy constraint; eligible zero allocation')
        x=exit_rows[sid]
        state='NOT_REQUESTED' if deadline is None else exits.deadline_compatible(x,deadline)
        rows.append({'strategy_id':sid,'display_name':NAMES[sid],'canonical_state':canonical_metadata.reconciliation_category,
            'structural_candidate':canonical_metadata.structural_candidate,'allocation_gate':canonical_metadata.allocation_gate,'allocation_result':allocation,
            'allocated_weight':fmt(weights[sid]),'allocated_amount_0g':format((amount*weights[sid]).normalize(),'f'),
            'technical_admission':diagnostic.technical_admission,'economics_state':'ASSESSED' if diagnostic.economics_evidence else 'MISSING',
            'economics':economics(diagnostic),'diagnostic_amount_0g':format(Decimal(str(diagnostic.amount_0g)).normalize(),'f'),
            'economics_basis':'SELECTED_EXACT_AMOUNT' if sid in selected else 'UNSELECTED_CANDIDATE_DIAGNOSTIC',
            'policy_feasibility':'NOT_ASSESSED' if check is None else check.overall,
            'risk':{'state':'UNRESOLVED' if risk_row is None else risk_row['risk_assessment_state'],
                'loss_fraction':measure(None if risk_row is None else risk_row['strategy_stress_loss_fraction']),
                'absolute_loss_usd':measure(None if risk_row is None else risk_row['absolute_strategy_stress_loss'],'USD'),
                'basis':'SELECTED_EXACT_AMOUNT' if sid in selected else 'UNSELECTED_CANDIDATE_DIAGNOSTIC'},
            'rejection_reasons':reasons,'binding_constraints':[] if check is None else list(check.binding_constraints),
            'evidence':{'mode':evidence_mode,'class':'MODELLED' if synthetic else 'MISSING','provenance':diagnostic.economics_evidence},
            'liquidity':{'exit_type':x.exit_type,'time_to_cash_days':measure(x.time_to_cash_days,'DAYS',basis=x.timing_evidence_class),
                'deadline_state':state,'qualification':x.qualification_state,'model_version':x.exit_model_version,'output_asset':x.output_asset},
            'protocol_availability':canonical_metadata.protocol_availability,'integration_state':canonical_metadata.integration_status,
            'runtime_configuration':'UNRESOLVED','execution_readiness':'NOT_ESTABLISHED','public_proof':'NOT_ESTABLISHED'})
    totals={k:Decimal(0) for k in economics()}
    for c in selected.values():
        ev=c.economics_evidence
        values={'gross_income_usd':ev['return']['expected_gross_income_usd'],
                'lifecycle_cost_usd':ev['costs']['total_cost_usd'],
                'fixed_cost_usd':c.fixed_execution_cost_usd,
                'quote_execution_cost_usd':ev['quote_cost_usd'],
                'expected_net_profit_usd':c.net_profit_usd}
        for key,value in values.items(): totals[key]+=Decimal(str(value))
    totals['expected_net_return']=totals['expected_net_profit_usd']/(amount*price)
    totals['net_apy']=Decimal(str(annualize_horizon_return(float(totals['expected_net_return']),float(horizon))))
    aggregate={k:measure(v if synthetic else None,'USD' if k.endswith('_usd') else 'FRACTION',basis='IDLE_HAS_NO_STRATEGY_INCOME_OR_COST' if not selected else 'SELECTED_EXACT_AMOUNTS') for k,v in totals.items()}
    constraints=ep['constraints'] if ep else {k:{'state':'NOT_ASSESSED','value':None,'limit':limits[f]} for k,f in
        [('concentration','max_strategy_concentration'),('staking_stress','max_slashing_stress_loss'),('lp_absolute_stress','max_decision_sleeve_lp_absolute_stress_loss')]}
    constraints['concentration']={'state':'PASS','value':fmt(max(weights.values())), 'limit':limits['max_strategy_concentration']}
    comparison={'legacy_linear':{'state':'NOT_ASSESSED','capability_warning':'Legacy reference-notional linearization; legacy LP/exit constraints; final range risk and cash deadline NOT_SUPPORTED.'}}
    if inp:
        result=optimize_portfolio(legacy_candidates(inp),portfolio_value_usd=float(amount*price),profile=profile)
        comparison['legacy_linear'].update(state='ASSESSED',allocation_weights={s:fmt(result.allocations.get(s,0)) for s in r.STRATEGIES},
            idle_weight=fmt(result.idle_weight),selection_expected_net_profit=measure(result.expected_net_profit_usd,'USD'),
            profit_comparability='LIMITED',cash_deadline='NOT_SUPPORTED',risk_namespace='LEGACY_COMPATIBILITY')
    return {'schema_version':'1.4','input':{'decision_amount_0g':amount_text,'profile':profile,'holding_horizon_days':horizon_text,'cash_deadline_days':deadline,'evidence_mode':evidence_mode},
        'run_scope':{'scope':'DECISION_SLEEVE','whole_portfolio_compliance':'NOT_ASSESSED','existing_positions':'EXOGENOUS_NOT_OPTIMIZED'},
        'valuation':{'price_usd':measure(price if synthetic else None,'USD',basis='MODELLED' if synthetic else 'MISSING'),'evidence_class':'MODELLED' if synthetic else 'MISSING'},
        'recommendation':{'method':'POLICY_AWARE_AMOUNT_OPTIMIZER','state':'SELECTED_REVALIDATION_FAILED' if not valid else 'RECOMMENDATION_GENERATED' if selected else 'KEEP_IDLE',
            'allocation_weights':{s:fmt(v) for s,v in weights.items()},'allocated_amounts_0g':{s:format((amount*v).normalize(),'f') for s,v in weights.items()},
            'idle_weight':fmt(idle),'idle_amount_0g':format((amount*idle).normalize(),'f'),'economics':aggregate,'revalidation_state':run.revalidation},
        'strategies':rows,'risk':{'profile':profile,'concentration':constraints['concentration'],'staking_stress':constraints['staking_stress'],
            'lp_absolute_stress':constraints['lp_absolute_stress'],'total_decision_sleeve_stress':measure(None if ep is None else ep['risk_budget']['total_loss_fraction']),
            'qualification':'Independent deterministic stress budgets; no correlated joint-event assumption'},
        'liquidity':{'holding_horizon_days':horizon_text,'cash_deadline_days':deadline,'deadline_state':'NOT_REQUESTED' if deadline is None else 'UNRESOLVED' if ep is None else ep['constraints']['cash_deadline']['state'], 'idle_time_to_cash_days':'0'},
        'policy':{'version':p.VERSION,'state':'NOT_ASSESSED' if ep is None else ep['overall'],'binding_constraints':[] if ep is None else list(ep['binding_constraints']),
            'unresolved_required_constraints':[] if ep is None else list(ep['unresolved_required_constraints']),
            'assessment':ep,'qualification':'SYNTHETIC_EVALUATION_ONLY; production evidence fails closed before policy assessment'},
        'solver':{'method':'AMOUNT_GRID_ENUMERATION_V1','grid':list(run.grid),'combinations_tested':run.combinations_tested,'revalidation_errors':list(run.revalidation_errors)},
        'evidence':{'mode':evidence_mode,'valuation_and_admission':'MODELLED' if synthetic else 'UNRESOLVED','runtime_binding':'UNRESOLVED'},
        'readiness':{'execution_readiness':'NOT_ESTABLISHED','public_proof':'NOT_ESTABLISHED','public_deployment':'NOT_REQUIRED_NOT_PLANNED'},
        'comparison':comparison}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decision-amount-0g',required=True);parser.add_argument('--holding-horizon-days',default='90')
    parser.add_argument('--cash-deadline-days');parser.add_argument('--profile',default='Balanced',choices=tuple(p.LP_LIMITS))
    parser.add_argument('--evidence-mode',default='PRODUCTION',choices=MODES)
    args=vars(parser.parse_args());print(json.dumps(optimize_request(**args),allow_nan=False))
